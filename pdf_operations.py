from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape

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
