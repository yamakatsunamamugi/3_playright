"""
AIモデル情報取得モジュール

各AIサービスから最新のモデル情報と設定オプションを動的に取得する。
キャッシュ機構により頻繁なアクセスを防ぎ、エラー時にはフォールバックデータを提供する。
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
from enum import Enum

from playwright.async_api import Page, Browser
import aiohttp

# ロガー設定
logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """AIモデルプロバイダー"""
    CHATGPT = "ChatGPT"
    CLAUDE = "Claude"
    GEMINI = "Gemini"
    GENSPARK = "Genspark"
    GOOGLE_AI_STUDIO = "Google AI Studio"


@dataclass
class ModelInfo:
    """モデル情報を格納するデータクラス"""
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    context_length: Optional[int] = None
    max_tokens: Optional[int] = None
    capabilities: List[str] = field(default_factory=list)
    is_default: bool = False
    release_date: Optional[str] = None


@dataclass
class SettingOption:
    """設定オプション情報"""
    id: str
    name: str
    display_name: str
    type: str  # "boolean", "number", "select", "text"
    default_value: Any = None
    options: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: Optional[str] = None


@dataclass
class CacheEntry:
    """キャッシュエントリー"""
    data: Any
    timestamp: float
    ttl: int  # Time to live in seconds


class CacheManager:
    """キャッシュ管理クラス"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        キャッシュマネージャーを初期化
        
        Args:
            cache_dir: キャッシュディレクトリ（Noneの場合はメモリキャッシュのみ）
        """
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"キャッシュマネージャー初期化: cache_dir={cache_dir}")
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュからデータを取得"""
        # メモリキャッシュをチェック
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if time.time() - entry.timestamp < entry.ttl:
                logger.debug(f"メモリキャッシュヒット: {key}")
                return entry.data
            else:
                logger.debug(f"メモリキャッシュ期限切れ: {key}")
                del self.memory_cache[key]
        
        # ディスクキャッシュをチェック
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    entry = CacheEntry(**cache_data)
                    if time.time() - entry.timestamp < entry.ttl:
                        logger.debug(f"ディスクキャッシュヒット: {key}")
                        # メモリキャッシュにも保存
                        self.memory_cache[key] = entry
                        return entry.data
                    else:
                        logger.debug(f"ディスクキャッシュ期限切れ: {key}")
                        cache_file.unlink()
                except Exception as e:
                    logger.error(f"ディスクキャッシュ読み込みエラー: {e}")
        
        return None
    
    def set(self, key: str, data: Any, ttl: int = 900):  # デフォルト15分
        """キャッシュにデータを保存"""
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl
        )
        
        # メモリキャッシュに保存
        self.memory_cache[key] = entry
        logger.debug(f"メモリキャッシュ保存: {key}, TTL={ttl}秒")
        
        # ディスクキャッシュに保存
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.json"
            try:
                cache_data = {
                    "data": data,
                    "timestamp": entry.timestamp,
                    "ttl": entry.ttl
                }
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                logger.debug(f"ディスクキャッシュ保存: {key}")
            except Exception as e:
                logger.error(f"ディスクキャッシュ保存エラー: {e}")
    
    def clear(self, key: Optional[str] = None):
        """キャッシュをクリア"""
        if key:
            # 特定のキーをクリア
            if key in self.memory_cache:
                del self.memory_cache[key]
            if self.cache_dir:
                cache_file = self.cache_dir / f"{key}.json"
                if cache_file.exists():
                    cache_file.unlink()
            logger.info(f"キャッシュクリア: {key}")
        else:
            # 全キャッシュをクリア
            self.memory_cache.clear()
            if self.cache_dir:
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
            logger.info("全キャッシュをクリア")


