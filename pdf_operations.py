from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.colors import Color

def combine_pdfs(pdf_paths, output_path):
    """
    複数のPDFファイルを1つに結合する
    """
    merger = PdfMerger()

    for pdf_path in pdf_paths:
        merger.append(pdf_path)

    merger.write(output_path)
    merger.close()

    return output_path

def add_page_numbers(pdf_path):
    """
    PDFにページ番号を追加する
    """
    # 一時ファイルのパスを生成
    temp_number_path = pdf_path.replace('.pdf', '_numbers.pdf')
    output_path = pdf_path.replace('.pdf', '_with_numbers.pdf')

    # 元のPDFを読み込む
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    # ページ番号用のPDFを作成
    c = canvas.Canvas(temp_number_path)

    for i in range(total_pages):
        page = reader.pages[i]

        # ページサイズを取得
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        # ページの向きに応じてキャンバスサイズを設定
        if width > height:
            c.setPageSize(landscape((width, height)))
            x_position = width - 15
            y_position = height - 15
        else:
            c.setPageSize((width, height))
            x_position = width - 15
            y_position = height - 15

        # ページ番号を描画
        c.setFont("Helvetica", 8)
        c.drawRightString(x_position, y_position, f"{i + 1}/{total_pages}")
        c.showPage()

    c.save()

    # ページ番号PDFと元のPDFを結合
    writer = PdfWriter()
    number_reader = PdfReader(temp_number_path)

    for i in range(total_pages):
        page = reader.pages[i]
        number_page = number_reader.pages[i]
        page.merge_page(number_page)
        writer.add_page(page)

    with open(output_path, 'wb') as f:
        writer.write(f)

    # 一時ファイルを削除
    os.remove(temp_number_path)

    return output_path


def split_pdf(pdf_path, output_dir):
    """
    PDFを個別のページに分割する

    Args:
        pdf_path: 分割するPDFファイルのパス
        output_dir: 分割されたPDFファイルを保存するディレクトリ

    Returns:
        分割されたPDFファイルのパスリスト
    """
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    output_paths = []

    for i in range(total_pages):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])

        output_path = os.path.join(output_dir, f"{base_name}_page_{i + 1}.pdf")
        with open(output_path, 'wb') as f:
            writer.write(f)

        output_paths.append(output_path)

    return output_paths


def extract_pages(pdf_path, page_numbers, output_path):
    """
    指定したページを抽出して新しいPDFを作成

    Args:
        pdf_path: 元のPDFファイルのパス
        page_numbers: 抽出するページ番号のリスト（1始まり）
        output_path: 出力PDFファイルのパス

    Returns:
        出力PDFファイルのパス
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    total_pages = len(reader.pages)

    for page_num in page_numbers:
        if 1 <= page_num <= total_pages:
            writer.add_page(reader.pages[page_num - 1])

    with open(output_path, 'wb') as f:
        writer.write(f)

    return output_path


def parse_page_numbers(page_string, total_pages):
    """
    ページ番号文字列を解析してページ番号のリストを返す

    Args:
        page_string: ページ番号文字列（例: "1,3,5-10"）
        total_pages: PDFの総ページ数

    Returns:
        ページ番号のリスト（1始まり）
    """
    pages = set()
    parts = page_string.replace(' ', '').split(',')

    for part in parts:
        if '-' in part:
            try:
                start, end = part.split('-')
                start = int(start)
                end = int(end)
                for i in range(start, end + 1):
                    if 1 <= i <= total_pages:
                        pages.add(i)
            except ValueError:
                continue
        else:
            try:
                page = int(part)
                if 1 <= page <= total_pages:
                    pages.add(page)
            except ValueError:
                continue

    return sorted(list(pages))


def rotate_pages(pdf_path, rotation, page_numbers=None, output_path=None):
    """
    ページを回転

    Args:
        pdf_path: 元のPDFファイルのパス
        rotation: 回転角度（90, 180, 270のいずれか）
        page_numbers: 回転するページ番号のリスト（1始まり）。Noneの場合は全ページ
        output_path: 出力PDFファイルのパス。Noneの場合は元のファイル名に_rotatedを付加

    Returns:
        出力PDFファイルのパス
    """
    if output_path is None:
        output_path = pdf_path.replace('.pdf', '_rotated.pdf')

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    total_pages = len(reader.pages)

    for i in range(total_pages):
        page = reader.pages[i]

        if page_numbers is None or (i + 1) in page_numbers:
            page.rotate(rotation)

        writer.add_page(page)

    with open(output_path, 'wb') as f:
        writer.write(f)

    return output_path


def add_watermark(pdf_path, watermark_text, output_path=None, font_size=50, opacity=0.3, angle=45):
    """
    テキスト透かしを追加

    Args:
        pdf_path: 元のPDFファイルのパス
        watermark_text: 透かしテキスト
        output_path: 出力PDFファイルのパス。Noneの場合は元のファイル名に_watermarkedを付加
        font_size: フォントサイズ（デフォルト: 50）
        opacity: 透明度（0.0-1.0、デフォルト: 0.3）
        angle: 回転角度（デフォルト: 45）

    Returns:
        出力PDFファイルのパス
    """
    if output_path is None:
        output_path = pdf_path.replace('.pdf', '_watermarked.pdf')

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    total_pages = len(reader.pages)

    # 一時的な透かしPDFのパス
    temp_watermark_path = pdf_path.replace('.pdf', '_temp_watermark.pdf')

    # 透かし用のPDFを作成
    c = canvas.Canvas(temp_watermark_path)

    for i in range(total_pages):
        page = reader.pages[i]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        c.setPageSize((width, height))
        c.saveState()

        # 透明度を設定
        c.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
        c.setFont("Helvetica-Bold", font_size)

        # ページの中央に透かしを配置
        c.translate(width / 2, height / 2)
        c.rotate(angle)
        c.drawCentredString(0, 0, watermark_text)

        c.restoreState()
        c.showPage()

    c.save()

    # 透かしPDFを元のPDFにマージ
    watermark_reader = PdfReader(temp_watermark_path)

    for i in range(total_pages):
        page = reader.pages[i]
        watermark_page = watermark_reader.pages[i]
        page.merge_page(watermark_page)
        writer.add_page(page)

    with open(output_path, 'wb') as f:
        writer.write(f)

    # 一時ファイルを削除
    os.remove(temp_watermark_path)

    return output_path
