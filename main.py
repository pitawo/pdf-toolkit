import streamlit as st
import os
import tempfile
import zipfile
import io
from pdf_operations import (
    combine_pdfs,
    add_page_numbers,
    split_pdf,
    extract_pages,
    parse_page_numbers,
    rotate_pages,
    add_watermark
)
from app_utils import (
    MAX_TOTAL_UPLOAD_MB,
    describe_error,
    read_pdf,
    safe_filename,
    save_upload,
    total_size_mb
)


OFFICE_EXTENSIONS = ('.xlsx', '.xls', '.docx', '.doc', '.pptx', '.ppt', '.odt', '.ods', '.odp')


@st.cache_resource
def libreoffice_available():
    """LibreOffice が使える環境かを一度だけ調べる（検出に数秒かかるためキャッシュする）。"""
    from file_converter_libreoffice import check_libreoffice_installation
    return check_libreoffice_installation()


def main():
    st.set_page_config(
        page_title="PDF変換・結合ツール",
        page_icon="📄",
        layout="wide"
    )

    st.title("📄 PDF変換・結合ツール")

    # タブを作成
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔄 変換・結合",
        "✂️ PDF分割",
        "📑 ページ抽出",
        "🔃 ページ回転",
        "💧 透かし追加"
    ])

    # タブ1: 変換・結合（既存機能）
    with tab1:
        render_convert_combine_tab()

    # タブ2: PDF分割
    with tab2:
        render_split_tab()

    # タブ3: ページ抽出
    with tab3:
        render_extract_tab()

    # タブ4: ページ回転
    with tab4:
        render_rotate_tab()

    # タブ5: 透かし追加
    with tab5:
        render_watermark_tab()


