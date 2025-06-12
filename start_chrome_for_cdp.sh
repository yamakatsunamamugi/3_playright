#!/bin/bash
# Chrome起動スクリプト（CDP接続用）

echo "=== Chrome CDP起動スクリプト ==="
echo ""
echo "Chromeを起動します（ポート9222でデバッグ接続待機）"
echo ""

# 既存のChromeプロセスを確認
if lsof -i :9222 > /dev/null 2>&1; then
    echo "⚠️ ポート9222は既に使用中です"
    echo "既存のChromeを終了するか、別のポートを使用してください"
    exit 1
fi

# Chromeを起動
echo "🚀 Chromeを起動中..."
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --remote-debugging-port=9222 \
    --no-first-run \
    --no-default-browser-check \
    &

echo ""
echo "✅ Chromeが起動しました"
echo ""
echo "次の手順:"
echo "1. ChatGPT (https://chat.openai.com) にログイン"
echo "2. Claude (https://claude.ai) にログイン"
echo "3. 別のターミナルで test_cdp_connection.py を実行"
echo ""
echo "終了するには Ctrl+C を押してください"

# プロセスを待機
wait