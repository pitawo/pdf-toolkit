import streamlit as st
import os
import tempfile
from pdf_operations import combine_pdfs, add_page_numbers
import shutil

def main():
    st.set_page_config(
        page_title="PDF変換・結合ツール",
        page_icon="📄",
        layout="wide"
    )

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

    # サイドバーの設定
    with st.sidebar:
        st.title("📄 ファイル管理")

        st.info("📌 対応形式: JPG, PNG, PDF, Excel, Word, PowerPoint, OpenDocument")
        supported_types = ['jpg', 'jpeg', 'png', 'pdf', 'xlsx', 'xls', 'docx', 'doc', 'pptx', 'ppt', 'odt', 'ods', 'odp']

        st.markdown("---")
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

    # メインコンテンツ
    st.title("📄 ファイル変換・結合ツール")
    st.markdown("---")

    if not st.session_state.uploaded_files:
        st.info("📥 サイドバーからファイルをアップロードしてください。")
        return

    # ------------------------------
    # 📑 処理対象リスト
    # ------------------------------
    if st.session_state.uploaded_files:
        st.subheader("📑 処理対象ファイル（順番変更・削除可能）")
        st.write("""
サイドバーでアップロードしたファイルのリストです。
順番変更・削除が可能です。
""")

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

    else:
        st.info("📥 サイドバーからファイルをアップロードしてください。")
        return

    st.markdown("---")
    st.subheader("⚙️ オプション設定")
    col1, col2 = st.columns(2)

    combine_option = col1.checkbox("🛠️ PDFを結合する", value=False)
    combined_filename = col1.text_input("📄 結合後のファイル名", value="combined_document", disabled=not combine_option)
    add_page_numbers_option = col2.checkbox("🔢 ページ番号を追加する", value=False)

    if st.button("🚀 変換を開始", type="primary"):
        from file_converter_libreoffice import convert_to_pdf

        with st.spinner("⏳ 処理中..."):
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # セッションステートのリセット
                    st.session_state.converted_files = []
                    st.session_state.combined_pdf = None

                    # リスト to store converted PDF paths
                    converted_pdf_paths = []

                    for uploaded_file in st.session_state.uploaded_files:
                        temp_path = os.path.join(temp_dir, uploaded_file.name)
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getvalue())

                        temp_path = os.path.abspath(temp_path)
                        if not os.path.exists(temp_path):
                            raise FileNotFoundError(f"一時ファイルが存在しません: {temp_path}")

                        pdf_path = convert_to_pdf(temp_path, temp_dir) if not uploaded_file.name.lower().endswith('.pdf') else temp_path

                        if add_page_numbers_option and not combine_option:
                            pdf_path = add_page_numbers(pdf_path)

                        if not os.path.exists(pdf_path):
                            raise FileNotFoundError(f"PDFファイルが存在しません: {pdf_path}")

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
                        # 結合処理
                        combined_pdf_temp = os.path.join(temp_dir, f"{combined_filename}.pdf")
                        combine_pdfs(converted_pdf_paths, combined_pdf_temp)

                        if add_page_numbers_option:
                            combined_pdf_temp = add_page_numbers(combined_pdf_temp)

                        # 結合後のPDFをバイトデータとして保存
                        with open(combined_pdf_temp, "rb") as combined_pdf_file:
                            combined_pdf_bytes = combined_pdf_file.read()
                        st.session_state.combined_pdf = {
                            "name": f"{combined_filename}_final.pdf",
                            "data": combined_pdf_bytes
                        }

            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")
                st.stop()

    st.markdown("---")
    st.subheader("📥 ダウンロード")

    if combine_option:
        if st.session_state.combined_pdf and "data" in st.session_state.combined_pdf:
            st.download_button(
                "📥 結合PDFをダウンロード",
                st.session_state.combined_pdf["data"],
                file_name=st.session_state.combined_pdf["name"],
                mime="application/pdf"
            )
    else:
        if st.session_state.converted_files:
            for file_dict in st.session_state.converted_files:
                st.download_button(
                    f"📥 {file_dict['name']} をダウンロード",
                    file_dict['data'],
                    file_name=file_dict['name'],
                    mime="application/pdf"
                )
        else:
            st.info("📥 変換されたファイルがありません。")

if __name__ == "__main__":
    main()
