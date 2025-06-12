"""拡張AIハンドラー - 改善されたブラウザ自動化とエラーハンドリング"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from ..browser.enhanced_browser_manager import EnhancedBrowserManager
from ..browser.enhanced_selector_strategy import EnhancedSelectorStrategy
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class EnhancedAIHandler(ABC):
    """改善されたAI自動化ハンドラーの基底クラス
    
    主な改善点:
    - 安定したセレクター戦略
    - インテリジェントなエラーハンドリング
    - セッション管理の統合
    - パフォーマンス最適化
    """
    
    def __init__(
        self,
        service_name: str,
        browser_manager: EnhancedBrowserManager
    ):
        self.service_name = service_name
        self.browser_manager = browser_manager
        self.selector_strategy = browser_manager.selector_strategy
        self.page: Optional[Page] = None
        
        # エラー統計
        self.error_stats = {
            'total_errors': 0,
            'error_types': {},
            'last_errors': []
        }
        
        # 処理統計
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'average_response_time': 0
        }
    
    @abstractmethod
    def get_service_url(self) -> str:
        """サービスのURLを取得"""
        pass
    
    async def initialize(self) -> bool:
        """ハンドラーを初期化"""
        try:
            # ページを作成
            self.page = await self.browser_manager.create_service_page(
                self.service_name,
                self.get_service_url()
            )
            
            if not self.page:
                logger.error(f"Failed to create page for {self.service_name}")
                return False
            
            # ログイン状態を確認
            is_logged_in = await self.verify_login_status()
            
            if not is_logged_in:
                logger.warning(f"Not logged in to {self.service_name}")
                # 自動再認証を試みる
                success = await self.browser_manager.session_manager.auto_reauth(
                    self.page,
                    self.service_name,
                    self.manual_login_callback
                )
                
                if not success:
                    logger.error(f"Failed to authenticate with {self.service_name}")
                    return False
            
            logger.info(f"Initialized {self.service_name} handler")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.service_name} handler: {e}")
            self._record_error('initialization', str(e))
            return False
    
    async def verify_login_status(self) -> bool:
        """ログイン状態を確認"""
        try:
            # 入力欄が表示されているかチェック
            input_element = await self.selector_strategy.find_element(
                self.page,
                self.service_name,
                'input',
                timeout=10000
            )
            
            return input_element is not None
            
        except Exception as e:
            logger.error(f"Login status check failed: {e}")
            return False
    
    async def manual_login_callback(self, page: Page, service_name: str) -> bool:
        """手動ログインのコールバック"""
        logger.info(f"Manual login required for {service_name}")
        logger.info("Please log in manually in the browser window...")
        
        # ユーザーがログインするまで待機（最大5分）
        max_wait_time = 300  # 秒
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
            # ログイン状態を定期的にチェック
            if await self.verify_login_status():
                logger.info(f"Login successful for {service_name}")
                return True
            
            await asyncio.sleep(5)
        
        logger.error(f"Manual login timeout for {service_name}")
        return False
    
    async def send_prompt(self, prompt: str) -> Optional[str]:
        """プロンプトを送信して応答を取得
        
        Args:
            prompt: 送信するプロンプト
            
        Returns:
            応答テキスト、エラー時はNone
        """
        start_time = asyncio.get_event_loop().time()
        self.processing_stats['total_requests'] += 1
        
        try:
            # 入力欄を見つける
            input_element = await self.selector_strategy.find_element(
                self.page,
                self.service_name,
                'input'
            )
            
            if not input_element:
                raise Exception("Input element not found")
            
            # テキストを入力
            success = await self.selector_strategy.smart_fill(
                self.page,
                input_element,
                prompt,
                self.service_name
            )
            
            if not success:
                raise Exception("Failed to input text")
            
            # 送信
            await self._send_message()
            
            # 応答完了を待つ
            response_complete = await self.selector_strategy.detect_response_complete(
                self.page,
                self.service_name,
                timeout=120000
            )
            
            if not response_complete:
                raise Exception("Response timeout")
            
            # 応答を取得
            response = await self._get_response()
            
            # 統計を更新
            self.processing_stats['successful_requests'] += 1
            response_time = asyncio.get_event_loop().time() - start_time
            self._update_average_response_time(response_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send prompt: {e}")
            self._record_error('prompt_processing', str(e))
            
            # エラーリカバリーを試みる
            if await self._try_error_recovery():
                # リトライ
                return await self.send_prompt(prompt)
            
            return None
    
    async def _send_message(self):
        """メッセージを送信"""
        # まず送信ボタンを探す
        send_button = await self.selector_strategy.find_element(
            self.page,
            self.service_name,
            'send_button',
            timeout=3000
        )
        
        if send_button:
            await send_button.click()
        else:
            # Enterキーで送信
            await self.page.keyboard.press('Enter')
        
        # 送信後の待機
        strategy = self.selector_strategy.get_interaction_strategies(self.service_name)
        wait_time = strategy.get('wait_after_send', 1000)
        await asyncio.sleep(wait_time / 1000)
    
    async def _get_response(self) -> str:
        """応答を取得"""
        # 応答コンテナを見つける
        response_containers = await self.page.query_selector_all(
            self.selector_strategy.selector_definitions[self.service_name]['response_container'][0]
        )
        
        if not response_containers:
            logger.warning("No response containers found")
            return ""
        
        # 最新の応答を取得
        latest_response = response_containers[-1]
        response_text = await latest_response.text_content()
        
        return response_text.strip() if response_text else ""
    
    async def _try_error_recovery(self) -> bool:
        """エラーからの回復を試みる"""
        logger.info(f"Attempting error recovery for {self.service_name}")
        
        try:
            # ページをリロード
            await self.browser_manager.safe_goto(
                self.page,
                self.get_service_url()
            )
            
            # ログイン状態を再確認
            return await self.verify_login_status()
            
        except Exception as e:
            logger.error(f"Error recovery failed: {e}")
            return False
    
    def _record_error(self, error_type: str, error_message: str):
        """エラーを記録"""
        self.error_stats['total_errors'] += 1
        
        if error_type not in self.error_stats['error_types']:
            self.error_stats['error_types'][error_type] = 0
        self.error_stats['error_types'][error_type] += 1
        
        # 最新のエラーを記録（最大10件）
        self.error_stats['last_errors'].append({
            'type': error_type,
            'message': error_message,
            'timestamp': asyncio.get_event_loop().time()
        })
        
        if len(self.error_stats['last_errors']) > 10:
            self.error_stats['last_errors'].pop(0)
    
    def _update_average_response_time(self, response_time: float):
        """平均応答時間を更新"""
        n = self.processing_stats['successful_requests']
        current_avg = self.processing_stats['average_response_time']
        
        # 移動平均を計算
        new_avg = ((n - 1) * current_avg + response_time) / n
        self.processing_stats['average_response_time'] = new_avg
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            'service': self.service_name,
            'error_stats': self.error_stats,
            'processing_stats': self.processing_stats,
            'success_rate': (
                self.processing_stats['successful_requests'] / 
                self.processing_stats['total_requests'] * 100
                if self.processing_stats['total_requests'] > 0 else 0
            )
        }


class ChatGPTEnhancedHandler(EnhancedAIHandler):
    """ChatGPT用の拡張ハンドラー"""
    
    def get_service_url(self) -> str:
        return "https://chat.openai.com"


class ClaudeEnhancedHandler(EnhancedAIHandler):
    """Claude用の拡張ハンドラー"""
    
    def get_service_url(self) -> str:
        return "https://claude.ai"


class GeminiEnhancedHandler(EnhancedAIHandler):
    """Gemini用の拡張ハンドラー"""
    
    def get_service_url(self) -> str:
        return "https://gemini.google.com"


class AIHandlerFactory:
    """AIハンドラーのファクトリー"""
    
    @staticmethod
    def create_handler(
        service_name: str,
        browser_manager: EnhancedBrowserManager
    ) -> Optional[EnhancedAIHandler]:
        """指定されたサービス用のハンドラーを作成"""
        
        handlers = {
            'chatgpt': ChatGPTEnhancedHandler,
            'claude': ClaudeEnhancedHandler,
            'gemini': GeminiEnhancedHandler
        }
        
        handler_class = handlers.get(service_name.lower())
        
        if handler_class:
            return handler_class(service_name, browser_manager)
        
        logger.error(f"Unknown service: {service_name}")
        return None