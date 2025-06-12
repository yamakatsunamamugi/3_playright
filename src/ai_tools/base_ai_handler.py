"""
AI操作の基底クラス

このモジュールは以下の機能を提供します：
1. 全AIツール共通のインターフェース定義
2. ブラウザ操作の基本機能
3. エラーハンドリングとリトライ機能
4. ログ出力の統一化

初心者向け解説：
- 各AIツール（ChatGPT、Claude等）の共通基盤
- ブラウザの起動、ページ操作、テキスト入力などの基本機能を提供
- 継承して各AIツール固有の機能を実装
- エラー時の自動リトライ機能も含む
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.utils.logger import get_logger
from src.utils.retry_handler import retry_on_api_error, ErrorCollector

logger = get_logger(__name__)


class AIToolStatus(Enum):
    """AI ツールの状態定義"""
    DISCONNECTED = "disconnected"  # 未接続
    CONNECTING = "connecting"      # 接続中
    CONNECTED = "connected"        # 接続済み
    PROCESSING = "processing"      # 処理中
    ERROR = "error"               # エラー状態
    LOGGED_OUT = "logged_out"     # ログアウト状態


@dataclass
class AIProcessingResult:
    """AI処理結果のデータクラス"""
    success: bool
    result_text: str = ""
    error_message: str = ""
    processing_time: float = 0.0
    retry_count: int = 0
    
    @property
    def has_error(self) -> bool:
        """エラーがあるかチェック"""
        return not self.success or bool(self.error_message)


@dataclass
class AIConfig:
    """AI設定のデータクラス"""
    ai_name: str
    model_name: str
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


class BaseAIHandler(ABC):
    """
    AI操作の基底クラス
    
    全てのAIツール（ChatGPT、Claude、Gemini等）が継承する共通基盤
    
    使用例:
        class ChatGPTHandler(BaseAIHandler):
            async def process_text(self, text: str) -> AIProcessingResult:
                # ChatGPT固有の処理を実装
                pass
        
        handler = ChatGPTHandler()
        await handler.initialize()
        result = await handler.process_text("Hello, AI!")
        await handler.cleanup()
    """
    
    def __init__(self, ai_config: AIConfig):
        """
        基底ハンドラーを初期化
        
        Args:
            ai_config: AI設定
        """
        self.config = ai_config
        self.status = AIToolStatus.DISCONNECTED
        self.error_collector = ErrorCollector()
        
        # Playwright関連
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # 統計情報
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        logger.info(f"🤖 {self.config.ai_name} ハンドラーを初期化しました")
    
    async def initialize(self) -> bool:
        """
        AIハンドラーを初期化
        
        Returns:
            成功時はTrue、失敗時はFalse
        """
        try:
            logger.info(f"🚀 {self.config.ai_name} の初期化を開始")
            self.status = AIToolStatus.CONNECTING
            
            # Playwrightの起動
            await self._initialize_browser()
            
            # AI固有の初期化処理
            await self._initialize_ai_specific()
            
            self.status = AIToolStatus.CONNECTED
            logger.info(f"✅ {self.config.ai_name} の初期化完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ {self.config.ai_name} の初期化失敗: {e}")
            self.error_collector.add_error("初期化", e)
            self.status = AIToolStatus.ERROR
            return False
    
    async def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            logger.info(f"🧹 {self.config.ai_name} のクリーンアップを開始")
            
            # AI固有のクリーンアップ
            await self._cleanup_ai_specific()
            
            # ブラウザのクリーンアップ
            await self._cleanup_browser()
            
            self.status = AIToolStatus.DISCONNECTED
            logger.info(f"✅ {self.config.ai_name} のクリーンアップ完了")
            
        except Exception as e:
            logger.error(f"❌ {self.config.ai_name} のクリーンアップエラー: {e}")
    
    @retry_on_api_error(max_retries=5, base_delay=2.0)
    async def process_text(self, text: str) -> AIProcessingResult:
        """
        テキストをAIで処理（基底実装）
        
        Args:
            text: 処理対象テキスト
            
        Returns:
            処理結果
        """
        start_time = time.time()
        self.total_requests += 1
        
        try:
            logger.debug(f"🤖 {self.config.ai_name} でテキスト処理開始: {text[:50]}...")
            self.status = AIToolStatus.PROCESSING
            
            # AI固有の処理を実行
            result = await self._process_text_ai_specific(text)
            
            self.status = AIToolStatus.CONNECTED
            self.successful_requests += 1
            
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            logger.debug(f"✅ {self.config.ai_name} 処理完了: {processing_time:.2f}秒")
            return result
            
        except Exception as e:
            self.failed_requests += 1
            self.error_collector.add_error("テキスト処理", e)
            self.status = AIToolStatus.ERROR
            
            processing_time = time.time() - start_time
            logger.error(f"❌ {self.config.ai_name} 処理失敗: {e}")
            
            return AIProcessingResult(
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )
    
    async def check_connection(self) -> bool:
        """
        接続状態をチェック
        
        Returns:
            接続中の場合はTrue
        """
        try:
            return await self._check_connection_ai_specific()
        except Exception as e:
            logger.error(f"❌ {self.config.ai_name} 接続チェック失敗: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        success_rate = 0.0
        if self.total_requests > 0:
            success_rate = (self.successful_requests / self.total_requests) * 100
        
        return {
            'ai_name': self.config.ai_name,
            'model_name': self.config.model_name,
            'status': self.status.value,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': success_rate,
            'error_count': self.error_collector.get_error_count()
        }
    
    async def _initialize_browser(self):
        """ブラウザの初期化"""
        logger.debug(f"🌐 ブラウザを起動中: {self.config.ai_name}")
        
        self.playwright = await async_playwright().start()
        
        # ブラウザ起動設定
        browser_options = {
            'headless': False,  # GUIモードで起動（ログイン用）
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        }
        
        self.browser = await self.playwright.chromium.launch(**browser_options)
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        self.page = await self.context.new_page()
        
        # ページの基本設定
        await self.page.set_viewport_size({"width": 1280, "height": 720})
        
        logger.debug(f"✅ ブラウザ起動完了: {self.config.ai_name}")
    
    async def _cleanup_browser(self):
        """ブラウザのクリーンアップ"""
        if self.page:
            await self.page.close()
            self.page = None
        
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def _wait_for_element(self, selector: str, timeout: float = 30000) -> bool:
        """
        要素の出現を待機
        
        Args:
            selector: CSS セレクター
            timeout: タイムアウト時間（ミリ秒）
            
        Returns:
            要素が見つかった場合はTrue
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"⏰ 要素待機タイムアウト: {selector}")
            return False
    
    async def _safe_click(self, selector: str, timeout: float = 10000) -> bool:
        """
        安全なクリック操作
        
        Args:
            selector: CSS セレクター
            timeout: タイムアウト時間（ミリ秒）
            
        Returns:
            成功時はTrue
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.click(selector)
            return True
        except Exception as e:
            logger.debug(f"❌ クリック失敗: {selector} - {e}")
            return False
    
    async def _safe_type(self, selector: str, text: str, timeout: float = 10000) -> bool:
        """
        安全なテキスト入力
        
        Args:
            selector: CSS セレクター
            text: 入力テキスト
            timeout: タイムアウト時間（ミリ秒）
            
        Returns:
            成功時はTrue
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.fill(selector, text)
            return True
        except Exception as e:
            logger.debug(f"❌ テキスト入力失敗: {selector} - {e}")
            return False
    
    async def _get_text_content(self, selector: str, timeout: float = 10000) -> Optional[str]:
        """
        要素のテキスト内容を取得
        
        Args:
            selector: CSS セレクター
            timeout: タイムアウト時間（ミリ秒）
            
        Returns:
            テキスト内容、取得できない場合はNone
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return await self.page.text_content(selector)
        except Exception as e:
            logger.debug(f"❌ テキスト取得失敗: {selector} - {e}")
            return None
    
    # 継承クラスで実装する抽象メソッド
    
    @abstractmethod
    async def _initialize_ai_specific(self):
        """AI固有の初期化処理"""
        pass
    
    @abstractmethod
    async def _cleanup_ai_specific(self):
        """AI固有のクリーンアップ処理"""
        pass
    
    @abstractmethod
    async def _process_text_ai_specific(self, text: str) -> AIProcessingResult:
        """AI固有のテキスト処理"""
        pass
    
    @abstractmethod
    async def _check_connection_ai_specific(self) -> bool:
        """AI固有の接続チェック"""
        pass
    
    @abstractmethod
    def get_login_url(self) -> str:
        """ログインURLを取得"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """利用可能なモデル一覧を取得"""
        pass


class AIHandlerFactory:
    """
    AIハンドラーのファクトリークラス
    
    使用例:
        factory = AIHandlerFactory()
        factory.register('chatgpt', ChatGPTHandler)
        
        handler = factory.create('chatgpt', config)
    """
    
    _handlers = {}
    
    @classmethod
    def register(cls, ai_name: str, handler_class):
        """AIハンドラークラスを登録"""
        cls._handlers[ai_name] = handler_class
        logger.info(f"🏭 AIハンドラーを登録: {ai_name}")
    
    @classmethod
    def create(cls, ai_name: str, config: AIConfig) -> Optional[BaseAIHandler]:
        """AIハンドラーを作成"""
        handler_class = cls._handlers.get(ai_name)
        if not handler_class:
            logger.error(f"❌ 未登録のAI: {ai_name}")
            return None
        
        try:
            return handler_class(config)
        except Exception as e:
            logger.error(f"❌ AIハンドラー作成失敗: {ai_name} - {e}")
            return None
    
    @classmethod
    def get_registered_ais(cls) -> List[str]:
        """登録済みAI名一覧を取得"""
        return list(cls._handlers.keys())