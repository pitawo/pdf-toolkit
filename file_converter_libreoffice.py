import os
import subprocess
import time
from PIL import Image
import shutil
import sys


def check_libreoffice_installation():
    """
    LibreOfficeがインストールされているかチェック
    """
    try:
        get_libreoffice_command()
        return True
    except Exception:
        return False


def get_libreoffice_command():
    """
    環境に応じたLibreOfficeコマンドを取得
    """
    print("=== LibreOffice検索開始 ===")

    # Windows用の標準インストールパスを優先（初回起動を考慮してタイムアウトを延長）
    windows_paths = [
        r'C:\Program Files\LibreOffice\program\soffice.exe',
        r'C:\Program Files (x86)\LibreOffice\program\soffice.exe'
    ]

    for path in windows_paths:
        if os.path.exists(path):
            try:
                print(f"テスト中（Windows標準パス）: {path}")

                # Windowsでコンソールウィンドウを非表示にする
                startupinfo = None
                if sys.platform == 'win32':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE

                result = subprocess.run(
                    [path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=15,  # 15秒に延長
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                if result.returncode == 0:
                    print(f"LibreOfficeが見つかりました: {path}")
                    return path
            except subprocess.TimeoutExpired:
                print(f"{path} タイムアウト（LibreOfficeの初回起動が遅い可能性）")
                # タイムアウトしても、実際の変換では動作する可能性があるので、このパスを返す
                print(f"タイムアウトしましたが、このパスを使用します: {path}")
                return path
            except FileNotFoundError:
                print(f"ファイルが見つかりません: {path}")
                continue

    # PATHからコマンドを試す
    path_commands = ['soffice', 'libreoffice', 'libreoffice7.0']

    for cmd in path_commands:
        try:
            print(f"テスト中（PATH）: {cmd}")

            # Windowsでコンソールウィンドウを非表示にする
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=10,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            if result.returncode == 0:
                print(f"LibreOfficeが見つかりました: {cmd}")
                return cmd
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"{cmd} で失敗: {type(e).__name__}")
            continue

    print("=== LibreOffice検索終了（見つからず） ===")
    raise Exception("LibreOfficeが見つかりません。LibreOfficeをインストールしてください。")


def convert_excel_with_fit_to_page(input_path, output_dir):
    """
    Excelファイルを1ページに収めてPDF変換（タイムアウト延長版）
    """
    libreoffice_cmd = get_libreoffice_command()
    file_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{file_name}.pdf")

    try:
        print(f"Excelファイルを1ページに収めて変換中: {os.path.basename(input_path)}")

        # 方法1: 直接calc_pdf_Exportでオプション指定を試行
        convert_cmd = [
            libreoffice_cmd,
            '--headless',
            '--convert-to', 'pdf:calc_pdf_Export:{"ScaleToPagesX":{"type":"long","value":"1"},"ScaleToPagesY":{"type":"long","value":"1"}}',
            '--outdir', output_dir,
            input_path
        ]

        print(f"方法1: オプション指定でPDF変換中...")

        # Windowsでコンソールウィンドウを非表示にする
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        result = subprocess.run(
            convert_cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2分に延長
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        if result.returncode == 0 and os.path.exists(output_path):
            print(f"方法1で変換成功: {os.path.basename(output_path)}")
            return output_path

        print(f"方法1失敗、方法2を試行...")

        # 方法2: 従来の単純変換（フォールバック）
        convert_cmd_simple = [
            libreoffice_cmd,
            '--headless',
            '--convert-to', 'pdf:calc_pdf_Export',
            '--outdir', output_dir,
            input_path
        ]

        print(f"方法2: 単純変換でPDF変換中...")

        # Windowsでコンソールウィンドウを非表示にする
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        result = subprocess.run(
            convert_cmd_simple,
            capture_output=True,
            text=True,
            timeout=120,  # 2分に延長
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            raise Exception(f"PDF変換エラー: {error_msg}")

        print(f"方法2で変換完了: {os.path.basename(output_path)}")
        return output_path

    except subprocess.TimeoutExpired:
        raise Exception(f"LibreOfficeでの変換がタイムアウトしました（2分経過）: {input_path}")
    except Exception as e:
        raise Exception(f"Excel変換エラー: {e}")


def convert_to_pdf(input_path, output_dir):
    """
    Convert supported files to PDF using LibreOffice
    Supports: Images (jpg, jpeg, png), Word (docx, doc), Excel (xlsx, xls), PowerPoint (pptx, ppt), OpenDocument (odt, ods, odp)
    """
    file_ext = os.path.splitext(input_path)[1].lower()
    file_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{file_name}.pdf")

    try:
        if file_ext in ['.jpg', '.jpeg', '.png']:
            # 画像ファイルの場合はPillowを使用
            image = Image.open(input_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(output_path, "PDF", resolution=100.0)
            image.close()

        elif file_ext in ['.xlsx', '.xls', '.docx', '.doc', '.pptx', '.ppt', '.odt', '.ods', '.odp']:
            # Office文書の場合はLibreOfficeを使用
            libreoffice_cmd = get_libreoffice_command()

            # LibreOfficeコマンドを実行
            cmd = [
                libreoffice_cmd,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                input_path
            ]

            print(f"実行中: {' '.join(cmd)}")

            # Windowsでコンソールウィンドウを非表示にする
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise Exception(f"LibreOffice変換エラー (終了コード: {result.returncode}): {error_msg}")

        else:
            raise Exception(f"サポートされていないファイル形式: {file_ext}")

        # 変換後のファイルが存在するか確認
        max_wait_time = 10  # 最大10秒待機
        wait_time = 0
        while not os.path.exists(output_path) and wait_time < max_wait_time:
            time.sleep(1)
            wait_time += 1

        if not os.path.exists(output_path):
            raise Exception(f"変換後のPDFファイルが見つかりません: {output_path}")

        return output_path

    except subprocess.TimeoutExpired:
        raise Exception(f"LibreOfficeでの変換がタイムアウトしました: {input_path}")
    except Exception as e:
        raise Exception(f"ファイル {input_path} のPDF変換エラー: {e}")


def get_supported_extensions():
    """対応しているファイル拡張子のリストを返す"""
    return ['jpg', 'jpeg', 'png', 'pdf', 'xlsx', 'xls', 'docx', 'doc', 'pptx', 'ppt', 'odt', 'ods', 'odp']
