# PDF変換・結合ツール

Streamlitで作成されたWebアプリケーションです。様々なファイル形式をPDFに変換し、結合やページ番号の追加ができます。

## 機能

- **ファイル変換**: 画像やOffice文書をPDFに変換
- **PDF結合**: 複数のPDFファイルを1つに結合
- **ページ番号追加**: PDFにページ番号（1/10形式）を追加
- **順序変更**: アップロードしたファイルの順序を自由に変更

## 対応ファイル形式

| カテゴリ | 形式 |
|---------|------|
| 画像 | JPG, JPEG, PNG |
| PDF | PDF |
| Microsoft Office | Excel (xlsx, xls), Word (docx, doc), PowerPoint (pptx, ppt) |
| OpenDocument | ODT, ODS, ODP |

## 使い方

1. サイドバーからファイルをアップロード
2. ファイルリストで順番を調整（上下ボタンで移動、削除も可能）
3. オプションを設定
   - 「PDFを結合する」: 複数ファイルを1つのPDFにまとめる
   - 「ページ番号を追加する」: 各ページの右上にページ番号を付与
4. 「変換を開始」ボタンをクリック
5. 完了後、ダウンロードボタンからPDFを取得

## デモ

Streamlit Cloudで公開中: [アプリURL]

## ローカル環境での実行

### 必要条件

- Python 3.8以上
- LibreOffice（Office文書の変換に必要）

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/[username]/[repository].git
cd [repository]

# 依存パッケージをインストール
pip install -r requirements.txt

# LibreOfficeのインストール（Office文書変換に必要）
# Windows: https://www.libreoffice.org/ からダウンロード
# macOS: brew install --cask libreoffice
# Ubuntu: sudo apt install libreoffice
```

### 実行

```bash
streamlit run main.py
```

ブラウザで `http://localhost:8501` にアクセスしてください。

## ファイル構成

```
.
├── main.py                      # メインアプリケーション（UI）
├── pdf_operations.py            # PDF結合・ページ番号追加処理
├── file_converter_libreoffice.py # ファイル変換処理（LibreOffice連携）
├── requirements.txt             # Python依存パッケージ
├── packages.txt                 # Streamlit Cloud用システムパッケージ
└── .gitignore
```

## 技術スタック

- **フロントエンド**: Streamlit
- **PDF処理**: PyPDF2, ReportLab
- **画像処理**: Pillow
- **Office文書変換**: LibreOffice (headlessモード)

## ライセンス

MIT License