def render_convert_combine_tab():
    """変換・結合タブの描画"""
    # セッションステートの初期化
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []
    if 'uploaded_files_raw' not in st.session_state:
        st.session_state.uploaded_files_raw = []
    if 'converted_files' not in st.session_state:
        st.session_state.converted_files = []
    if 'combined_pdf' not in st.session_state:
        st.session_state.combined_pdf = None
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0

    # ファイルの順序変更用の関数
    def move_file_up(idx):
        if idx > 0:
            st.session_state.uploaded_files[idx], st.session_state.uploaded_files[idx - 1] = \
                st.session_state.uploaded_files[idx - 1], st.session_state.uploaded_files[idx]
            st.rerun()

    def move_file_down(idx):
        if idx < len(st.session_state.uploaded_files) - 1:
            st.session_state.uploaded_files[idx], st.session_state.uploaded_files[idx + 1] = \
                st.session_state.uploaded_files[idx + 1], st.session_state.uploaded_files[idx]
            st.rerun()

    def remove_file(idx):
        if idx < len(st.session_state.uploaded_files):
            file = st.session_state.uploaded_files[idx]
            st.session_state.uploaded_files.pop(idx)
            if file in st.session_state.uploaded_files_raw:
                st.session_state.uploaded_files_raw.remove(file)
            st.rerun()

    st.info("📌 対応形式: JPG, PNG, PDF, Excel, Word, PowerPoint, OpenDocument")
    supported_types = ['jpg', 'jpeg', 'png', 'pdf', 'xlsx', 'xls', 'docx', 'doc', 'pptx', 'ppt', 'odt', 'ods', 'odp']

    st.subheader("🗂️ ファイルをアップロード")

    new_files = st.file_uploader(
        "ファイルをアップロードしてください。",
        accept_multiple_files=True,
        type=supported_types,
        key=f"file_uploader_{st.session_state.uploader_key}"
    )

    if new_files:
        for file in new_files:
            if file not in st.session_state.uploaded_files_raw:
                st.session_state.uploaded_files.append(file)
                st.session_state.uploaded_files_raw.append(file)

    if not st.session_state.uploaded_files:
        st.info("📥 ファイルをアップロードしてください。")
        return

    # 変換結果はすべてメモリ上に保持するので、合計サイズが大きいときは先に知らせる
    uploaded_mb = total_size_mb(st.session_state.uploaded_files)
    if uploaded_mb > MAX_TOTAL_UPLOAD_MB:
        st.warning(
            "アップロードの合計が %.0fMB あります。%dMB を超えると処理に失敗することがあります。"
            "ファイルを分けてお試しください。" % (uploaded_mb, MAX_TOTAL_UPLOAD_MB)
        )

    # Office 文書の変換には LibreOffice が要る。実行してから失敗するより先に伝える
    has_office = any(
        f.name.lower().endswith(OFFICE_EXTENSIONS) for f in st.session_state.uploaded_files
    )
    if has_office and not libreoffice_available():
        st.warning(
            "この環境では Office 文書の変換に必要な LibreOffice が見つかりませんでした。"
            "PDF と画像はそのまま処理できます。"
        )

    # 処理対象リスト
    if st.session_state.uploaded_files:
        st.subheader("📑 処理対象ファイル（順番変更・削除可能）")

        for idx, file in enumerate(st.session_state.uploaded_files):
            col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
            with col1:
                st.text(f"{idx + 1}. {file.name}")
            with col2:
                if st.button("⬆️ 上へ", key=f"up_{idx}"):
                    move_file_up(idx)
            with col3:
                if st.button("⬇️ 下へ", key=f"down_{idx}"):
                    move_file_down(idx)
            with col4:
                if st.button("🗑️ 削除", key=f"delete_{idx}"):
                    remove_file(idx)

    st.markdown("---")
    st.subheader("⚙️ オプション設定")
    col1, col2 = st.columns(2)

    combine_option = col1.checkbox("🛠️ PDFを結合する", value=False)
    combined_filename = col1.text_input("📄 結合後のファイル名", value="combined_document", disabled=not combine_option)
    add_page_numbers_option = col2.checkbox("🔢 ページ番号を追加する", value=False)

    if st.button("🚀 変換を開始", type="primary", key="convert_start"):
        from file_converter_libreoffice import convert_to_pdf

        with st.spinner("⏳ 処理中..."):
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # セッションステートのリセット
                    st.session_state.converted_files = []
                    st.session_state.combined_pdf = None

                    # 変換後の PDF のパスを順番どおりに保持する
                    converted_pdf_paths = []
                    used_names = set()

                    for uploaded_file in st.session_state.uploaded_files:
                        # ファイル名はブラウザから来る値なので、そのままパスに使わない。
                        # 同名が複数あると上書きされてしまうため連番も付ける。
                        temp_path = save_upload(uploaded_file, temp_dir, used_names)

                        if not os.path.exists(temp_path):
                            raise FileNotFoundError("一時ファイルを作成できませんでした")

                        pdf_path = convert_to_pdf(temp_path, temp_dir) if not temp_path.lower().endswith('.pdf') else temp_path

                        if add_page_numbers_option and not combine_option:
                            pdf_path = add_page_numbers(pdf_path)

                        if not os.path.exists(pdf_path):
                            raise FileNotFoundError("変換後のPDFを作成できませんでした")

                        # Append to the list of PDF paths
                        converted_pdf_paths.append(pdf_path)

                        # 変換後のPDFをバイトデータとして保存
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                        st.session_state.converted_files.append({
                            "name": os.path.basename(pdf_path),
                            "data": pdf_bytes
                        })

                    if combine_option:
                        # 結合処理（ファイル名は利用者の入力なので安全な形に直す）
                        safe_stem = safe_filename(combined_filename, default="combined_document")
                        combined_pdf_temp = os.path.join(temp_dir, f"{safe_stem}.pdf")
                        combine_pdfs(converted_pdf_paths, combined_pdf_temp)

                        if add_page_numbers_option:
                            combined_pdf_temp = add_page_numbers(combined_pdf_temp)

                        # 結合後のPDFをバイトデータとして保存
                        with open(combined_pdf_temp, "rb") as combined_pdf_file:
                            combined_pdf_bytes = combined_pdf_file.read()
                        st.session_state.combined_pdf = {
                            "name": f"{safe_stem}_final.pdf",
                            "data": combined_pdf_bytes
                        }

            except Exception as e:
                # 他のタブの描画まで止めたくないので st.stop() は使わない
                st.error("❌ " + describe_error(e))

    st.markdown("---")
    st.subheader("📥 ダウンロード")

    if combine_option:
        if st.session_state.combined_pdf and "data" in st.session_state.combined_pdf:
            st.download_button(
                "📥 結合PDFをダウンロード",
                st.session_state.combined_pdf["data"],
                file_name=st.session_state.combined_pdf["name"],
                mime="application/pdf",
                key="download_combined"
            )
    else:
        if st.session_state.converted_files:
            for i, file_dict in enumerate(st.session_state.converted_files):
                st.download_button(
                    f"📥 {file_dict['name']} をダウンロード",
                    file_dict['data'],
                    file_name=file_dict['name'],
                    mime="application/pdf",
                    key=f"download_converted_{i}"
                )
        else:
            st.info("📥 変換されたファイルがありません。")


