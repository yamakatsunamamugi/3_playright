"""
Google AI Studioモデル情報取得モジュール

Google AI StudioのWebUIから最新モデル情報を取得する。
"""

import asyncio
from typing import List, Optional
from playwright.async_api import async_playwright

from .model_fetcher import (
    ModelFetcherBase, ModelInfo, SettingOption, 
    ModelProvider, CacheManager
)


class GoogleAIStudioModelFetcher(ModelFetcherBase):
    """Google AI Studio用のモデル情報取得クラス"""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """初期化"""
        super().__init__(ModelProvider.GOOGLE_AI_STUDIO, cache_manager)
        self.studio_url = "https://aistudio.google.com"
    
    async def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        Google AI Studioから最新のモデル情報を取得
        
        Returns:
            モデル情報リスト
        """
        # Google AI StudioはGeminiモデルを使用するため、
        # Geminiと同様のモデルリストを返す
        return [
            ModelInfo(
                id="gemini-2.0-flash-exp",
                name="gemini-2.0-flash-exp",
                display_name="Gemini 2.0 Flash (Experimental)",
                description="最新の実験的モデル、高速で高性能",
                context_length=1048576,
                capabilities=["chat", "vision", "function_calling", "code_execution"],
                is_default=True
            ),
            ModelInfo(
                id="gemini-1.5-pro",
                name="gemini-1.5-pro",
                display_name="Gemini 1.5 Pro",
                description="高性能な長文コンテキスト対応モデル",
                context_length=2097152,
                capabilities=["chat", "vision", "function_calling", "code_execution"]
            ),
            ModelInfo(
                id="gemini-1.5-flash",
                name="gemini-1.5-flash",
                display_name="Gemini 1.5 Flash",
                description="高速で効率的なモデル",
                context_length=1048576,
                capabilities=["chat", "vision", "function_calling"]
            ),
            ModelInfo(
                id="gemini-pro",
                name="gemini-pro",
                display_name="Gemini Pro",
                description="バランスの取れた汎用モデル",
                context_length=32768,
                capabilities=["chat", "vision"]
            )
        ]
    
    async def fetch_settings_from_source(self) -> List[SettingOption]:
        """
        Google AI Studioから最新の設定オプションを取得
        
        Returns:
            設定オプションリスト
        """
        return [
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
            ),
            SettingOption(
                id="stop_sequences",
                name="stop_sequences",
                display_name="停止シーケンス",
                type="text",
                default_value="",
                description="出力を停止するシーケンス（カンマ区切り）"
            ),
            SettingOption(
                id="safety_settings",
                name="safety_settings",
                display_name="安全設定",
                type="select",
                options=["ブロックなし", "少数をブロック", "一部をブロック", "ほとんどをブロック"],
                default_value="一部をブロック",
                description="有害なコンテンツのフィルタリングレベル"
            )
        ]