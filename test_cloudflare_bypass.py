#!/usr/bin/env python3
"""
Cloudflare回避機能をテスト
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.browser.cloudflare_bypass_manager import CloudflareBypassManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_cloudflare_bypass():
    """Cloudflare回避機能をテスト"""
    bypass_manager = None
    
    try:
        logger.info("=== Cloudflare回避テスト開始 ===")
        
        # CloudflareBypassManagerを初期化
        logger.info("🛡️ Cloudflare回避マネージャーを初期化中...")
        bypass_manager = CloudflareBypassManager(
            headless=False,
            use_existing_profile=True,
            debug_mode=True
        )
        
        # ブラウザを初期化
        if not await bypass_manager.initialize():
            raise Exception("Cloudflare回避マネージャーの初期化に失敗しました")
        
        logger.info("✅ Cloudflare回避マネージャー初期化完了")
        
        # ChatGPTにアクセス
        logger.info("\n=== ChatGPTテスト ===")
        chatgpt_page = await bypass_manager.create_page_with_stealth(
            "chatgpt_test",
            "https://chat.openai.com"
        )
        
        if chatgpt_page:
            logger.info("✅ ChatGPTサイトへのアクセス成功")
            
            # 10秒待機
            await asyncio.sleep(10)
            
            # ログイン状態をチェック
            login_button = await chatgpt_page.query_selector('[data-testid="login-button"]')
            if login_button:
                logger.info("⚠️ ChatGPTにログインしてください")
            else:
                chat_input = await chatgpt_page.query_selector('[data-testid="prompt-textarea"]')
                if chat_input:
                    logger.info("✅ ChatGPTログイン済み - 準備完了")
                    await bypass_manager.save_session("chatgpt_test")
                    logger.info("💾 ChatGPTセッションを保存しました")
                else:
                    logger.info("⚠️ ChatGPTの状態確認中...")
        
        # Claudeにアクセス
        logger.info("\n=== Claudeテスト ===")
        claude_page = await bypass_manager.create_page_with_stealth(
            "claude_test",
            "https://claude.ai"
        )
        
        if claude_page:
            logger.info("✅ Claudeサイトへのアクセス成功")
            
            # 10秒待機
            await asyncio.sleep(10)
            
            # Claude の入力欄をチェック
            chat_input = await claude_page.query_selector('div[contenteditable="true"]')
            if chat_input:
                logger.info("✅ Claudeログイン済み - 準備完了")
                await bypass_manager.save_session("claude_test")
                logger.info("💾 Claudeセッションを保存しました")
            else:
                logger.info("⚠️ Claudeにログインしてください")
        
        # 30秒待機（手動操作用）
        logger.info("\n🌐 ブラウザを30秒間開いたままにします（手動でログイン可能）")
        await asyncio.sleep(30)
        
        logger.info("\n=== テスト完了 ===")
        
    except Exception as e:
        logger.error(f"❌ テストエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # クリーンアップ
        if bypass_manager:
            await bypass_manager.cleanup()
            logger.info("🧹 クリーンアップ完了")


if __name__ == "__main__":
    # 非同期処理を実行
    asyncio.run(test_cloudflare_bypass())