def render_split_tab():
    """PDF分割タブの描画"""
    st.subheader("✂️ PDFを個別のページに分割")
    st.write("PDFファイルをアップロードすると、各ページを個別のPDFファイルに分割します。")

    # セッションステートの初期化
    if 'split_result' not in st.session_state:
        st.session_state.split_result = None

    uploaded_file = st.file_uploader(
        "PDFファイルをアップロード",
        type=['pdf'],
        key="split_uploader"
    )

    # 開けるかどうかはアップロードした時点で確かめる（開けないファイルで画面を落とさない）
    pdf_bytes, reader, error = None, None, None
    if uploaded_file:
        pdf_bytes = uploaded_file.getvalue()
        reader, error = read_pdf(pdf_bytes)
        if error:
            st.error("❌ " + error)

    if uploaded_file and not error:
        total_pages = len(reader.pages)
        st.info(f"📄 {safe_filename(uploaded_file.name)} - 全{total_pages}ページ")

        if st.button("✂️ 分割実行", type="primary", key="split_execute"):
            with st.spinner("⏳ 分割中..."):
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # ファイル名はブラウザから来る値なので、そのままパスに使わない
                        temp_path = save_upload(uploaded_file, temp_dir, data=pdf_bytes)

                        # PDF分割
                        output_paths = split_pdf(temp_path, temp_dir)

                        # ZIPファイルを作成
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for path in output_paths:
                                zip_file.write(path, os.path.basename(path))

                        zip_buffer.seek(0)
                        st.session_state.split_result = {
                            "zip_data": zip_buffer.getvalue(),
                            "filename": f"{os.path.splitext(safe_filename(uploaded_file.name))[0]}_split.zip",
                            "page_count": len(output_paths)
                        }

                    st.success(f"✅ {len(output_paths)}ページに分割しました")

                except Exception as e:
                    st.error("❌ " + describe_error(e))

    # ダウンロードボタン
    if st.session_state.split_result:
        st.download_button(
            f"📥 分割されたPDFをダウンロード（ZIP形式・{st.session_state.split_result['page_count']}ファイル）",
            st.session_state.split_result["zip_data"],
            file_name=st.session_state.split_result["filename"],
            mime="application/zip",
            key="download_split"
        )


