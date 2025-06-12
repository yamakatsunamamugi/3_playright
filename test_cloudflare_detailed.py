#!/usr/bin/env python3
"""
Cloudflare回避機能の詳細デバッグテスト
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.browser.cloudflare_bypass_manager import CloudflareBypassManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_cloudflare_detailed():
    """Cloudflare回避機能を詳細テスト"""
    bypass_manager = None
    
    try:
        logger.info("=== Cloudflare詳細デバッグテスト開始 ===")
        
        # CloudflareBypassManagerを初期化
        logger.info("🛡️ Cloudflare回避マネージャーを初期化中...")
        bypass_manager = CloudflareBypassManager(
            headless=False,
            use_existing_profile=True,
            debug_mode=True
        )
        
        # ブラウザを初期化
        logger.info("📋 bypass_manager.initialize()を呼び出し...")
        init_result = await bypass_manager.initialize()
        logger.info(f"📋 initialize()結果: {init_result}")
        
        if not init_result:
            raise Exception("Cloudflare回避マネージャーの初期化に失敗しました")
        
        logger.info("✅ Cloudflare回避マネージャー初期化完了")
        
        # ステータスを確認
        status = bypass_manager.get_status()
        logger.info(f"📊 マネージャーステータス: {status}")
        
        # コンテキストのテスト
        logger.info("\n=== コンテキスト作成テスト ===")
        test_context = await bypass_manager.create_stealth_context("test_service", restore_session=False)
        
        if test_context:
            logger.info("✅ コンテキスト作成成功")
            logger.info(f"📋 コンテキスト: {test_context}")
            
            # ページ作成のテスト
            logger.info("\n=== ページ作成テスト（URLなし）===")
            test_page = await test_context.new_page()
            if test_page:
                logger.info("✅ ページ作成成功")
                logger.info(f"📋 ページURL: {test_page.url}")
                await test_page.close()
            else:
                logger.error("❌ ページ作成失敗")
        else:
            logger.error("❌ コンテキスト作成失敗")
        
        # ChatGPTページ作成テスト
        logger.info("\n=== ChatGPTページ作成テスト ===")
        chatgpt_page = await bypass_manager.create_page_with_stealth(
            "chatgpt_test",
            "https://chat.openai.com"
        )
        
        if chatgpt_page:
            logger.info("✅ ChatGPTページ作成成功")
            logger.info(f"📋 ページURL: {chatgpt_page.url}")
            
            # 10秒待機
            await asyncio.sleep(10)
            
            # ログイン状態をチェック
            try:
                login_button = await chatgpt_page.query_selector('[data-testid="login-button"]')
                if login_button:
                    logger.info("⚠️ ChatGPTにログインしてください")
                else:
                    chat_input = await chatgpt_page.query_selector('[data-testid="prompt-textarea"]')
                    if chat_input:
                        logger.info("✅ ChatGPTログイン済み - 準備完了")
                    else:
                        logger.info("⚠️ ChatGPTの状態確認中...")
            except Exception as e:
                logger.error(f"❌ セレクターエラー: {e}")
        else:
            logger.error("❌ ChatGPTページ作成失敗")
            
            # 基本的なページ作成を試行
            logger.info("\n=== 基本ページテスト ===")
            if "test_service" in bypass_manager.contexts:
                basic_page = await bypass_manager.contexts["test_service"].new_page()
                if basic_page:
                    logger.info("✅ 基本ページ作成成功")
                    await basic_page.goto("https://www.google.com")
                    await asyncio.sleep(3)
                    logger.info(f"📋 Googleページタイトル: {await basic_page.title()}")
                    await basic_page.close()
        
        # 最終ステータス
        final_status = bypass_manager.get_status()
        logger.info(f"\n📊 最終ステータス: {final_status}")
        
        # 30秒待機
        logger.info("\n🌐 ブラウザを30秒間開いたままにします")
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
    asyncio.run(test_cloudflare_detailed())