class ModelFetcherBase(ABC):
    """モデル情報取得の基底クラス"""
    
    def __init__(self, provider: ModelProvider, cache_manager: Optional[CacheManager] = None):
        """
        初期化
        
        Args:
            provider: AIプロバイダー
            cache_manager: キャッシュマネージャー
        """
        self.provider = provider
        self.cache_manager = cache_manager or CacheManager()
        self.logger = logging.getLogger(f"{__name__}.{provider.value}")
        
        # フォールバックデータ
        self.fallback_models = self._get_fallback_models()
        self.fallback_settings = self._get_fallback_settings()
    
    @abstractmethod
    async def fetch_models_from_source(self) -> List[ModelInfo]:
        """ソースから最新のモデル情報を取得（実装必須）"""
        pass
    
    @abstractmethod
    async def fetch_settings_from_source(self) -> List[SettingOption]:
        """ソースから最新の設定オプションを取得（実装必須）"""
        pass
    
    async def fetch_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """
        モデル情報を取得（キャッシュ対応）
        
        Args:
            force_refresh: 強制的に最新情報を取得
            
        Returns:
            モデル情報リスト
        """
        cache_key = f"{self.provider.value}_models"
        
        # キャッシュチェック
        if not force_refresh:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return [ModelInfo(**model) for model in cached_data]
        
        # ソースから取得
        try:
            self.logger.info(f"{self.provider.value}から最新モデル情報を取得中...")
            models = await self._fetch_with_retry(self.fetch_models_from_source)
            
            # キャッシュに保存
            cache_data = [model.__dict__ for model in models]
            self.cache_manager.set(cache_key, cache_data, ttl=3600)  # 1時間
            
            self.logger.info(f"{len(models)}個のモデル情報を取得しました")
            return models
            
        except Exception as e:
            self.logger.error(f"モデル情報取得エラー: {e}")
            self.logger.warning("フォールバックデータを使用します")
            return self.fallback_models
    
    async def fetch_settings(self, force_refresh: bool = False) -> List[SettingOption]:
        """
        設定オプションを取得（キャッシュ対応）
        
        Args:
            force_refresh: 強制的に最新情報を取得
            
        Returns:
            設定オプションリスト
        """
        cache_key = f"{self.provider.value}_settings"
        
        # キャッシュチェック
        if not force_refresh:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return [SettingOption(**setting) for setting in cached_data]
        
        # ソースから取得
        try:
            self.logger.info(f"{self.provider.value}から最新設定オプションを取得中...")
            settings = await self._fetch_with_retry(self.fetch_settings_from_source)
            
            # キャッシュに保存
            cache_data = [setting.__dict__ for setting in settings]
            self.cache_manager.set(cache_key, cache_data, ttl=3600)  # 1時間
            
            self.logger.info(f"{len(settings)}個の設定オプションを取得しました")
            return settings
            
        except Exception as e:
            self.logger.error(f"設定オプション取得エラー: {e}")
            self.logger.warning("フォールバックデータを使用します")
            return self.fallback_settings
    
    async def _fetch_with_retry(self, fetch_func, max_retries: int = 3):
        """リトライ機構付きでデータ取得"""
        for attempt in range(max_retries):
            try:
                return await fetch_func()
            except Exception as e:
                self.logger.warning(f"取得試行 {attempt + 1}/{max_retries} 失敗: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数バックオフ
                else:
                    raise
    
    def _get_fallback_models(self) -> List[ModelInfo]:
        """フォールバック用のモデルデータ"""
        # 各プロバイダー用のデフォルトモデルリストをここに定義
        fallback_data = {
            ModelProvider.CHATGPT: [
                ModelInfo(
                    id="gpt-4o",
                    name="gpt-4o",
                    display_name="GPT-4o",
                    description="最新の高性能モデル",
                    context_length=128000,
                    capabilities=["chat", "vision", "function_calling"],
                    is_default=True
                ),
                ModelInfo(
                    id="gpt-4o-mini",
                    name="gpt-4o-mini",
                    display_name="GPT-4o Mini",
                    description="高速・低コストモデル",
                    context_length=128000,
                    capabilities=["chat", "vision", "function_calling"]
                ),
            ],
            ModelProvider.CLAUDE: [
                ModelInfo(
                    id="claude-3-5-sonnet-20241022",
                    name="claude-3-5-sonnet-20241022",
                    display_name="Claude 3.5 Sonnet",
                    description="最新の高性能モデル",
                    context_length=200000,
                    capabilities=["chat", "vision"],
                    is_default=True
                ),
                ModelInfo(
                    id="claude-3-5-haiku-20241022",
                    name="claude-3-5-haiku-20241022",
                    display_name="Claude 3.5 Haiku",
                    description="高速・低コストモデル",
                    context_length=200000,
                    capabilities=["chat"]
                ),
            ],
            ModelProvider.GEMINI: [
                ModelInfo(
                    id="gemini-2.0-flash-exp",
                    name="gemini-2.0-flash-exp",
                    display_name="Gemini 2.0 Flash (Experimental)",
                    description="最新の実験的モデル",
                    context_length=1048576,
                    capabilities=["chat", "vision"],
                    is_default=True
                ),
                ModelInfo(
                    id="gemini-1.5-pro",
                    name="gemini-1.5-pro",
                    display_name="Gemini 1.5 Pro",
                    description="高性能モデル",
                    context_length=2097152,
                    capabilities=["chat", "vision"]
                ),
            ],
            ModelProvider.GENSPARK: [
                ModelInfo(
                    id="genspark-latest",
                    name="genspark-latest",
                    display_name="Genspark Latest",
                    description="最新モデル",
                    is_default=True
                ),
            ],
            ModelProvider.GOOGLE_AI_STUDIO: [
                ModelInfo(
                    id="gemini-2.0-flash-exp",
                    name="gemini-2.0-flash-exp",
                    display_name="Gemini 2.0 Flash (Experimental)",
                    description="最新の実験的モデル",
                    is_default=True
                ),
            ]
        }
        
        return fallback_data.get(self.provider, [])
    
    def _get_fallback_settings(self) -> List[SettingOption]:
        """フォールバック用の設定データ"""
        # 共通設定オプション
        common_settings = [
            SettingOption(
                id="temperature",
                name="temperature",
                display_name="Temperature",
                type="number",
                default_value=0.7,
                min_value=0.0,
                max_value=2.0,
                description="出力のランダム性を制御"
            ),
            SettingOption(
                id="max_tokens",
                name="max_tokens",
                display_name="最大トークン数",
                type="number",
                default_value=2000,
                min_value=1,
                max_value=4096,
                description="生成する最大トークン数"
            ),
        ]
        
        # プロバイダー固有の設定
        provider_settings = {
            ModelProvider.CHATGPT: common_settings + [
                SettingOption(
                    id="presence_penalty",
                    name="presence_penalty",
                    display_name="Presence Penalty",
                    type="number",
                    default_value=0.0,
                    min_value=-2.0,
                    max_value=2.0,
                    description="新しいトピックへの移行を促進"
                ),
            ],
            ModelProvider.CLAUDE: [
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
            ],
            ModelProvider.GEMINI: common_settings + [
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
            ],
        }
        
        return provider_settings.get(self.provider, [])


# ファクトリー関数
def create_model_fetcher(provider: ModelProvider, cache_dir: Optional[Path] = None) -> ModelFetcherBase:
    """
    指定されたプロバイダー用のモデルフェッチャーを作成
    
    Args:
        provider: AIプロバイダー
        cache_dir: キャッシュディレクトリ
        
    Returns:
        モデルフェッチャーインスタンス
    """
    from .chatgpt_model_fetcher import ChatGPTModelFetcher
    from .claude_model_fetcher import ClaudeModelFetcher
    from .gemini_model_fetcher import GeminiModelFetcher
    from .genspark_model_fetcher import GensparkModelFetcher
    from .google_ai_studio_model_fetcher import GoogleAIStudioModelFetcher
    
    cache_manager = CacheManager(cache_dir)
    
    fetcher_classes = {
        ModelProvider.CHATGPT: ChatGPTModelFetcher,
        ModelProvider.CLAUDE: ClaudeModelFetcher,
        ModelProvider.GEMINI: GeminiModelFetcher,
        ModelProvider.GENSPARK: GensparkModelFetcher,
        ModelProvider.GOOGLE_AI_STUDIO: GoogleAIStudioModelFetcher,
    }
    
    fetcher_class = fetcher_classes.get(provider)
    if not fetcher_class:
        raise ValueError(f"サポートされていないプロバイダー: {provider}")
    
    return fetcher_class(cache_manager)