def render_extract_tab():
    """ページ抽出タブの描画"""
    st.subheader("📑 指定ページを抽出")
    st.write("PDFから指定したページのみを抽出して新しいPDFを作成します。")

    # セッションステートの初期化
    if 'extract_result' not in st.session_state:
        st.session_state.extract_result = None

    uploaded_file = st.file_uploader(
        "PDFファイルをアップロード",
        type=['pdf'],
        key="extract_uploader"
    )

    # 開けるかどうかはアップロードした時点で確かめる（開けないファイルで画面を落とさない）
    pdf_bytes, reader, error = None, None, None
    if uploaded_file:
        pdf_bytes = uploaded_file.getvalue()
        reader, error = read_pdf(pdf_bytes)
        if error:
            st.error("❌ " + error)

    if uploaded_file and not error:
        total_pages = len(reader.pages)
        st.info(f"📄 {safe_filename(uploaded_file.name)} - 全{total_pages}ページ")

        page_input = st.text_input(
            "抽出するページ番号を入力",
            placeholder="例: 1,3,5-10",
            help="カンマ区切りで個別ページ、ハイフンで範囲を指定できます"
        )

        if page_input:
            pages_to_extract = parse_page_numbers(page_input, total_pages)
            if pages_to_extract:
                st.write(f"抽出対象: {pages_to_extract}")
            else:
                st.warning("有効なページ番号が指定されていません")

        if st.button("📑 抽出実行", type="primary", key="extract_execute"):
            if not page_input:
                st.warning("ページ番号を入力してください")
            else:
                pages_to_extract = parse_page_numbers(page_input, total_pages)
                if not pages_to_extract:
                    st.warning("有効なページ番号が指定されていません")
                else:
                    with st.spinner("⏳ 抽出中..."):
                        try:
                            with tempfile.TemporaryDirectory() as temp_dir:
                                # ファイル名はブラウザから来る値なので、そのままパスに使わない
                                temp_path = save_upload(uploaded_file, temp_dir, data=pdf_bytes)

                                # ページ抽出
                                output_path = os.path.join(temp_dir, f"{os.path.splitext(safe_filename(uploaded_file.name))[0]}_extracted.pdf")
                                extract_pages(temp_path, pages_to_extract, output_path)

                                # 結果を保存
                                with open(output_path, "rb") as f:
                                    st.session_state.extract_result = {
                                        "data": f.read(),
                                        "filename": os.path.basename(output_path),
                                        "pages": pages_to_extract
                                    }

                            st.success(f"✅ {len(pages_to_extract)}ページを抽出しました")

                        except Exception as e:
                            st.error("❌ " + describe_error(e))

    # ダウンロードボタン
    if st.session_state.extract_result:
        st.download_button(
            f"📥 抽出したPDFをダウンロード（{len(st.session_state.extract_result['pages'])}ページ）",
            st.session_state.extract_result["data"],
            file_name=st.session_state.extract_result["filename"],
            mime="application/pdf",
            key="download_extract"
        )


def render_rotate_tab():
    """ページ回転タブの描画"""
    st.subheader("🔃 ページを回転")
    st.write("PDFのページを指定した角度で回転させます。")

    # セッションステートの初期化
    if 'rotate_result' not in st.session_state:
        st.session_state.rotate_result = None

    uploaded_file = st.file_uploader(
        "PDFファイルをアップロード",
        type=['pdf'],
        key="rotate_uploader"
    )

    # 開けるかどうかはアップロードした時点で確かめる（開けないファイルで画面を落とさない）
    pdf_bytes, reader, error = None, None, None
    if uploaded_file:
        pdf_bytes = uploaded_file.getvalue()
        reader, error = read_pdf(pdf_bytes)
        if error:
            st.error("❌ " + error)

    if uploaded_file and not error:
        total_pages = len(reader.pages)
        st.info(f"📄 {safe_filename(uploaded_file.name)} - 全{total_pages}ページ")

        col1, col2 = st.columns(2)

        with col1:
            rotation = st.selectbox(
                "回転角度",
                options=[90, 180, 270],
                format_func=lambda x: f"{x}度（{'右' if x == 90 else '反対' if x == 180 else '左'}回り）"
            )

        with col2:
            rotate_all = st.radio(
                "回転対象",
                options=["all", "specific"],
                format_func=lambda x: "全ページ" if x == "all" else "特定ページのみ",
                horizontal=True
            )

        page_numbers = None
        if rotate_all == "specific":
            page_input = st.text_input(
                "回転するページ番号を入力",
                placeholder="例: 1,3,5-10",
                help="カンマ区切りで個別ページ、ハイフンで範囲を指定できます"
            )
            if page_input:
                page_numbers = parse_page_numbers(page_input, total_pages)
                if page_numbers:
                    st.write(f"回転対象: {page_numbers}")
                else:
                    st.warning("有効なページ番号が指定されていません")

        if st.button("🔃 回転実行", type="primary", key="rotate_execute"):
            if rotate_all == "specific" and not page_numbers:
                st.warning("回転するページ番号を指定してください")
            else:
                with st.spinner("⏳ 回転中..."):
                    try:
                        with tempfile.TemporaryDirectory() as temp_dir:
                            # ファイル名はブラウザから来る値なので、そのままパスに使わない
                            temp_path = save_upload(uploaded_file, temp_dir, data=pdf_bytes)

                            # ページ回転
                            output_path = os.path.join(temp_dir, f"{os.path.splitext(safe_filename(uploaded_file.name))[0]}_rotated.pdf")
                            rotate_pages(temp_path, rotation, page_numbers, output_path)

                            # 結果を保存
                            with open(output_path, "rb") as f:
                                st.session_state.rotate_result = {
                                    "data": f.read(),
                                    "filename": os.path.basename(output_path)
                                }

                        target_desc = "全ページ" if rotate_all == "all" else f"{len(page_numbers)}ページ"
                        st.success(f"✅ {target_desc}を{rotation}度回転しました")

                    except Exception as e:
                        st.error("❌ " + describe_error(e))

    # ダウンロードボタン
    if st.session_state.rotate_result:
        st.download_button(
            "📥 回転後のPDFをダウンロード",
            st.session_state.rotate_result["data"],
            file_name=st.session_state.rotate_result["filename"],
            mime="application/pdf",
            key="download_rotate"
        )


