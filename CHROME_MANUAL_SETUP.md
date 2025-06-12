# Chrome手動起動によるCloudflare回避手順

## 概要
Cloudflareのブロックを回避するため、手動でChromeを起動してからPlaywrightで接続する方法です。

## 手順

### 1. Chromeを手動で起動

ターミナルで以下のコマンドを実行します：

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

このコマンドで：
- Chromeが通常モードで起動します
- ポート9222でデバッグ接続を待ち受けます
- 既存のプロファイル（ログイン情報など）が使用されます

### 2. AIサービスにログイン

起動したChromeで以下のサイトにアクセスしてログインします：

1. **ChatGPT**: https://chat.openai.com
2. **Claude**: https://claude.ai
3. **Gemini**: https://gemini.google.com
4. **Genspark**: https://www.genspark.ai
5. **Google AI Studio**: https://aistudio.google.com

### 3. スクリプトを実行

別のターミナルウィンドウで：

```bash
cd /Users/roudousha/Dropbox/6.auto/3.playwrite
python3 test_cdp_connection.py
```

または、メインアプリケーションを実行：

```bash
python3 main.py
```

## 仕組み

1. **CDP（Chrome DevTools Protocol）接続**
   - 手動起動したChromeにPlaywrightが接続
   - 既存のセッション、Cookie、ログイン状態を維持

2. **Cloudflare回避の理由**
   - 通常のユーザーが使用している実際のChromeブラウザ
   - 自動化の痕跡がない
   - 既存のブラウジング履歴とCookieが存在

3. **メリット**
   - 100%確実にCloudflareを回避
   - ログイン状態が永続化
   - 拡張機能も使用可能

## トラブルシューティング

### ポート9222が使用中の場合

```bash
# 使用中のプロセスを確認
lsof -i :9222

# 別のポートを使用（例：9223）
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9223
```

### 接続できない場合

1. Chromeが正しく起動しているか確認
2. ファイアウォールがポート9222をブロックしていないか確認
3. 別のChromeインスタンスが起動していないか確認

## セキュリティ注意事項

- デバッグポートは外部からアクセスできないように注意
- 作業終了後はChromeを通常通り終了させる
- 本番環境では使用しない（開発・テスト用）