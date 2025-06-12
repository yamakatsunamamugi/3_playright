# Google Sheets API セットアップガイド

## 1. Google Cloud Console での設定

### ステップ1: プロジェクト作成
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクト作成または既存プロジェクト選択
3. プロジェクト名: "SpreadsheetAI" など

### ステップ2: Google Sheets API有効化
1. 左メニュー → "APIとサービス" → "ライブラリ"
2. "Google Sheets API"を検索
3. "有効にする"をクリック

### ステップ3: 認証情報作成
1. 左メニュー → "APIとサービス" → "認証情報"
2. "認証情報を作成" → "サービスアカウント"
3. サービスアカウント名: "spreadsheet-ai-service"
4. 作成後、サービスアカウントをクリック
5. "キー"タブ → "キーを追加" → "新しいキーを作成"
6. "JSON"を選択してダウンロード

### ステップ4: ファイル配置
1. ダウンロードしたJSONファイルを以下に配置:
   ```
   /Users/roudousha/Dropbox/6.auto/3.playwrite/credentials/google_service_account.json
   ```

## 2. スプレッドシート共有設定

### 対象スプレッドシートの共有
1. Google スプレッドシートを開く
2. "共有"ボタンをクリック  
3. JSONファイル内の"client_email"のメールアドレスを追加
4. 権限: "編集者"または"閲覧者"

## 3. 必要なライブラリインストール

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## 4. テスト方法

認証が正しく設定されているかテストするため、以下のコマンドを実行:

```bash
python3 test_google_api.py
```