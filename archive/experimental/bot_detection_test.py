#!/usr/bin/env python3
"""
Bot検出テストツール
ステルス技術の効果を確認
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def bot_detection_test():
    """Bot検出の診断"""
    print("🔍 Bot検出テスト開始")
    print("=" * 50)
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    
    try:
        # 通常のコンテキスト（ステルスなし）
        print("\n1️⃣ 通常のブラウザ（ステルスなし）でテスト:")
        normal_context = await browser.new_context()
        normal_page = await normal_context.new_page()
        
        await normal_page.goto('https://bot.sannysoft.com/')
        await asyncio.sleep(3)
        await normal_page.screenshot(path='bot_test_normal.png', full_page=True)
        print("   📸 スクリーンショット: bot_test_normal.png")
        
        # フィンガープリント確認（通常）
        normal_fp = await normal_page.evaluate("""
            () => {
                return {
                    userAgent: navigator.userAgent,
                    webdriver: navigator.webdriver,
                    languages: navigator.languages,
                    plugins: Array.from(navigator.plugins).map(p => p.name),
                    chrome: window.chrome ? 'exists' : 'missing',
                    permissions: navigator.permissions ? 'exists' : 'missing'
                }
            }
        """)
        
        print("   🔍 通常ブラウザのフィンガープリント:")
        print(json.dumps(normal_fp, indent=4, ensure_ascii=False))
        
        await normal_context.close()
        
        # ステルスコンテキスト
        print("\n2️⃣ ステルスブラウザでテスト:")
        stealth_context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        stealth_page = await stealth_context.new_page()
        
        # ステルス設定を適用
        await stealth_async(stealth_page)
        
        # 高度なBot検出回避スクリプトを追加
        await stealth_context.add_init_script("""
            // navigator.webdriver を完全に削除
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Chrome関連オブジェクトを偽装
            window.chrome = {
                runtime: {},
                csi: function() {}
            };
            
            // navigator.plugins を偽装
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin' },
                    { name: 'Chrome PDF Viewer' },
                    { name: 'Native Client' }
                ],
            });
            
            // navigator.languages を偽装
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ja-JP', 'ja', 'en-US', 'en'],
            });
        """)
        
        await stealth_page.goto('https://bot.sannysoft.com/')
        await asyncio.sleep(3)
        await stealth_page.screenshot(path='bot_test_stealth.png', full_page=True)
        print("   📸 スクリーンショット: bot_test_stealth.png")
        
        # フィンガープリント確認（ステルス）
        stealth_fp = await stealth_page.evaluate("""
            () => {
                return {
                    userAgent: navigator.userAgent,
                    webdriver: navigator.webdriver,
                    languages: navigator.languages,
                    plugins: Array.from(navigator.plugins).map(p => p.name),
                    chrome: window.chrome ? 'exists' : 'missing',
                    permissions: navigator.permissions ? 'exists' : 'missing'
                }
            }
        """)
        
        print("   🔍 ステルスブラウザのフィンガープリント:")
        print(json.dumps(stealth_fp, indent=4, ensure_ascii=False))
        
        # areyouheadless.comでもテスト
        print("\n3️⃣ Headless検出テスト:")
        await stealth_page.goto('https://areyouheadless.com/')
        await asyncio.sleep(3)
        
        headless_result = await stealth_page.text_content('body')
        print(f"   🎯 Headless検出結果: {headless_result[:200]}...")
        
        await stealth_page.screenshot(path='headless_test.png', full_page=True)
        print("   📸 スクリーンショット: headless_test.png")
        
        await stealth_context.close()
        
        # 比較結果
        print("\n📊 比較結果:")
        print("-" * 30)
        print(f"通常ブラウザ webdriver: {normal_fp.get('webdriver')}")
        print(f"ステルス webdriver: {stealth_fp.get('webdriver')}")
        print(f"通常ブラウザ chrome: {normal_fp.get('chrome')}")
        print(f"ステルス chrome: {stealth_fp.get('chrome')}")
        
        if normal_fp.get('webdriver') and not stealth_fp.get('webdriver'):
            print("✅ webdriver隠蔽成功")
        else:
            print("❌ webdriver隠蔽失敗")
        
    finally:
        await browser.close()
        await playwright.stop()
    
    print("\n🎯 Bot検出テスト完了!")
    print("スクリーンショットで詳細を確認してください。")

if __name__ == "__main__":
    asyncio.run(bot_detection_test())