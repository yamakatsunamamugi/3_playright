#!/usr/bin/env python3
"""
拡張版Chromeマネージャーのテスト
手動起動のChromeに接続してCloudflareを回避
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.browser.enhanced_real_chrome_manager import EnhancedRealChromeManager
from src.utils.logger import setup_logger


async def test_enhanced_chrome():
    """拡張版Chromeマネージャーのテスト"""
    print("=== 拡張版Chromeマネージャーテスト ===")
    
    # ロガー設定
    setup_logger()
    
    # マネージャー作成
    manager = EnhancedRealChromeManager(cdp_port=9222)
    
    # 手動起動の手順を表示
    manager.show_manual_instructions()
    
    try:
        # 初期化（CDP接続を試行）
        print("\n🔄 ブラウザに接続中...")
        if not await manager.initialize():
            print("❌ ブラウザ初期化失敗")
            print("\n💡 ヒント: 上記の手順でChromeを手動起動してください")
            return
        
        print(f"✅ ブラウザ接続成功")
        print(f"📊 状態: {manager.get_status()}")
        
        # ChatGPTテスト
        print("\n=== ChatGPTテスト ===")
        chatgpt_page = await manager.get_logged_in_page("ChatGPT", "https://chat.openai.com")
        
        if chatgpt_page:
            print("✅ ChatGPTページ作成成功")
            
            # ログイン状態確認
            if await manager.ensure_logged_in(chatgpt_page, "ChatGPT"):
                print("✅ ChatGPTログイン済み")
                
                # スクリーンショット保存
                await chatgpt_page.screenshot(path="chatgpt_logged_in.png")
                print("📸 スクリーンショット保存: chatgpt_logged_in.png")
            else:
                print("⚠️ ChatGPTログインが必要です")
                if await manager.wait_for_manual_login(chatgpt_page, "ChatGPT", timeout=120):
                    print("✅ 手動ログイン完了")
                else:
                    print("❌ ログインタイムアウト")
        
        # Claudeテスト
        print("\n=== Claudeテスト ===")
        claude_page = await manager.get_logged_in_page("Claude", "https://claude.ai")
        
        if claude_page:
            print("✅ Claudeページ作成成功")
            
            # ログイン状態確認
            if await manager.ensure_logged_in(claude_page, "Claude"):
                print("✅ Claudeログイン済み")
                
                # スクリーンショット保存
                await claude_page.screenshot(path="claude_logged_in.png")
                print("📸 スクリーンショット保存: claude_logged_in.png")
            else:
                print("⚠️ Claudeログインが必要です")
                if await manager.wait_for_manual_login(claude_page, "Claude", timeout=120):
                    print("✅ 手動ログイン完了")
                else:
                    print("❌ ログインタイムアウト")
        
        # 30秒待機（動作確認）
        print("\n⏳ 30秒間待機中...")
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # クリーンアップ
        print("\n🧹 クリーンアップ中...")
        await manager.cleanup()
        print("✅ 完了")


if __name__ == "__main__":
    asyncio.run(test_enhanced_chrome())