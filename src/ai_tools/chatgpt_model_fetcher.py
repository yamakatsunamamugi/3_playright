"""
ChatGPTモデル情報取得モジュール

OpenAI APIまたはWebUIからChatGPTの最新モデル情報を取得する。
"""

import asyncio
import json
import re
from typing import List, Optional, Dict, Any
from playwright.async_api import Page, async_playwright, Browser

from .model_fetcher import (
    ModelFetcherBase, ModelInfo, SettingOption, 
    ModelProvider, CacheManager
)


class ChatGPTModelFetcher(ModelFetcherBase):
    """ChatGPT用のモデル情報取得クラス"""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """初期化"""
        super().__init__(ModelProvider.CHATGPT, cache_manager)
        self.api_key = None  # 必要に応じてAPIキーを設定
        self.chatgpt_url = "https://chatgpt.com"
    
    async def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        ChatGPTから最新のモデル情報を取得
        
        Returns:
            モデル情報リスト
        """
        # APIキーがある場合はAPI経由で取得を試みる
        if self.api_key:
            try:
                return await self._fetch_models_via_api()
            except Exception as e:
                self.logger.warning(f"API経由での取得失敗: {e}")
        
        # WebUI経由で取得
        return await self._fetch_models_via_webui()
    
    async def fetch_settings_from_source(self) -> List[SettingOption]:
        """
        ChatGPTから最新の設定オプションを取得
        
        Returns:
            設定オプションリスト
        """
        # WebUI経由で設定オプションを取得
        return await self._fetch_settings_via_webui()
    
    async def _fetch_models_via_api(self) -> List[ModelInfo]:
        """
        OpenAI API経由でモデル情報を取得
        
        Returns:
            モデル情報リスト
        """
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.openai.com/v1/models",
                headers=headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"API エラー: {response.status}")
                
                data = await response.json()
                models = []
                
                # GPTモデルのみをフィルタリング
                for model_data in data.get("data", []):
                    model_id = model_data.get("id", "")
                    if not any(model_id.startswith(prefix) for prefix in ["gpt-4", "gpt-3.5"]):
                        continue
                    
                    # モデル情報を作成
                    model = ModelInfo(
                        id=model_id,
                        name=model_id,
                        display_name=self._format_model_name(model_id),
                        description=self._get_model_description(model_id),
                        capabilities=self._get_model_capabilities(model_id),
                        is_default="gpt-4o" in model_id
                    )
                    models.append(model)
                
                # ソート（新しいモデルを上に）
                models.sort(key=lambda x: (not x.is_default, x.id), reverse=True)
                
                return models
    
    async def _fetch_models_via_webui(self) -> List[ModelInfo]:
        """
        WebUI経由でモデル情報を取得
        
        Returns:
            モデル情報リスト
        """
        async with async_playwright() as p:
            # 既存のChromeを使用する場合のオプション
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                page = await browser.new_page()
                await page.goto(self.chatgpt_url, wait_until="networkidle")
                
                # ログイン状態を確認
                await page.wait_for_timeout(3000)
                
                # モデル選択ドロップダウンを探す
                models = []
                
                # GPTセレクターのパターン（複数試行）
                selectors = [
                    'button[aria-haspopup="menu"]:has-text("GPT")',
                    'div[role="button"]:has-text("GPT")',
                    'button:has-text("Model:")',
                    '[data-testid="model-selector"]'
                ]
                
                model_selector = None
                for selector in selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        model_selector = selector
                        break
                    except:
                        continue
                
                if model_selector:
                    # モデル選択メニューを開く
                    await page.click(model_selector)
                    await page.wait_for_timeout(1000)
                    
                    # モデルオプションを取得
                    model_elements = await page.query_selector_all('div[role="menuitem"], button[role="menuitem"]')
                    
                    for element in model_elements:
                        text = await element.text_content()
                        if text:
                            # モデルIDとテキストを解析
                            model_info = self._parse_model_text(text.strip())
                            if model_info:
                                models.append(model_info)
                    
                    # メニューを閉じる
                    await page.keyboard.press('Escape')
                
                # モデルが見つからない場合はデフォルトを返す
                if not models:
                    self.logger.warning("WebUIからモデル情報を取得できませんでした")
                    return self.fallback_models
                
                return models
                
            finally:
                await browser.close()
    
    async def _fetch_settings_via_webui(self) -> List[SettingOption]:
        """
        WebUI経由で設定オプションを取得
        
        Returns:
            設定オプションリスト
        """
        settings = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                page = await browser.new_page()
                await page.goto(self.chatgpt_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # 設定メニューを探す
                settings_selectors = [
                    'button[aria-label="Settings"]',
                    'button:has-text("Settings")',
                    '[data-testid="settings-button"]'
                ]
                
                settings_found = False
                for selector in settings_selectors:
                    try:
                        await page.click(selector, timeout=5000)
                        settings_found = True
                        break
                    except:
                        continue
                
                if settings_found:
                    await page.wait_for_timeout(1000)
                    
                    # カスタム指示や設定項目を探す
                    custom_instructions = await page.query_selector('text="Custom instructions"')
                    if custom_instructions:
                        settings.append(SettingOption(
                            id="custom_instructions",
                            name="custom_instructions",
                            display_name="カスタム指示",
                            type="text",
                            description="ChatGPTの応答をカスタマイズする指示"
                        ))
                    
                    # 他の設定項目を探す
                    checkboxes = await page.query_selector_all('input[type="checkbox"]')
                    for checkbox in checkboxes:
                        label = await checkbox.evaluate('el => el.parentElement.textContent')
                        if label:
                            setting_id = re.sub(r'[^a-zA-Z0-9_]', '_', label.lower())
                            settings.append(SettingOption(
                                id=setting_id,
                                name=setting_id,
                                display_name=label,
                                type="boolean",
                                default_value=await checkbox.is_checked()
                            ))
                
                # 設定が見つからない場合はデフォルトを返す
                if not settings:
                    return self.fallback_settings
                
                return settings
                
            finally:
                await browser.close()
    
    def _format_model_name(self, model_id: str) -> str:
        """モデルIDを表示名にフォーマット"""
        # 例: "gpt-4o" -> "GPT-4o"
        name = model_id.upper().replace("-", " ")
        # 特殊なケースの処理
        name = name.replace("GPT 4O", "GPT-4o")
        name = name.replace("GPT 3.5", "GPT-3.5")
        return name
    
    def _get_model_description(self, model_id: str) -> str:
        """モデルIDから説明を生成"""
        descriptions = {
            "gpt-4o": "最新の高性能マルチモーダルモデル",
            "gpt-4o-mini": "高速・低コストのマルチモーダルモデル",
            "gpt-4-turbo": "GPT-4の高速版",
            "gpt-4": "高度な推論能力を持つモデル",
            "gpt-3.5-turbo": "高速で効率的なチャットモデル"
        }
        
        for key, desc in descriptions.items():
            if key in model_id.lower():
                return desc
        
        return "ChatGPTモデル"
    
    def _get_model_capabilities(self, model_id: str) -> List[str]:
        """モデルIDから能力リストを生成"""
        capabilities = ["chat"]
        
        if "vision" in model_id or "4o" in model_id:
            capabilities.append("vision")
        
        if "gpt-4" in model_id or "gpt-3.5-turbo" in model_id:
            capabilities.append("function_calling")
        
        if "32k" in model_id:
            capabilities.append("extended_context")
        elif "128k" in model_id:
            capabilities.append("super_extended_context")
        
        return capabilities
    
    def _parse_model_text(self, text: str) -> Optional[ModelInfo]:
        """
        UIのテキストからモデル情報を解析
        
        Args:
            text: UIから取得したテキスト
            
        Returns:
            モデル情報またはNone
        """
        # GPTモデルのパターンマッチング
        patterns = [
            r'(gpt-[\w\-\.]+)',
            r'(GPT-[\w\-\.]+)',
            r'(ChatGPT[\s\-][\w\-\.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                model_id = match.group(1).lower()
                # 正規化
                model_id = model_id.replace("chatgpt", "gpt").replace(" ", "-")
                
                return ModelInfo(
                    id=model_id,
                    name=model_id,
                    display_name=self._format_model_name(model_id),
                    description=self._extract_description_from_text(text),
                    capabilities=self._get_model_capabilities(model_id),
                    is_default="default" in text.lower() or "selected" in text.lower()
                )
        
        return None
    
    def _extract_description_from_text(self, text: str) -> str:
        """UIテキストから説明を抽出"""
        # 括弧内のテキストを説明として使用
        match = re.search(r'\((.*?)\)', text)
        if match:
            return match.group(1)
        
        # 説明的なキーワードを探す
        if "fast" in text.lower():
            return "高速モデル"
        elif "smart" in text.lower() or "advanced" in text.lower():
            return "高性能モデル"
        
        return ""