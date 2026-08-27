# -*- coding: utf-8 -*-
"""アップロードファイルの取り扱いとエラー表示の共通処理。

各タブが同じ処理を書いていたので、ここに集約する。
やっていることは3つ。

  1. ファイル名を安全にする（ブラウザから来る名前をそのままパスに使わない）
  2. PDF を開けなかった理由を日本語で返す（ライブラリの英語例外をそのまま出さない）
  3. 同名ファイルの衝突を避ける
"""
import io
import os
import re

from PyPDF2 import PdfReader

# ファイル名に使えない文字（Windows の禁止文字と制御文字）
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

MAX_TOTAL_UPLOAD_MB = 100


def safe_filename(name, default="upload"):
    """ブラウザから来たファイル名を、パスとして安全な形に直す。

    `../` などでディレクトリを抜けられないよう basename を取り、
    禁止文字を落とす。空になった場合は default を使う。
    """
    name = os.path.basename(name or "")
    # basename は Windows 形式の区切りを落とさない環境があるので明示的に処理する
    name = name.replace("\\", "/").split("/")[-1]
    name = _UNSAFE_CHARS.sub("_", name).strip(" .")
    return name or default


def unique_path(directory, filename, used=None):
    """同名ファイルが既にある場合に連番を付けて衝突を避ける。"""
    used = used if used is not None else set()
    stem, ext = os.path.splitext(filename)
    candidate = filename
    index = 2
    while candidate in used or os.path.exists(os.path.join(directory, candidate)):
        candidate = "%s_%d%s" % (stem, index, ext)
        index += 1
    used.add(candidate)
    return os.path.join(directory, candidate)


def save_upload(uploaded_file, temp_dir, used=None, data=None):
    """アップロードされたファイルを一時ディレクトリへ安全に保存し、パスを返す。"""
    filename = safe_filename(getattr(uploaded_file, "name", ""), default="upload.pdf")
    path = unique_path(temp_dir, filename, used)
    with open(path, "wb") as f:
        f.write(data if data is not None else uploaded_file.getvalue())
    return path


def describe_error(exc):
    """例外を、利用者に意味が伝わる日本語のメッセージに変換する。

    ライブラリの英語メッセージ（"File has not been decrypted" など）は
    そのままでは何をすればよいか分からないため、対処を添えた文言に置き換える。
    """
    name = type(exc).__name__
    text = str(exc)

    if "FileNotDecrypted" in name or "has not been decrypted" in text:
        return "このPDFはパスワードで保護されています。保護を解除したファイルをアップロードしてください。"
    if "EmptyFile" in name or "empty file" in text.lower():
        return "ファイルの中身が空です。別のファイルを選んでください。"
    if "PdfReadError" in name or "EOF marker not found" in text or "startxref" in text:
        return "PDFとして読み取れませんでした。ファイルが壊れているか、PDF ではない可能性があります。"
    if "DependencyError" in name or "crypt" in text.lower():
        return "このPDFの暗号化方式に対応していません。保護を解除したファイルをアップロードしてください。"
    if isinstance(exc, FileNotFoundError):
        return "処理中にファイルを見つけられませんでした。もう一度お試しください。"
    if "TimeoutExpired" in name:
        return "変換に時間がかかりすぎたため中断しました。ファイルを小さくして試してください。"
    if isinstance(exc, MemoryError):
        return "ファイルが大きすぎて処理できませんでした。分割してからお試しください。"
    # 想定外のものは種類だけ出す（内部パスなどを画面に出さない）
    return "処理中に問題が発生しました（%s）。ファイルを確認してもう一度お試しください。" % name


def read_pdf(data):
    """PDF を読み込む。読めない場合は (None, 日本語メッセージ) を返す。"""
    try:
        reader = PdfReader(io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else data)
        # ページ数の取得まで行って初めて「開けた」と判断する
        len(reader.pages)
        return reader, None
    except Exception as e:  # PyPDF2 は例外の種類が多いのでまとめて受ける
        return None, describe_error(e)


def total_size_mb(files):
    """アップロードされたファイルの合計サイズ（MB）。"""
    total = 0
    for f in files:
        try:
            total += f.size
        except AttributeError:
            total += len(f.getvalue())
    return total / (1024 * 1024)