def render_watermark_tab():
    """透かし追加タブの描画"""
    st.subheader("💧 透かしを追加")
    st.write("PDFの各ページにテキスト透かしを追加します。")

    # セッションステートの初期化
    if 'watermark_result' not in st.session_state:
        st.session_state.watermark_result = None

    uploaded_file = st.file_uploader(
        "PDFファイルをアップロード",
        type=['pdf'],
        key="watermark_uploader"
    )

    # 開けるかどうかはアップロードした時点で確かめる（開けないファイルで画面を落とさない）
    pdf_bytes, reader, error = None, None, None
    if uploaded_file:
        pdf_bytes = uploaded_file.getvalue()
        reader, error = read_pdf(pdf_bytes)
        if error:
            st.error("❌ " + error)

    if uploaded_file and not error:
        total_pages = len(reader.pages)
        st.info(f"📄 {safe_filename(uploaded_file.name)} - 全{total_pages}ページ")

        watermark_text = st.text_input(
            "透かしテキスト",
            placeholder="例: CONFIDENTIAL, DRAFT, サンプル"
        )

        st.subheader("⚙️ オプション設定")
        col1, col2, col3 = st.columns(3)

        with col1:
            font_size = st.slider("フォントサイズ", min_value=20, max_value=100, value=50)

        with col2:
            opacity = st.slider("透明度", min_value=0.1, max_value=1.0, value=0.3, step=0.1)

        with col3:
            angle = st.slider("角度", min_value=0, max_value=90, value=45)

        if st.button("💧 透かし追加", type="primary", key="watermark_execute"):
            if not watermark_text:
                st.warning("透かしテキストを入力してください")
            else:
                with st.spinner("⏳ 透かしを追加中..."):
                    try:
                        with tempfile.TemporaryDirectory() as temp_dir:
                            # ファイル名はブラウザから来る値なので、そのままパスに使わない
                            temp_path = save_upload(uploaded_file, temp_dir, data=pdf_bytes)

                            # 透かし追加
                            output_path = os.path.join(temp_dir, f"{os.path.splitext(safe_filename(uploaded_file.name))[0]}_watermarked.pdf")
                            add_watermark(temp_path, watermark_text, output_path, font_size, opacity, angle)

                            # 結果を保存
                            with open(output_path, "rb") as f:
                                st.session_state.watermark_result = {
                                    "data": f.read(),
                                    "filename": os.path.basename(output_path)
                                }

                        st.success(f"✅ 透かし「{watermark_text}」を追加しました")

                    except Exception as e:
                        st.error("❌ " + describe_error(e))

    # ダウンロードボタン
    if st.session_state.watermark_result:
        st.download_button(
            "📥 透かし付きPDFをダウンロード",
            st.session_state.watermark_result["data"],
            file_name=st.session_state.watermark_result["filename"],
            mime="application/pdf",
            key="download_watermark"
        )


if __name__ == "__main__":
    main()
