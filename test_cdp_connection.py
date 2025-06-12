#!/usr/bin/env python3
"""
CDP接続テスト - 手動起動したChromeへの接続確認
"""

import asyncio
from playwright.async_api import async_playwright


async def test_cdp_connection():
    """CDP接続のシンプルなテスト"""
    print("=== CDP接続テスト ===")
    print("\n事前準備:")
    print("1. 別のターミナルで以下を実行してChromeを起動:")
    print("   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
    print("2. ChatGPTやClaudeにログイン")
    print("3. このスクリプトを実行\n")
    
    print("3秒後に接続を開始します...")
    await asyncio.sleep(3)
    
    async with async_playwright() as p:
        try:
            # CDP接続
            print("\n🔄 CDP接続を試行中...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            print("✅ CDP接続成功!")
            
            # コンテキストとページを確認
            contexts = browser.contexts
            print(f"📊 コンテキスト数: {len(contexts)}")
            
            if contexts:
                context = contexts[0]
                pages = context.pages
                print(f"📄 ページ数: {len(pages)}")
                
                for i, page in enumerate(pages):
                    print(f"   - ページ{i}: {page.url}")
                
                # ChatGPTページを探す
                chatgpt_page = None
                for page in pages:
                    if "chat.openai.com" in page.url:
                        chatgpt_page = page
                        print("\n✅ ChatGPTページを発見!")
                        break
                
                if not chatgpt_page:
                    # 新しいタブでChatGPTを開く
                    print("\n📋 新しいタブでChatGPTを開きます...")
                    chatgpt_page = await context.new_page()
                    await chatgpt_page.goto("https://chat.openai.com")
                
                # ログイン状態を確認
                await asyncio.sleep(3)
                login_button = await chatgpt_page.query_selector('[data-testid="login-button"]')
                
                if login_button:
                    print("⚠️ ChatGPTへのログインが必要です")
                else:
                    chat_input = await chatgpt_page.query_selector('[data-testid="prompt-textarea"]')
                    if chat_input:
                        print("✅ ChatGPTログイン済み - 使用可能!")
                        
                        # スクリーンショット
                        await chatgpt_page.screenshot(path="chatgpt_cdp_test.png")
                        print("📸 スクリーンショット保存: chatgpt_cdp_test.png")
                
                # Claudeページを探す
                claude_page = None
                for page in pages:
                    if "claude.ai" in page.url:
                        claude_page = page
                        print("\n✅ Claudeページを発見!")
                        break
                
                if not claude_page:
                    # 新しいタブでClaudeを開く
                    print("\n📋 新しいタブでClaudeを開きます...")
                    claude_page = await context.new_page()
                    await claude_page.goto("https://claude.ai")
                
                # ログイン状態を確認
                await asyncio.sleep(3)
                chat_input = await claude_page.query_selector('div[contenteditable="true"]')
                
                if chat_input:
                    print("✅ Claudeログイン済み - 使用可能!")
                    
                    # スクリーンショット
                    await claude_page.screenshot(path="claude_cdp_test.png")
                    print("📸 スクリーンショット保存: claude_cdp_test.png")
                else:
                    print("⚠️ Claudeへのログインが必要です")
                
            print("\n✅ テスト完了 - CDP接続は正常に動作しています!")
            print("💡 ブラウザは開いたままにします（手動で閉じてください）")
            
        except Exception as e:
            print(f"\n❌ エラー: {e}")
            print("\n💡 トラブルシューティング:")
            print("1. Chromeが --remote-debugging-port=9222 で起動しているか確認")
            print("2. 別のChromeインスタンスが起動していないか確認")
            print("3. ポート9222が使用されていないか確認: lsof -i :9222")


if __name__ == "__main__":
    asyncio.run(test_cdp_connection())