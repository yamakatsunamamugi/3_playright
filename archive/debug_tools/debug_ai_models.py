#!/usr/bin/env python3
"""
AIモデル情報デバッグスクリプト
各AIサービスのページを実際に開いて、スクリーンショット取得とDOM解析を行う
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright

async def debug_ai_service(service_name: str, url: str, screenshot_dir: Path):
    """個別AIサービスのデバッグ"""
    print(f"\n🔍 {service_name} のデバッグ開始")
    print(f"   📡 URL: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # ヘッドレス無効でブラウザ表示
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        try:
            page = await context.new_page()
            
            # ページを開く
            print(f"   ⏳ ページ読み込み中...")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)  # 動的コンテンツの読み込み待機
            
            # スクリーンショット撮影
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = screenshot_dir / f"{service_name.lower()}_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   📸 スクリーンショット保存: {screenshot_path}")
            
            # ページタイトル取得
            title = await page.title()
            print(f"   📄 ページタイトル: {title}")
            
            # ログイン状態の確認
            is_logged_in = await check_login_status(page, service_name)
            print(f"   🔐 ログイン状態: {'ログイン済み' if is_logged_in else 'ログイン必要'}")
            
            if is_logged_in:
                # モデル選択要素を探す
                await find_model_elements(page, service_name)
                
                # 設定要素を探す
                await find_setting_elements(page, service_name)
            else:
                print(f"   ⚠️  {service_name}にログインしてからモデル情報を取得してください")
            
            # DOM構造をファイルに保存
            html_content = await page.content()
            html_path = screenshot_dir / f"{service_name.lower()}_{timestamp}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   💾 HTML保存: {html_path}")
            
        finally:
            await browser.close()

async def check_login_status(page, service_name: str) -> bool:
    """ログイン状態をチェック"""
    try:
        if service_name.lower() == 'chatgpt':
            # ChatGPTのログイン確認
            selectors = [
                'textarea[data-testid="textbox"]',
                'div[contenteditable="true"]',
                'button[data-testid="send-button"]'
            ]
        elif service_name.lower() == 'claude':
            # Claudeのログイン確認
            selectors = [
                'div[contenteditable="true"]',
                'div.ProseMirror',
                'button[aria-label="Send Message"]'
            ]
        elif service_name.lower() == 'gemini':
            # Geminiのログイン確認
            selectors = [
                'rich-textarea',
                'div[contenteditable="true"]',
                'button[aria-label*="Send"]'
            ]
        else:
            return False
        
        for selector in selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element:
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        print(f"      ログイン状態確認エラー: {e}")
        return False

async def find_model_elements(page, service_name: str):
    """モデル選択要素を探す"""
    print(f"   🔍 モデル選択要素を検索中...")
    
    if service_name.lower() == 'chatgpt':
        selectors = [
            'button[data-testid="model-switcher-button"]',
            'button:has-text("GPT")',
            'div[data-testid="model-switcher"]',
            'button[aria-label*="model"]',
            '[data-testid*="model"]',
            'button:has-text("4o")',
            'button:has-text("o1")'
        ]
    elif service_name.lower() == 'claude':
        selectors = [
            'button[aria-label*="Model"]',
            'button:has-text("Claude")',
            'div[role="button"]:has-text("Model")',
            'button:has-text("Sonnet")',
            'button:has-text("Haiku")',
            'button:has-text("Opus")'
        ]
    elif service_name.lower() == 'gemini':
        selectors = [
            'button:has-text("Gemini")',
            'mat-select[aria-label*="model"]',
            'button[aria-label*="Select model"]',
            'button:has-text("Pro")',
            'button:has-text("Flash")'
        ]
    else:
        selectors = ['button', 'select', '[role="button"]']
    
    found_elements = []
    for selector in selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                text = await element.text_content()
                if text and text.strip():
                    found_elements.append(f"{selector}: '{text.strip()}'")
        except:
            continue
    
    if found_elements:
        print(f"   ✅ 見つかったモデル関連要素:")
        for element in found_elements[:10]:  # 上位10個
            print(f"      - {element}")
    else:
        print(f"   ❌ モデル選択要素が見つかりません")

async def find_setting_elements(page, service_name: str):
    """設定要素を探す"""
    print(f"   🔍 設定要素を検索中...")
    
    # 共通の設定関連セレクター
    setting_selectors = [
        'input[type="checkbox"]',
        'input[type="range"]',
        'select',
        'button:has-text("Settings")',
        'button:has-text("設定")',
        '[aria-label*="setting"]',
        '[data-testid*="setting"]'
    ]
    
    found_settings = []
    for selector in setting_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                # 要素の属性情報を取得
                tag_name = await element.evaluate('el => el.tagName')
                attributes = await element.evaluate('''el => {
                    const attrs = {};
                    for (let attr of el.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    return attrs;
                }''')
                
                text = await element.text_content()
                if text:
                    text = text.strip()[:50]  # 50文字まで
                
                found_settings.append({
                    'selector': selector,
                    'tag': tag_name,
                    'text': text,
                    'attributes': attributes
                })
        except:
            continue
    
    if found_settings:
        print(f"   ✅ 見つかった設定要素:")
        for setting in found_settings[:5]:  # 上位5個
            print(f"      - {setting['tag']}: {setting['text']} | {setting['selector']}")
    else:
        print(f"   ❌ 設定要素が見つかりません")

async def main():
    print("🕵️ AIモデル情報デバッグツール")
    print("=" * 60)
    print("各AIサービスのページを実際に開いて調査します")
    print("⚠️  事前に各AIサービスにログインしておいてください")
    print()
    
    # スクリーンショット保存ディレクトリ
    screenshot_dir = Path("screenshots/debug_models")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    # 調査対象のAIサービス
    services = [
        ('ChatGPT', 'https://chat.openai.com'),
        ('Claude', 'https://claude.ai'),
        ('Gemini', 'https://gemini.google.com'),
    ]
    
    for service_name, url in services:
        try:
            await debug_ai_service(service_name, url, screenshot_dir)
        except Exception as e:
            print(f"   ❌ {service_name} のデバッグに失敗: {e}")
        
        print(f"   ⏸️  次のサービスまで5秒待機...")
        await asyncio.sleep(5)
    
    print("\n🎯 デバッグ完了!")
    print(f"📁 結果は {screenshot_dir} に保存されました")
    print("\n📋 次のステップ:")
    print("1. スクリーンショットで各サービスの画面を確認")
    print("2. HTMLファイルで正確なセレクターを特定")
    print("3. 最新モデル一覧を手動で確認")
    print("4. セレクターを修正してモデル取得機能を改善")

if __name__ == "__main__":
    asyncio.run(main())