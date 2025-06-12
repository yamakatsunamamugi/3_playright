#!/usr/bin/env python3
"""
シンプルなステルステスト
独自のBot検出回避スクリプトをテスト
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from playwright.async_api import async_playwright

async def simple_stealth_test():
    """シンプルなステルステスト"""
    print("🔍 シンプルステルステスト開始")
    print("=" * 50)
    
    playwright = await async_playwright().start()
    
    # より高度なブラウザ設定
    browser_args = [
        '--no-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-field-trial-config',
        '--disable-ipc-flooding-protection',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-default-apps',
        '--no-first-run'
    ]
    
    browser = await playwright.chromium.launch(
        headless=False,
        args=browser_args
    )
    
    try:
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # 高度なBot検出回避スクリプト
        await context.add_init_script("""
            // 1. navigator.webdriver を完全に削除
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 2. window.chrome を偽装
            window.chrome = {
                runtime: {},
                csi: function() {},
                loadTimes: function() {},
                app: {}
            };
            
            // 3. navigator.plugins を偽装
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin' },
                    { name: 'Chrome PDF Viewer' },
                    { name: 'Native Client' }
                ],
            });
            
            // 4. navigator.languages を偽装
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ja-JP', 'ja', 'en-US', 'en'],
            });
            
            // 5. Permissions API を偽装
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 6. DeviceMotionEvent を削除
            window.DeviceMotionEvent = undefined;
            window.DeviceOrientationEvent = undefined;
            
            // 7. Battery API を削除
            delete navigator.getBattery;
            
            // 8. Connection API を偽装
            Object.defineProperty(navigator, 'connection', {
                get: () => ({ effectiveType: '4g', rtt: 50 })
            });
            
            // 9. 自動化関連プロパティを隠蔽
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // 10. document.documentElement の属性を削除
            document.addEventListener('DOMContentLoaded', function() {
                if (document.documentElement.getAttribute('webdriver')) {
                    document.documentElement.removeAttribute('webdriver');
                }
            });
        """)
        
        page = await context.new_page()
        
        print("\n📡 bot.sannysoft.com でテスト中...")
        await page.goto('https://bot.sannysoft.com/', wait_until='networkidle')
        await asyncio.sleep(5)
        
        await page.screenshot(path='stealth_test_result.png', full_page=True)
        print("   📸 スクリーンショット: stealth_test_result.png")
        
        # フィンガープリント確認
        fp_result = await page.evaluate("""
            () => {
                return {
                    userAgent: navigator.userAgent,
                    webdriver: navigator.webdriver,
                    languages: navigator.languages,
                    plugins: Array.from(navigator.plugins).map(p => p.name),
                    chrome: window.chrome ? 'exists' : 'missing',
                    permissions: navigator.permissions ? 'exists' : 'missing',
                    battery: navigator.getBattery ? 'exists' : 'missing',
                    connection: navigator.connection ? 'exists' : 'missing'
                }
            }
        """)
        
        print("\n🔍 ステルスフィンガープリント:")
        print(json.dumps(fp_result, indent=4, ensure_ascii=False))
        
        # より詳細な検出テスト
        detection_tests = await page.evaluate("""
            () => {
                const tests = {};
                
                // webdriver検出
                tests.webdriver = navigator.webdriver;
                
                // 自動化検出
                tests.automation = window.navigator.webdriver || 
                                 window.cdc_adoQpoasnfa76pfcZLmcfl_Array ||
                                 window.fmget_targets ||
                                 window.domAutomation ||
                                 window.domAutomationController;
                
                // Chrome検出
                tests.chrome = window.chrome && window.chrome.runtime;
                
                // プラグイン数
                tests.pluginCount = navigator.plugins.length;
                
                // 言語設定
                tests.languages = navigator.languages;
                
                // ヘッドレス検出のヒント
                tests.outerHeight = window.outerHeight;
                tests.outerWidth = window.outerWidth;
                
                return tests;
            }
        """)
        
        print("\n🧪 詳細検出テスト:")
        print(json.dumps(detection_tests, indent=4, ensure_ascii=False))
        
        # areyouheadless.com でもテスト
        print("\n📡 areyouheadless.com でテスト中...")
        await page.goto('https://areyouheadless.com/', wait_until='networkidle')
        await asyncio.sleep(3)
        
        headless_content = await page.text_content('body')
        print(f"   🎯 Headless検出: {headless_content[:100]}...")
        
        await page.screenshot(path='headless_stealth_test.png', full_page=True)
        print("   📸 スクリーンショット: headless_stealth_test.png")
        
        # 成果判定
        print("\n📊 ステルス成果:")
        print("-" * 30)
        
        success_count = 0
        total_tests = 0
        
        if not detection_tests.get('webdriver'):
            print("✅ webdriver隠蔽成功")
            success_count += 1
        else:
            print("❌ webdriver検出された")
        total_tests += 1
        
        if not detection_tests.get('automation'):
            print("✅ 自動化検出回避成功")
            success_count += 1
        else:
            print("❌ 自動化が検出された")
        total_tests += 1
        
        if detection_tests.get('chrome'):
            print("✅ Chrome偽装成功")
            success_count += 1
        else:
            print("❌ Chrome偽装失敗")
        total_tests += 1
        
        if detection_tests.get('pluginCount', 0) > 0:
            print("✅ プラグイン偽装成功")
            success_count += 1
        else:
            print("❌ プラグイン偽装失敗")
        total_tests += 1
        
        print(f"\n🎯 ステルス成功率: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
        
        await context.close()
        
    finally:
        await browser.close()
        await playwright.stop()
    
    print("\n✅ シンプルステルステスト完了!")

if __name__ == "__main__":
    asyncio.run(simple_stealth_test())