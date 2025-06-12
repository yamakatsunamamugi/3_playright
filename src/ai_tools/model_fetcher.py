"""
AIモデル情報取得の基底クラス
各AIツールの最新モデル情報を取得するための共通インターフェース
"""
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
import requests
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ModelProvider(Enum):
    """AIプロバイダーの列挙型"""
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    GEMINI = "gemini"
    GENSPARK = "genspark"
    GOOGLE_AI_STUDIO = "google_ai_studio"


class SettingOption:
    """設定オプションのクラス"""
    def __init__(self, id: str, display_name: str, type: str, 
                 default_value: Any = None, description: str = "",
                 min_value: Optional[float] = None, max_value: Optional[float] = None,
                 options: Optional[List[str]] = None):
        self.id = id
        self.display_name = display_name
        self.type = type  # "boolean", "number", "select", "text"
        self.default_value = default_value
        self.description = description
        self.min_value = min_value
        self.max_value = max_value
        self.options = options


class ModelInfo:
    """モデル情報を保持するクラス"""
    def __init__(self, id: str, name: str, description: str = "", 
                 capabilities: List[str] = None, max_tokens: int = None,
                 is_default: bool = False):
        self.id = id
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.max_tokens = max_tokens
        self.is_default = is_default
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "max_tokens": self.max_tokens,
            "is_default": self.is_default
        }


class ModelFetcher(ABC):
    """モデル情報取得の基底クラス"""
    
    CACHE_DIR = Path("cache/models")
    CACHE_DURATION = timedelta(hours=24)
    
    def __init__(self, ai_name: str):
        self.ai_name = ai_name
        self.cache_file = self.CACHE_DIR / f"{ai_name.lower()}_models.json"
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
    @abstractmethod
    def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        ソースから最新のモデル情報を取得
        各AIツール固有の実装が必要
        """
        pass
        
    @abstractmethod
    def get_default_settings(self) -> Dict[str, Any]:
        """
        各AIツールのデフォルト設定を取得
        DeepThinkなどの設定オプション
        """
        pass
        
    def get_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """
        モデル情報を取得（キャッシュ対応）
        
        Args:
            force_refresh: Trueの場合、キャッシュを無視して最新情報を取得
            
        Returns:
            モデル情報のリスト
        """
        if not force_refresh and self._is_cache_valid():
            logger.info(f"{self.ai_name}: キャッシュからモデル情報を読み込み")
            return self._load_from_cache()
            
        try:
            logger.info(f"{self.ai_name}: 最新のモデル情報を取得中...")
            models = self.fetch_models_from_source()
            self._save_to_cache(models)
            return models
        except Exception as e:
            logger.error(f"{self.ai_name}: モデル情報の取得に失敗: {e}")
            # キャッシュが存在すれば古くても使用
            if self.cache_file.exists():
                logger.warning(f"{self.ai_name}: 古いキャッシュを使用します")
                return self._load_from_cache()
            # フォールバック
            return self._get_fallback_models()
            
    def _is_cache_valid(self) -> bool:
        """キャッシュの有効性をチェック"""
        if not self.cache_file.exists():
            return False
            
        modified_time = datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        return datetime.now() - modified_time < self.CACHE_DURATION
        
    def _load_from_cache(self) -> List[ModelInfo]:
        """キャッシュからモデル情報を読み込み"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [ModelInfo(**model) for model in data['models']]
        except Exception as e:
            logger.error(f"キャッシュの読み込みに失敗: {e}")
            return []
            
    def _save_to_cache(self, models: List[ModelInfo]):
        """モデル情報をキャッシュに保存"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'models': [model.to_dict() for model in models]
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"キャッシュの保存に失敗: {e}")
            
    def _get_fallback_models(self) -> List[ModelInfo]:
        """フォールバック用のデフォルトモデル情報"""
        logger.warning(f"{self.ai_name}: フォールバックモデルを使用")
        return []
        
    def make_api_request(self, url: str, headers: Dict[str, str] = None, 
                        timeout: int = 10) -> Optional[Dict]:
        """
        API リクエストを実行するヘルパーメソッド
        
        Args:
            url: リクエストURL
            headers: リクエストヘッダー
            timeout: タイムアウト秒数
            
        Returns:
            レスポンスのJSONデータ
        """
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"APIリクエストエラー: {e}")
            return None
    
    async def fetch_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """非同期でモデル情報を取得（互換性のため）"""
        return self.get_models(force_refresh)
    
    async def fetch_settings(self, force_refresh: bool = False) -> List[SettingOption]:
        """非同期で設定オプションを取得（互換性のため）"""
        settings = self.get_default_settings()
        setting_options = []
        
        for key, value in settings.items():
            option = SettingOption(
                id=key,
                display_name=key.replace('_', ' ').title(),
                type=value.get('type', 'text'),
                default_value=value.get('default'),
                description=value.get('description', ''),
                min_value=value.get('min'),
                max_value=value.get('max'),
                options=value.get('options')
            )
            setting_options.append(option)
        
        return setting_options


def create_model_fetcher(provider: ModelProvider, cache_dir: Optional[Path] = None) -> ModelFetcher:
    """
    指定されたプロバイダー用のモデルフェッチャーを作成
    
    Args:
        provider: AIプロバイダー
        cache_dir: キャッシュディレクトリ（省略時はデフォルト）
        
    Returns:
        ModelFetcherインスタンス
    """
    # 各モデルフェッチャーをインポート
    if provider == ModelProvider.CHATGPT:
        from .chatgpt_model_fetcher import ChatGPTModelFetcher
        return ChatGPTModelFetcher()
    
    elif provider == ModelProvider.CLAUDE:
        from .claude_model_fetcher import ClaudeModelFetcher
        return ClaudeModelFetcher()
    
    elif provider == ModelProvider.GEMINI:
        from .gemini_model_fetcher import GeminiModelFetcher
        return GeminiModelFetcher()
    
    elif provider == ModelProvider.GENSPARK:
        from .genspark_model_fetcher import GensparkModelFetcher
        return GensparkModelFetcher()
    
    elif provider == ModelProvider.GOOGLE_AI_STUDIO:
        from .google_ai_studio_model_fetcher import GoogleAIStudioModelFetcher
        return GoogleAIStudioModelFetcher()
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")