"""
Gensparkモデル情報取得モジュール

GensparkのWebUIから最新モデル情報を取得する。
"""

import asyncio
from typing import List, Optional
from playwright.async_api import async_playwright

from .model_fetcher import (
    ModelFetcherBase, ModelInfo, SettingOption, 
    ModelProvider, CacheManager
)


class GensparkModelFetcher(ModelFetcherBase):
    """Genspark用のモデル情報取得クラス"""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """初期化"""
        super().__init__(ModelProvider.GENSPARK, cache_manager)
        self.genspark_url = "https://www.genspark.ai"
    
    async def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        Gensparkから最新のモデル情報を取得
        
        Returns:
            モデル情報リスト
        """
        # Gensparkは現在単一モデルのため、固定リストを返す
        # 将来的にWebUIから動的取得に対応
        return [
            ModelInfo(
                id="genspark-latest",
                name="genspark-latest",
                display_name="Genspark Latest",
                description="最新のGensparkモデル",
                capabilities=["chat", "search", "summarization"],
                is_default=True
            ),
            ModelInfo(
                id="genspark-pro",
                name="genspark-pro",
                display_name="Genspark Pro",
                description="高度な検索と要約機能",
                capabilities=["chat", "search", "summarization", "research"]
            ),
            ModelInfo(
                id="genspark-standard",
                name="genspark-standard",
                display_name="Genspark Standard",
                description="標準的な検索エンジン",
                capabilities=["chat", "search"]
            )
        ]
    
    async def fetch_settings_from_source(self) -> List[SettingOption]:
        """
        Gensparkから最新の設定オプションを取得
        
        Returns:
            設定オプションリスト
        """
        return [
            SettingOption(
                id="search_depth",
                name="search_depth",
                display_name="検索の深さ",
                type="select",
                options=["浅い", "標準", "深い"],
                default_value="標準",
                description="情報検索の詳細度"
            ),
            SettingOption(
                id="include_sources",
                name="include_sources",
                display_name="ソース表示",
                type="boolean",
                default_value=True,
                description="検索結果のソースを表示"
            ),
            SettingOption(
                id="summary_length",
                name="summary_length",
                display_name="要約の長さ",
                type="select",
                options=["短い", "中程度", "長い"],
                default_value="中程度",
                description="生成される要約の長さ"
            )
        ]