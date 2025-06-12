"""
Geminiモデル情報取得モジュール

Google AI APIまたはWebUIからGeminiの最新モデル情報を取得する。
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


class GeminiModelFetcher(ModelFetcherBase):
    """Gemini用のモデル情報取得クラス"""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """初期化"""
        super().__init__(ModelProvider.GEMINI, cache_manager)
        self.api_key = None  # 必要に応じてAPIキーを設定
        self.gemini_url = "https://gemini.google.com"
    
    async def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        Geminiから最新のモデル情報を取得
        
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
        Geminiから最新の設定オプションを取得
        
        Returns:
            設定オプションリスト
        """
        return await self._fetch_settings_via_webui()
    
    async def _fetch_models_via_api(self) -> List[ModelInfo]:
        """
        Google AI API経由でモデル情報を取得
        
        Returns:
            モデル情報リスト
        """
        import aiohttp
        
        # Google AI APIのモデル一覧エンドポイント
        api_url = f"https://generativelanguage.googleapis.com/v1/models?key={self.api_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status != 200:
                    raise Exception(f"API エラー: {response.status}")
                
                data = await response.json()
                models = []
                
                for model_data in data.get("models", []):
                    model_name = model_data.get("name", "")
                    # "models/" プレフィックスを削除
                    model_id = model_name.replace("models/", "")
                    
                    # Geminiモデルのみをフィルタ
                    if not model_id.startswith("gemini"):
                        continue
                    
                    model = ModelInfo(
                        id=model_id,
                        name=model_id,
                        display_name=model_data.get("displayName", self._format_model_name(model_id)),
                        description=model_data.get("description", ""),
                        context_length=model_data.get("inputTokenLimit", 0),
                        max_tokens=model_data.get("outputTokenLimit", 0),
                        capabilities=self._extract_capabilities_from_api(model_data),
                        is_default="2.0-flash" in model_id
                    )
                    models.append(model)
                
                # ソート（新しいモデルを上に）
                models.sort(key=lambda x: (not x.is_default, not "2.0" in x.id, x.id), reverse=True)
                
                return models
    
    async def _fetch_models_via_webui(self) -> List[ModelInfo]:
        """
        WebUI経由でモデル情報を取得
        
        Returns:
            モデル情報リスト
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                page = await browser.new_page()
                await page.goto(self.gemini_url, wait_until="networkidle")
                
                # ログイン状態を確認
                await page.wait_for_timeout(3000)
                
                models = []
                
                # モデル選択要素のセレクター
                selectors = [
                    'button[aria-label*="model"]',
                    'button:has-text("Gemini")',
                    '[data-model-selector]',
                    'div[role="button"]:has-text("Gemini")'
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
                    model_elements = await page.query_selector_all('[role="option"], [role="menuitem"], [data-value*="gemini"]')
                    
                    for element in model_elements:
                        text = await element.text_content()
                        if text:
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
                await page.goto(self.gemini_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # 設定メニューを探す
                settings_selectors = [
                    'button[aria-label*="Settings"]',
                    'button[aria-label*="設定"]',
                    'button:has-text("Settings")',
                    '[data-settings-button]'
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
                    
                    # Gemini特有の設定を探す
                    
                    # レスポンスの長さ設定
                    length_setting = await page.query_selector('text="Response length"')
                    if length_setting:
                        settings.append(SettingOption(
                            id="response_length",
                            name="response_length",
                            display_name="応答の長さ",
                            type="select",
                            options=["短い", "中程度", "長い"],
                            default_value="中程度",
                            description="生成される応答の長さ"
                        ))
                    
                    # 拡張機能設定
                    extensions = await page.query_selector('text="Extensions"')
                    if extensions:
                        settings.append(SettingOption(
                            id="use_extensions",
                            name="use_extensions",
                            display_name="拡張機能",
                            type="boolean",
                            default_value=True,
                            description="Google Workspace連携などの拡張機能"
                        ))
                    
                    # リアルタイム情報アクセス
                    realtime = await page.query_selector('text="Real-time"')
                    if realtime:
                        settings.append(SettingOption(
                            id="realtime_access",
                            name="realtime_access",
                            display_name="リアルタイム情報",
                            type="boolean",
                            default_value=True,
                            description="最新情報へのアクセスを許可"
                        ))
                
                # 基本的な設定オプション
                settings.extend([
                    SettingOption(
                        id="temperature",
                        name="temperature",
                        display_name="Temperature",
                        type="number",
                        default_value=0.9,
                        min_value=0.0,
                        max_value=2.0,
                        description="出力のランダム性を制御"
                    ),
                    SettingOption(
                        id="top_p",
                        name="top_p",
                        display_name="Top P",
                        type="number",
                        default_value=0.95,
                        min_value=0.0,
                        max_value=1.0,
                        description="累積確率による出力の多様性制御"
                    ),
                    SettingOption(
                        id="top_k",
                        name="top_k",
                        display_name="Top K",
                        type="number",
                        default_value=40,
                        min_value=1,
                        max_value=100,
                        description="考慮する上位トークン数"
                    ),
                    SettingOption(
                        id="max_output_tokens",
                        name="max_output_tokens",
                        display_name="最大出力トークン",
                        type="number",
                        default_value=2048,
                        min_value=1,
                        max_value=8192,
                        description="生成する最大トークン数"
                    )
                ])
                
                return settings
                
            finally:
                await browser.close()
    
    def _format_model_name(self, model_id: str) -> str:
        """モデルIDを表示名にフォーマット"""
        # 例: "gemini-1.5-pro" -> "Gemini 1.5 Pro"
        name = model_id.replace("-", " ").title()
        name = name.replace("Gemini", "Gemini")
        name = name.replace("Pro", "Pro")
        name = name.replace("Flash", "Flash")
        name = name.replace("Exp", "(Experimental)")
        return name
    
    def _extract_capabilities_from_api(self, model_data: Dict[str, Any]) -> List[str]:
        """APIレスポンスから能力を抽出"""
        capabilities = []
        
        supported_methods = model_data.get("supportedGenerationMethods", [])
        if "generateContent" in supported_methods:
            capabilities.append("chat")
        if "embedContent" in supported_methods:
            capabilities.append("embeddings")
        
        # モデル名から推測
        model_name = model_data.get("name", "")
        if "vision" in model_name.lower() or "pro" in model_name.lower():
            capabilities.append("vision")
        
        if "1.5" in model_name or "2.0" in model_name:
            capabilities.append("long_context")
            capabilities.append("function_calling")
        
        return capabilities
    
    def _parse_model_text(self, text: str) -> Optional[ModelInfo]:
        """
        UIのテキストからモデル情報を解析
        
        Args:
            text: UIから取得したテキスト
            
        Returns:
            モデル情報またはNone
        """
        # Geminiモデルのパターン
        patterns = [
            r'gemini-2\.0-flash(?:-exp)?',
            r'gemini-1\.5-pro(?:-\w+)?',
            r'gemini-1\.5-flash(?:-\w+)?',
            r'gemini-pro',
            r'Gemini\s*2\.0\s*Flash',
            r'Gemini\s*1\.5\s*Pro',
            r'Gemini\s*1\.5\s*Flash',
            r'Gemini\s*Pro'
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # モデルIDを生成
                model_id = self._extract_model_id(text)
                if not model_id:
                    continue
                
                # コンテキスト長を推定
                context_length = self._estimate_context_length(model_id)
                
                # デフォルトかどうかを判定
                is_default = any(keyword in text.lower() for keyword in ["default", "selected", "recommended", "最新"])
                
                return ModelInfo(
                    id=model_id,
                    name=model_id,
                    display_name=self._format_model_name(model_id),
                    description=self._extract_description(text),
                    context_length=context_length,
                    capabilities=self._extract_capabilities(model_id),
                    is_default=is_default or "2.0-flash" in model_id
                )
        
        return None
    
    def _extract_model_id(self, text: str) -> Optional[str]:
        """テキストからモデルIDを抽出"""
        # 正規表現でモデルIDを抽出
        id_pattern = r'(gemini-(?:2\.0|1\.5|pro)(?:-(?:flash|pro))?(?:-(?:exp|latest))?)'
        match = re.search(id_pattern, text.lower())
        if match:
            return match.group(1)
        
        # 表示名からIDを推測
        if "2.0 flash" in text.lower():
            if "experimental" in text.lower():
                return "gemini-2.0-flash-exp"
            return "gemini-2.0-flash"
        elif "1.5 pro" in text.lower():
            return "gemini-1.5-pro"
        elif "1.5 flash" in text.lower():
            return "gemini-1.5-flash"
        elif "gemini pro" in text.lower():
            return "gemini-pro"
        
        return None
    
    def _extract_description(self, text: str) -> str:
        """テキストから説明を抽出"""
        # 括弧内のテキスト
        desc_pattern = r'\((.*?)\)'
        match = re.search(desc_pattern, text)
        if match:
            return match.group(1)
        
        # キーワードベースの説明
        if "2.0" in text:
            if "experimental" in text.lower():
                return "最新の実験的モデル、高速で高性能"
            return "最新世代の高速モデル"
        elif "1.5 pro" in text.lower():
            return "高性能な長文コンテキスト対応モデル"
        elif "1.5 flash" in text.lower():
            return "高速で効率的なモデル"
        elif "pro" in text.lower():
            return "バランスの取れた汎用モデル"
        
        return "Geminiモデル"
    
    def _estimate_context_length(self, model_id: str) -> int:
        """モデルIDからコンテキスト長を推定"""
        if "2.0" in model_id:
            return 1048576  # 1M tokens
        elif "1.5-pro" in model_id:
            return 2097152  # 2M tokens
        elif "1.5-flash" in model_id:
            return 1048576  # 1M tokens
        else:
            return 32768    # 32K tokens (gemini-pro)
    
    def _extract_capabilities(self, model_id: str) -> List[str]:
        """モデルIDから能力を推定"""
        capabilities = ["chat"]
        
        # すべてのGeminiモデルは画像認識対応
        capabilities.append("vision")
        
        # 1.5以降は長文コンテキストと関数呼び出し対応
        if "1.5" in model_id or "2.0" in model_id:
            capabilities.append("long_context")
            capabilities.append("function_calling")
            capabilities.append("code_execution")
        
        # 2.0は音声対応
        if "2.0" in model_id:
            capabilities.append("audio")
            capabilities.append("real_time")
        
        return capabilities