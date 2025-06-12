#!/usr/bin/env python3
"""
シンプルなCloudflare回避テスト
"""

import asyncio
from playwright.async_api import async_playwright


async def test_simple():
    """最小限の設定でテスト"""
    print("=== シンプルCloudflareテスト ===")
    
    async with async_playwright() as p:
        # ブラウザ起動（最小限のオプション）
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        # コンテキスト作成
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # bot検出回避スクリプト
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # ChatGPTにアクセス
        print("ChatGPTにアクセス中...")
        page = await context.new_page()
        
        try:
            await page.goto('https://chat.openai.com', wait_until='domcontentloaded', timeout=30000)
            print("✅ ChatGPTページ読み込み成功")
            
            # 30秒待機
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"❌ エラー: {e}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_simple())