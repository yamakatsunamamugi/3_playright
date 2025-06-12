# AI Tools Automation with Google Sheets

Googleスプレッドシートと複数のAIツールを連携させる自動化ツール

## 機能

- Googleスプレッドシートからデータを読み取り
- 複数のAIツール（ChatGPT、Claude、Gemini、Genspark、Google AI Studio）を自動操作
- AIの回答結果をスプレッドシートに書き戻し
- GUIによる直感的な操作

## 必要な環境

- Python 3.8以上
- macOS (将来的にWindows対応予定)
- Google APIアクセス権限

## セットアップ

1. 仮想環境の作成と有効化
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

2. 依存関係のインストール
```bash
pip install -r requirements.txt
```

3. Google Sheets API認証設定
   - Google Cloud Consoleでプロジェクトを作成
   - Google Sheets APIを有効化
   - 認証情報をダウンロードし、`config/credentials.json`として保存

4. アプリケーションの起動
```bash
python src/main.py
```

## プロジェクト構造

```
├── src/
│   ├── main.py              # メインアプリケーション
│   ├── gui/                 # GUI関連
│   ├── sheets/              # Google Sheets連携
│   ├── ai_tools/            # AIツール操作
│   └── utils/               # ユーティリティ
├── tests/                   # テストコード
├── docs/                    # ドキュメント
├── config/                  # 設定ファイル
└── requirements.txt         # 依存関係
```