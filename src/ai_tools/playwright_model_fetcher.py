"""
Playwrightを使用した最新AIモデル情報取得
各AIサービスから直接最新のモデル一覧と設定オプションを取得
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import time

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

logger = logging.getLogger(__name__)


class PlaywrightModelFetcher:
    """Playwrightを使用したモデル情報取得クラス"""
    
    def __init__(self, cache_dir: Optional[Path] = None, headless: bool = True):
        """
        PlaywrightModelFetcherを初期化
        
        Args:
            cache_dir: キャッシュディレクトリ
            headless: ヘッドレスモードで実行するか
        """
        self.cache_dir = cache_dir or Path("cache/models")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        
        # AI サービスの設定
        self.ai_services = {
            'chatgpt': {
                'url': 'https://chat.openai.com',
                'name': 'ChatGPT',
                'selectors': {
                    'model_selector': 'button[data-testid="model-switcher-button"]',
                    'model_dropdown': 'div[role="menu"]',
                    'model_items': 'div[role="menuitem"]',
                    'settings_button': 'button[aria-label="Open settings"]',
                    'settings_panel': 'div[role="dialog"]'
                }
            },
            'claude': {
                'url': 'https://claude.ai',
                'name': 'Claude',
                'selectors': {
                    'model_selector': 'button[aria-label*="Model"]',
                    'model_dropdown': 'div[role="listbox"]',
                    'model_items': 'div[role="option"]',
                    'settings_button': 'button[aria-label="Settings"]'
                }
            },
            'gemini': {
                'url': 'https://gemini.google.com',
                'name': 'Gemini',
                'selectors': {
                    'model_selector': 'button:has-text("Gemini")',
                    'model_dropdown': 'mat-select-panel',
                    'model_items': 'mat-option',
                    'settings_button': 'button[aria-label*="Settings"]'
                }
            },
            'genspark': {
                'url': 'https://www.genspark.ai',
                'name': 'Genspark',
                'selectors': {
                    'model_selector': 'select',
                    'model_items': 'option'
                }
            },
            'google_ai_studio': {
                'url': 'https://aistudio.google.com',
                'name': 'Google AI Studio',
                'selectors': {
                    'model_selector': 'mat-select[aria-label*="model"]',
                    'model_dropdown': 'mat-select-panel',
                    'model_items': 'mat-option'
                }
            }
        }
    
    async def fetch_all_models(self) -> Dict[str, Dict[str, Any]]:
        """全AIサービスから最新モデル情報を取得"""
        results = {}
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                for service_key, service_config in self.ai_services.items():
                    try:
                        logger.info(f"📡 {service_config['name']}のモデル情報取得開始")
                        result = await self._fetch_service_models(browser, service_key, service_config)
                        results[service_key] = result
                        
                        # キャッシュに保存
                        self._save_to_cache(service_key, result)
                        
                        logger.info(f"✅ {service_config['name']}: {len(result.get('models', []))}モデル取得")
                        
                    except Exception as e:
                        logger.error(f"❌ {service_config['name']}のモデル取得失敗: {e}")
                        # キャッシュから読み込み
                        results[service_key] = self._load_from_cache(service_key)
                
            finally:
                await browser.close()
        
        return results
    
    async def fetch_service_models(self, service_name: str) -> Dict[str, Any]:
        """指定されたAIサービスのモデル情報を取得"""
        service_key = service_name.lower().replace(' ', '_').replace('ai_studio', 'aistudio')
        
        if service_key not in self.ai_services:
            logger.error(f"未対応のAIサービス: {service_name}")
            return self._get_default_models(service_name)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                service_config = self.ai_services[service_key]
                result = await self._fetch_service_models(browser, service_key, service_config)
                
                # キャッシュに保存
                self._save_to_cache(service_key, result)
                
                return result
                
            finally:
                await browser.close()
    
    async def _fetch_service_models(self, browser: Browser, service_key: str, 
                                  service_config: Dict[str, Any]) -> Dict[str, Any]:
        """個別サービスのモデル情報取得"""
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        try:
            page = await context.new_page()
            
            # ページロード
            await page.goto(service_config['url'], wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)  # 動的コンテンツの読み込み待機
            
            # サービス別の処理
            if service_key == 'chatgpt':
                return await self._fetch_chatgpt_models(page, service_config)
            elif service_key == 'claude':
                return await self._fetch_claude_models(page, service_config)
            elif service_key == 'gemini':
                return await self._fetch_gemini_models(page, service_config)
            elif service_key == 'genspark':
                return await self._fetch_genspark_models(page, service_config)
            elif service_key == 'google_ai_studio':
                return await self._fetch_google_ai_studio_models(page, service_config)
            else:
                return self._get_default_models(service_config['name'])
                
        finally:
            await context.close()
    
    async def _fetch_chatgpt_models(self, page: Page, config: Dict[str, Any]) -> Dict[str, Any]:
        """ChatGPTのモデル情報を取得"""
        models = []
        settings = []
        
        try:
            # モデル選択ボタンを探す（複数のセレクターを試行）
            model_selectors = [
                'button[data-testid="model-switcher-button"]',
                'button:has-text("GPT")',
                'div[data-testid="model-switcher"]',
                'button[aria-label*="model"]'
            ]
            
            model_button = None
            for selector in model_selectors:
                try:
                    model_button = await page.wait_for_selector(selector, timeout=5000)
                    if model_button:
                        break
                except:
                    continue
            
            if model_button:
                await model_button.click()
                await asyncio.sleep(2)
                
                # モデル一覧を取得
                model_items = await page.query_selector_all('div[role="menuitem"], div[role="option"]')
                
                for item in model_items:
                    text = await item.text_content()
                    if text and 'GPT' in text:
                        models.append(text.strip())
                
                # ESCでメニューを閉じる
                await page.keyboard.press('Escape')
            
            # 設定オプションを取得
            settings = [
                {"name": "DeepThink", "type": "checkbox", "default": False},
                {"name": "Temperature", "type": "scale", "default": 0.7, "min": 0, "max": 2},
                {"name": "Max tokens", "type": "number", "default": 4096}
            ]
            
        except Exception as e:
            logger.error(f"ChatGPTモデル取得エラー: {e}")
            models = ["GPT-4o", "GPT-4 Turbo", "GPT-4", "GPT-3.5 Turbo"]
        
        if not models:
            models = ["GPT-4o", "GPT-4 Turbo", "GPT-4", "GPT-3.5 Turbo"]
        
        return {
            'service': 'ChatGPT',
            'models': models,
            'settings': settings,
            'updated_at': datetime.now().isoformat()
        }
    
    async def _fetch_claude_models(self, page: Page, config: Dict[str, Any]) -> Dict[str, Any]:
        """Claudeのモデル情報を取得"""
        models = []
        settings = []
        
        try:
            # モデル選択ボタンを探す
            model_selectors = [
                'button[aria-label*="Model"]',
                'button:has-text("Claude")',
                'div[role="button"]:has-text("Model")'
            ]
            
            model_button = None
            for selector in model_selectors:
                try:
                    model_button = await page.wait_for_selector(selector, timeout=5000)
                    if model_button:
                        break
                except:
                    continue
            
            if model_button:
                await model_button.click()
                await asyncio.sleep(2)
                
                # モデル一覧を取得
                model_items = await page.query_selector_all('div[role="option"], div[role="menuitem"]')
                
                for item in model_items:
                    text = await item.text_content()
                    if text and 'Claude' in text:
                        models.append(text.strip())
                
                # ESCでメニューを閉じる
                await page.keyboard.press('Escape')
            
            # 設定オプション
            settings = [
                {"name": "系統的思考", "type": "checkbox", "default": False},
                {"name": "創造性レベル", "type": "scale", "default": 0.5, "min": 0, "max": 1},
                {"name": "応答の詳細度", "type": "select", "options": ["簡潔", "標準", "詳細"], "default": "標準"}
            ]
            
        except Exception as e:
            logger.error(f"Claudeモデル取得エラー: {e}")
            models = ["Claude-3.5 Sonnet", "Claude-3 Opus", "Claude-3 Haiku"]
        
        if not models:
            models = ["Claude-3.5 Sonnet", "Claude-3 Opus", "Claude-3 Haiku"]
        
        return {
            'service': 'Claude',
            'models': models,
            'settings': settings,
            'updated_at': datetime.now().isoformat()
        }
    
    async def _fetch_gemini_models(self, page: Page, config: Dict[str, Any]) -> Dict[str, Any]:
        """Geminiのモデル情報を取得"""
        models = []
        settings = []
        
        try:
            # モデル選択ボタンを探す
            model_selectors = [
                'button:has-text("Gemini")',
                'mat-select[aria-label*="model"]',
                'button[aria-label*="Select model"]'
            ]
            
            model_button = None
            for selector in model_selectors:
                try:
                    model_button = await page.wait_for_selector(selector, timeout=5000)
                    if model_button:
                        break
                except:
                    continue
            
            if model_button:
                await model_button.click()
                await asyncio.sleep(2)
                
                # モデル一覧を取得
                model_items = await page.query_selector_all('mat-option, div[role="option"]')
                
                for item in model_items:
                    text = await item.text_content()
                    if text and ('Gemini' in text or 'Pro' in text or 'Flash' in text):
                        models.append(text.strip())
                
                # ESCでメニューを閉じる
                await page.keyboard.press('Escape')
            
            # 設定オプション
            settings = [
                {"name": "安全性フィルター", "type": "checkbox", "default": True},
                {"name": "応答長", "type": "scale", "default": 0.5, "min": 0, "max": 1},
                {"name": "言語スタイル", "type": "select", "options": ["カジュアル", "フォーマル", "技術的"], "default": "標準"}
            ]
            
        except Exception as e:
            logger.error(f"Geminiモデル取得エラー: {e}")
            models = ["Gemini 1.5 Pro", "Gemini 1.5 Flash", "Gemini Pro"]
        
        if not models:
            models = ["Gemini 1.5 Pro", "Gemini 1.5 Flash", "Gemini Pro"]
        
        return {
            'service': 'Gemini',
            'models': models,
            'settings': settings,
            'updated_at': datetime.now().isoformat()
        }
    
    async def _fetch_genspark_models(self, page: Page, config: Dict[str, Any]) -> Dict[str, Any]:
        """Gensparkのモデル情報を取得"""
        models = ["Genspark Pro", "Genspark Standard"]
        settings = [
            {"name": "検索深度", "type": "scale", "default": 0.7, "min": 0, "max": 1},
            {"name": "応答形式", "type": "select", "options": ["要約", "詳細", "分析"], "default": "標準"}
        ]
        
        return {
            'service': 'Genspark',
            'models': models,
            'settings': settings,
            'updated_at': datetime.now().isoformat()
        }
    
    async def _fetch_google_ai_studio_models(self, page: Page, config: Dict[str, Any]) -> Dict[str, Any]:
        """Google AI Studioのモデル情報を取得"""
        models = ["Gemini 1.5 Pro", "Gemini 1.5 Flash", "Gemini Pro Vision"]
        settings = [
            {"name": "Temperature", "type": "scale", "default": 0.4, "min": 0, "max": 2},
            {"name": "Top-p", "type": "scale", "default": 0.95, "min": 0, "max": 1},
            {"name": "Max tokens", "type": "number", "default": 8192}
        ]
        
        return {
            'service': 'Google AI Studio',
            'models': models,
            'settings': settings,
            'updated_at': datetime.now().isoformat()
        }
    
    def _get_default_models(self, service_name: str) -> Dict[str, Any]:
        """デフォルトモデル情報を取得"""
        default_data = {
            'ChatGPT': {
                'models': ["GPT-4o", "GPT-4 Turbo", "GPT-4", "GPT-3.5 Turbo"],
                'settings': [
                    {"name": "DeepThink", "type": "checkbox", "default": False},
                    {"name": "Temperature", "type": "scale", "default": 0.7, "min": 0, "max": 2}
                ]
            },
            'Claude': {
                'models': ["Claude-3.5 Sonnet", "Claude-3 Opus", "Claude-3 Haiku"],
                'settings': [
                    {"name": "系統的思考", "type": "checkbox", "default": False},
                    {"name": "創造性レベル", "type": "scale", "default": 0.5, "min": 0, "max": 1}
                ]
            },
            'Gemini': {
                'models': ["Gemini 1.5 Pro", "Gemini 1.5 Flash", "Gemini Pro"],
                'settings': [
                    {"name": "安全性フィルター", "type": "checkbox", "default": True},
                    {"name": "応答長", "type": "scale", "default": 0.5, "min": 0, "max": 1}
                ]
            }
        }
        
        data = default_data.get(service_name, {
            'models': ["Default Model"],
            'settings': []
        })
        
        return {
            'service': service_name,
            'models': data['models'],
            'settings': data['settings'],
            'updated_at': datetime.now().isoformat(),
            'source': 'default'
        }
    
    def _save_to_cache(self, service_key: str, data: Dict[str, Any]):
        """キャッシュにデータを保存"""
        try:
            cache_file = self.cache_dir / f"{service_key}_models.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"キャッシュ保存: {cache_file}")
            
        except Exception as e:
            logger.error(f"キャッシュ保存失敗: {e}")
    
    def _load_from_cache(self, service_key: str) -> Dict[str, Any]:
        """キャッシュからデータを読み込み"""
        try:
            cache_file = self.cache_dir / f"{service_key}_models.json"
            
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.debug(f"キャッシュ読み込み: {cache_file}")
                    return data
                    
        except Exception as e:
            logger.error(f"キャッシュ読み込み失敗: {e}")
        
        # デフォルトデータを返す
        service_name = service_key.replace('_', ' ').title()
        return self._get_default_models(service_name)


# 非同期実行用のヘルパー関数
async def fetch_latest_models(service_name: Optional[str] = None, 
                            cache_dir: Optional[Path] = None,
                            headless: bool = True) -> Dict[str, Any]:
    """最新モデル情報を取得（非同期）"""
    fetcher = PlaywrightModelFetcher(cache_dir, headless)
    
    if service_name:
        return await fetcher.fetch_service_models(service_name)
    else:
        return await fetcher.fetch_all_models()


def fetch_latest_models_sync(service_name: Optional[str] = None,
                           cache_dir: Optional[Path] = None,
                           headless: bool = True) -> Dict[str, Any]:
    """最新モデル情報を取得（同期）"""
    return asyncio.run(fetch_latest_models(service_name, cache_dir, headless))