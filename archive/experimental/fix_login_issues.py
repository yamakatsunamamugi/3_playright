#!/usr/bin/env python3
"""
AIサービスログイン問題修正スクリプト
Cloudflare回避、セッション復元、認証状態の改善
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
import json

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright

async def setup_stealth_browser():
    """ステルスブラウザの設定（bot検出回避）"""
    
    # より人間らしいブラウザ設定
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
        '--enable-features=NetworkService,NetworkServiceLogging',
        '--force-color-profile=srgb',
        '--metrics-recording-only',
        '--use-mock-keychain',
        '--disable-plugins',
        '--headless=new'  # 最新のヘッドレスモード
    ]
    
    # より詳細なユーザーエージェント
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    return browser_args, user_agent

async def setup_context_with_session(browser, service_name: str):
    """セッション復元付きコンテキスト設定"""
    
    # セッション保存ディレクトリ
    session_dir = Path("auth_states")
    session_dir.mkdir(exist_ok=True)
    session_file = session_dir / f"{service_name}_session.json"
    
    browser_args, user_agent = await setup_stealth_browser()
    
    # コンテキスト設定
    context_options = {
        'user_agent': user_agent,
        'viewport': {'width': 1920, 'height': 1080},
        'locale': 'ja-JP',
        'timezone_id': 'Asia/Tokyo',
        'permissions': ['notifications'],
        'extra_http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    
    # 保存されたセッションがあれば復元
    if session_file.exists():
        try:
            with open(session_file, 'r') as f:
                storage_state = json.load(f)
            context_options['storage_state'] = storage_state
            print(f"   🔄 {service_name}の保存済みセッションを復元")
        except Exception as e:
            print(f"   ⚠️  セッション復元失敗: {e}")
    
    context = await browser.new_context(**context_options)
    
    # Bot検出回避のJavaScript実行
    await context.add_init_script("""
        // navigator.webdriver を削除
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });

        // navigator.plugins を偽装
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });

        // navigator.languages を偽装
        Object.defineProperty(navigator, 'languages', {
            get: () => ['ja-JP', 'ja', 'en-US', 'en'],
        });

        // window.chrome を偽装
        window.chrome = {
            runtime: {},
        };

        // Permissions API を偽装
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // DeviceMotionEvent を偽装
        window.DeviceMotionEvent = undefined;
        window.DeviceOrientationEvent = undefined;
    """)
    
    return context, session_file

async def test_claude_access():
    """Claude のアクセステスト（Cloudflare回避）"""
    print("\n🔍 Claude アクセステスト開始")
    
    async with async_playwright() as p:
        browser_args, user_agent = await setup_stealth_browser()
        
        # ヘッドレス無効でテスト（Cloudflare回避）
        browser = await p.chromium.launch(
            headless=False,  # Cloudflare回避のため表示モード
            args=browser_args
        )
        
        try:
            context, session_file = await setup_context_with_session(browser, "claude")
            page = await context.new_page()
            
            print("   📡 Claude.aiにアクセス中...")
            
            # より自然なアクセスパターン
            await page.goto("https://claude.ai", wait_until='domcontentloaded', timeout=60000)
            
            # ページ読み込み完了まで待機
            await asyncio.sleep(5)
            
            # ページタイトル確認
            title = await page.title()
            print(f"   📄 ページタイトル: {title}")
            
            # Cloudflareチェック
            cloudflare_indicators = [
                "Checking your browser",
                "Please wait",
                "DDoS protection",
                "Cloudflare",
                "しばらくお待ちください"
            ]
            
            page_content = await page.content()
            is_cloudflare = any(indicator in page_content for indicator in cloudflare_indicators)
            
            if is_cloudflare:
                print("   🛡️  Cloudflare検出 - 手動確認が必要")
                print("   ⏳ Cloudflare認証完了まで30秒待機...")
                await asyncio.sleep(30)
                
                # 再度ページ確認
                title = await page.title()
                page_content = await page.content()
                print(f"   📄 認証後タイトル: {title}")
            
            # ログイン状態確認
            login_selectors = [
                'div[contenteditable="true"]',
                'div.ProseMirror',
                'textarea[placeholder*="Claude"]',
                'button[aria-label="Send Message"]'
            ]
            
            login_detected = False
            for selector in login_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        login_detected = True
                        print(f"   ✅ ログイン済み検出: {selector}")
                        break
                except:
                    continue
            
            if not login_detected:
                print("   🔐 ログインが必要 - 手動ログインしてください")
                print("   ⏳ ログイン完了まで60秒待機...")
                await asyncio.sleep(60)
            
            # セッション保存
            try:
                storage_state = await context.storage_state()
                with open(session_file, 'w') as f:
                    json.dump(storage_state, f)
                print(f"   💾 セッション保存: {session_file}")
            except Exception as e:
                print(f"   ❌ セッション保存失敗: {e}")
            
            # スクリーンショット撮影
            screenshot_path = f"screenshots/claude_login_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   📸 スクリーンショット: {screenshot_path}")
            
        finally:
            await browser.close()

async def test_chatgpt_proper_login():
    """ChatGPT の適切なログインテスト"""
    print("\n🔍 ChatGPT ログインテスト開始")
    
    async with async_playwright() as p:
        browser_args, user_agent = await setup_stealth_browser()
        
        browser = await p.chromium.launch(
            headless=False,
            args=browser_args
        )
        
        try:
            context, session_file = await setup_context_with_session(browser, "chatgpt")
            page = await context.new_page()
            
            print("   📡 ChatGPTにアクセス中...")
            await page.goto("https://chat.openai.com", wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # ログイン状態確認
            login_selectors = [
                'textarea[data-testid="textbox"]',
                'div[contenteditable="true"][data-placeholder]',
                'button[data-testid="send-button"]'
            ]
            
            login_detected = False
            for selector in login_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        login_detected = True
                        print(f"   ✅ ログイン済み検出: {selector}")
                        break
                except:
                    continue
            
            if not login_detected:
                print("   🔐 ログインが必要")
                # ログインボタンを探す
                login_button = await page.query_selector('button:has-text("Log in")')
                if login_button:
                    await login_button.click()
                    print("   🔄 ログインページにリダイレクト")
                    await asyncio.sleep(5)
            
            # モデル選択ボタンを探す（新しい方法）
            model_selectors = [
                'button[data-testid="model-switcher-button"]',
                'div[data-testid="model-switcher"]',
                'button:has-text("GPT")',
                'button:has-text("ChatGPT")',
                '[data-testid*="model"]'
            ]
            
            print("   🔍 モデル選択要素を検索...")
            for selector in model_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.text_content()
                        if text:
                            print(f"   📍 発見: {selector} -> '{text.strip()}'")
                except:
                    continue
            
            # セッション保存
            try:
                storage_state = await context.storage_state()
                with open(session_file, 'w') as f:
                    json.dump(storage_state, f)
                print(f"   💾 セッション保存: {session_file}")
            except Exception as e:
                print(f"   ❌ セッション保存失敗: {e}")
            
            # スクリーンショット撮影
            screenshot_path = f"screenshots/chatgpt_login_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   📸 スクリーンショット: {screenshot_path}")
            
        finally:
            await browser.close()

async def test_gemini_model_detection():
    """Gemini のモデル検出テスト"""
    print("\n🔍 Gemini モデル検出テスト開始")
    
    async with async_playwright() as p:
        browser_args, user_agent = await setup_stealth_browser()
        
        browser = await p.chromium.launch(
            headless=False,
            args=browser_args
        )
        
        try:
            context, session_file = await setup_context_with_session(browser, "gemini")
            page = await context.new_page()
            
            print("   📡 Geminiにアクセス中...")
            await page.goto("https://gemini.google.com", wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # モデル選択ドロップダウンを探す
            model_dropdown_selectors = [
                'button:has-text("Flash")',
                'button:has-text("Pro")',
                'button:has-text("2.5")',
                'div[data-testid="model-selector"]',
                '[aria-label*="model"]'
            ]
            
            print("   🔍 モデル選択ドロップダウンを検索...")
            model_button = None
            for selector in model_dropdown_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        print(f"   📍 発見: {selector} -> '{text.strip()}'")
                        if 'Flash' in text or 'Pro' in text:
                            model_button = element
                            break
                except:
                    continue
            
            if model_button:
                print("   🔄 モデル選択ドロップダウンをクリック...")
                await model_button.click()
                await asyncio.sleep(2)
                
                # 表示されたモデル一覧を取得
                model_option_selectors = [
                    'div[role="option"]',
                    'div[role="menuitem"]',
                    'li[role="option"]',
                    '[data-value]'
                ]
                
                models_found = []
                for selector in model_option_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            text = await element.text_content()
                            if text and ('Gemini' in text or 'Flash' in text or 'Pro' in text):
                                models_found.append(text.strip())
                    except:
                        continue
                
                if models_found:
                    print(f"   ✅ 検出されたモデル:")
                    for model in set(models_found):  # 重複除去
                        print(f"      • {model}")
                else:
                    print(f"   ❌ モデル一覧が取得できませんでした")
                
                # ドロップダウンを閉じる
                await page.keyboard.press('Escape')
            
            # スクリーンショット撮影
            screenshot_path = f"screenshots/gemini_model_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   📸 スクリーンショット: {screenshot_path}")
            
        finally:
            await browser.close()

async def main():
    print("🔧 AIサービス ログイン問題修正ツール")
    print("=" * 60)
    print("各AIサービスのログイン問題を診断・修正します")
    print()
    
    # スクリーンショット保存ディレクトリ
    Path("screenshots").mkdir(exist_ok=True)
    
    try:
        # 1. Claude のCloudflare問題修正
        await test_claude_access()
        
        # 2. ChatGPT の適切なログインとモデル検出
        await test_chatgpt_proper_login()
        
        # 3. Gemini のモデル検出改善
        await test_gemini_model_detection()
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 ログイン問題修正完了!")
    print("\n📋 次のステップ:")
    print("1. 各サービスのスクリーンショットを確認")
    print("2. 保存されたセッションファイルを確認")
    print("3. 必要に応じて手動ログインを完了")
    print("4. モデル取得機能を再テスト")

if __name__ == "__main__":
    asyncio.run(main())