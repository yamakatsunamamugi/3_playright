"""
Claudeモデル情報取得モジュール

Anthropic APIまたはWebUIからClaudeの最新モデル情報を取得する。
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


class ClaudeModelFetcher(ModelFetcherBase):
    """Claude用のモデル情報取得クラス"""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """初期化"""
        super().__init__(ModelProvider.CLAUDE, cache_manager)
        self.api_key = None  # 必要に応じてAPIキーを設定
        self.claude_url = "https://claude.ai"
    
    async def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        Claudeから最新のモデル情報を取得
        
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
        Claudeから最新の設定オプションを取得
        
        Returns:
            設定オプションリスト
        """
        # WebUI経由で設定オプションを取得
        return await self._fetch_settings_via_webui()
    
    async def _fetch_models_via_api(self) -> List[ModelInfo]:
        """
        Anthropic API経由でモデル情報を取得
        
        Returns:
            モデル情報リスト
        """
        import aiohttp
        
        # Anthropic APIはモデル一覧エンドポイントを提供していないため、
        # 既知のモデルリストを使用
        known_models = [
            {
                "id": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet",
                "description": "最新の高性能モデル、優れた推論能力と創造性",
                "context_length": 200000,
                "is_latest": True
            },
            {
                "id": "claude-3-5-haiku-20241022",
                "name": "Claude 3.5 Haiku",
                "description": "高速・低コストモデル、日常的なタスクに最適",
                "context_length": 200000,
                "is_latest": True
            },
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "description": "最高性能モデル、複雑なタスクに対応",
                "context_length": 200000
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "description": "バランスの取れた性能とコスト",
                "context_length": 200000
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "description": "高速応答、シンプルなタスク向け",
                "context_length": 200000
            }
        ]
        
        models = []
        for model_data in known_models:
            model = ModelInfo(
                id=model_data["id"],
                name=model_data["id"],
                display_name=model_data["name"],
                description=model_data["description"],
                context_length=model_data["context_length"],
                capabilities=["chat", "vision"] if "opus" in model_data["id"] or "sonnet" in model_data["id"] else ["chat"],
                is_default=model_data.get("is_latest", False) and "sonnet" in model_data["id"]
            )
            models.append(model)
        
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
                await page.goto(self.claude_url, wait_until="networkidle")
                
                # ログイン状態を確認
                await page.wait_for_timeout(3000)
                
                models = []
                
                # モデル選択要素のセレクター（複数パターン）
                selectors = [
                    'button[aria-label*="Model"]',
                    'button:has-text("Claude")',
                    '[data-testid="model-selector"]',
                    'div[role="button"]:has-text("Claude")'
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
                    model_elements = await page.query_selector_all('[role="option"], [role="menuitem"]')
                    
                    for element in model_elements:
                        text = await element.text_content()
                        if text and "claude" in text.lower():
                            # モデル情報を解析
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
                await page.goto(self.claude_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # 設定に関連する要素を探す
                # Claude特有の設定オプション
                
                # Artifacts設定
                artifacts_toggle = await page.query_selector('text="Artifacts"')
                if artifacts_toggle:
                    settings.append(SettingOption(
                        id="artifacts",
                        name="artifacts",
                        display_name="Artifacts",
                        type="boolean",
                        default_value=True,
                        description="コードやドキュメントを別パネルで表示"
                    ))
                
                # プロジェクト機能
                projects = await page.query_selector('text="Projects"')
                if projects:
                    settings.append(SettingOption(
                        id="use_projects",
                        name="use_projects",
                        display_name="プロジェクト機能",
                        type="boolean",
                        default_value=False,
                        description="会話をプロジェクトとして管理"
                    ))
                
                # 応答スタイル設定を探す
                style_selectors = [
                    'button:has-text("Style")',
                    '[aria-label*="response style"]'
                ]
                
                for selector in style_selectors:
                    try:
                        style_element = await page.query_selector(selector)
                        if style_element:
                            settings.append(SettingOption(
                                id="response_style",
                                name="response_style",
                                display_name="応答スタイル",
                                type="select",
                                options=["簡潔", "標準", "詳細"],
                                default_value="標準",
                                description="Claudeの応答の詳細度"
                            ))
                            break
                    except:
                        continue
                
                # 基本的な設定オプション
                settings.extend([
                    SettingOption(
                        id="max_tokens",
                        name="max_tokens",
                        display_name="最大トークン数",
                        type="number",
                        default_value=4096,
                        min_value=1,
                        max_value=4096,
                        description="生成する最大トークン数"
                    ),
                    SettingOption(
                        id="temperature",
                        name="temperature",
                        display_name="Temperature",
                        type="number",
                        default_value=1.0,
                        min_value=0.0,
                        max_value=1.0,
                        description="出力のランダム性（Claudeでは通常1.0固定）"
                    )
                ])
                
                return settings
                
            finally:
                await browser.close()
    
    def _parse_model_text(self, text: str) -> Optional[ModelInfo]:
        """
        UIのテキストからモデル情報を解析
        
        Args:
            text: UIから取得したテキスト
            
        Returns:
            モデル情報またはNone
        """
        # Claudeモデルのパターン
        patterns = [
            r'claude-3-5-sonnet',
            r'claude-3-5-haiku',
            r'claude-3-opus',
            r'claude-3-sonnet',
            r'claude-3-haiku',
            r'Claude\s*3\.5\s*Sonnet',
            r'Claude\s*3\.5\s*Haiku',
            r'Claude\s*3\s*Opus',
            r'Claude\s*3\s*Sonnet',
            r'Claude\s*3\s*Haiku'
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # モデルIDを生成
                model_id = self._extract_model_id(text)
                if not model_id:
                    continue
                
                # 表示名を抽出
                display_name = self._extract_display_name(text)
                
                # 説明を抽出
                description = self._extract_description(text)
                
                # デフォルトかどうかを判定
                is_default = any(keyword in text.lower() for keyword in ["default", "selected", "current", "推奨"])
                
                return ModelInfo(
                    id=model_id,
                    name=model_id,
                    display_name=display_name,
                    description=description,
                    context_length=200000,  # Claude 3以降は全て200kコンテキスト
                    capabilities=self._extract_capabilities(model_id),
                    is_default=is_default
                )
        
        return None
    
    def _extract_model_id(self, text: str) -> Optional[str]:
        """テキストからモデルIDを抽出"""
        # 日付パターンを含むモデルID
        id_pattern = r'(claude-3(?:-5)?-(?:opus|sonnet|haiku)(?:-\d{8})?)'
        match = re.search(id_pattern, text.lower())
        if match:
            return match.group(1)
        
        # 表示名からIDを推測
        if "3.5 sonnet" in text.lower():
            return "claude-3-5-sonnet-20241022"
        elif "3.5 haiku" in text.lower():
            return "claude-3-5-haiku-20241022"
        elif "3 opus" in text.lower():
            return "claude-3-opus-20240229"
        elif "3 sonnet" in text.lower():
            return "claude-3-sonnet-20240229"
        elif "3 haiku" in text.lower():
            return "claude-3-haiku-20240307"
        
        return None
    
    def _extract_display_name(self, text: str) -> str:
        """テキストから表示名を抽出"""
        # Claude X.X Name パターン
        name_pattern = r'(Claude\s*\d+(?:\.\d+)?\s*(?:Opus|Sonnet|Haiku))'
        match = re.search(name_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return text.split('\n')[0].strip()
    
    def _extract_description(self, text: str) -> str:
        """テキストから説明を抽出"""
        # 括弧内のテキスト
        desc_pattern = r'\((.*?)\)'
        match = re.search(desc_pattern, text)
        if match:
            return match.group(1)
        
        # 改行後のテキスト
        lines = text.split('\n')
        if len(lines) > 1:
            return lines[1].strip()
        
        # キーワードベースの説明
        if "opus" in text.lower():
            return "最高性能モデル、複雑なタスクに対応"
        elif "sonnet" in text.lower():
            if "3.5" in text:
                return "最新の高性能モデル、優れた推論能力"
            else:
                return "バランスの取れた性能"
        elif "haiku" in text.lower():
            return "高速・低コストモデル"
        
        return ""
    
    def _extract_capabilities(self, model_id: str) -> List[str]:
        """モデルIDから能力を推定"""
        capabilities = ["chat"]
        
        # Opus と Sonnet は画像認識対応
        if "opus" in model_id or "sonnet" in model_id:
            capabilities.append("vision")
        
        # 3.5モデルは強化された能力
        if "3-5" in model_id:
            capabilities.append("enhanced_reasoning")
            capabilities.append("code_generation")
        
        return capabilities