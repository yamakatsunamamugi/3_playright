"""
リトライ処理とエラーハンドリングのユーティリティ

このモジュールは以下の機能を提供します：
1. 関数のリトライデコレーター（指数バックオフ対応）
2. 特定例外の種類別リトライ戦略
3. エラーログの詳細記録
4. API制限やネットワークエラーへの対応

初心者向け解説：
- @retry_on_error デコレーターを関数に付けるだけで自動リトライ
- ネットワークエラーやAPI制限エラーを自動的に識別
- 段階的に待機時間を延長（指数バックオフ）
- 最大5回までリトライ（CLAUDE.mdの要件通り）
"""

import time
import functools
import logging
from typing import Callable, Type, Tuple, Optional, List, Any, Dict
from googleapiclient.errors import HttpError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RetryHandler:
    """リトライ処理を管理するクラス"""
    
    # リトライ対象のエラータイプ
    RETRYABLE_HTTP_CODES = [429, 500, 502, 503, 504]  # Too Many Requests, Server Errors
    RETRYABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        HttpError,
    )
    
    def __init__(self, max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        リトライハンドラーを初期化
        
        Args:
            max_retries: 最大リトライ回数（デフォルト: 5）
            base_delay: 基本待機時間（秒、デフォルト: 1.0）
            max_delay: 最大待機時間（秒、デフォルト: 60.0）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        logger.debug(f"🔄 RetryHandler初期化: max_retries={max_retries}, base_delay={base_delay}s")
    
    def retry_on_error(self, exceptions: Tuple[Type[Exception], ...] = None, 
                      max_retries: Optional[int] = None,
                      base_delay: Optional[float] = None) -> Callable:
        """
        関数にリトライ機能を追加するデコレーター
        
        Args:
            exceptions: リトライ対象の例外タプル（デフォルト: RETRYABLE_EXCEPTIONS）
            max_retries: このデコレーター用の最大リトライ回数
            base_delay: このデコレーター用の基本待機時間
            
        Returns:
            デコレーターされた関数
            
        使用例:
            @retry_handler.retry_on_error()
            def api_call():
                return some_api_function()
                
            @retry_handler.retry_on_error(exceptions=(ConnectionError,), max_retries=3)
            def network_call():
                return network_function()
        """
        if exceptions is None:
            exceptions = self.RETRYABLE_EXCEPTIONS
        if max_retries is None:
            max_retries = self.max_retries
        if base_delay is None:
            base_delay = self.base_delay
            
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(max_retries + 1):  # +1 for initial attempt
                    try:
                        if attempt > 0:
                            logger.info(f"🔄 リトライ {attempt}/{max_retries}: {func.__name__}")
                        
                        result = func(*args, **kwargs)
                        
                        if attempt > 0:
                            logger.info(f"✅ リトライ成功: {func.__name__} ({attempt}回目で成功)")
                        
                        return result
                        
                    except exceptions as e:
                        last_exception = e
                        
                        if not self._is_retryable_error(e):
                            logger.error(f"❌ リトライ不可エラー: {func.__name__} - {e}")
                            raise
                        
                        if attempt < max_retries:
                            delay = self._calculate_delay(attempt, base_delay)
                            logger.warning(
                                f"⚠️ エラー発生 ({attempt + 1}/{max_retries + 1}): {func.__name__} - "
                                f"{type(e).__name__}: {e} - {delay:.1f}秒後にリトライ"
                            )
                            time.sleep(delay)
                        else:
                            logger.error(
                                f"❌ 最大リトライ回数に達しました: {func.__name__} - "
                                f"最終エラー: {type(e).__name__}: {e}"
                            )
                            break
                    
                    except Exception as e:
                        logger.error(f"❌ 予期しないエラー: {func.__name__} - {type(e).__name__}: {e}")
                        raise
                
                # 最大リトライ回数に達した場合
                raise last_exception
            
            return wrapper
        return decorator
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        エラーがリトライ可能かどうかを判定
        
        Args:
            error: 判定対象の例外
            
        Returns:
            リトライ可能な場合はTrue
        """
        # HttpErrorの場合はステータスコードをチェック
        if isinstance(error, HttpError):
            status_code = error.resp.status
            is_retryable = status_code in self.RETRYABLE_HTTP_CODES
            
            if is_retryable:
                logger.debug(f"🔄 リトライ可能なHTTPエラー: {status_code}")
            else:
                logger.debug(f"❌ リトライ不可HTTPエラー: {status_code}")
                
            return is_retryable
        
        # その他の例外は基本的にリトライ可能
        return True
    
    def _calculate_delay(self, attempt: int, base_delay: float) -> float:
        """
        指数バックオフによる待機時間を計算
        
        Args:
            attempt: 現在の試行回数（0から開始）
            base_delay: 基本待機時間
            
        Returns:
            待機時間（秒）
            
        計算式: min(base_delay * (2 ^ attempt), max_delay)
        """
        delay = base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    @staticmethod
    def with_timeout(timeout_seconds: float) -> Callable:
        """
        関数にタイムアウト機能を追加するデコレーター
        
        Args:
            timeout_seconds: タイムアウト時間（秒）
            
        Returns:
            デコレーターされた関数
            
        使用例:
            @RetryHandler.with_timeout(30.0)
            def slow_function():
                time.sleep(60)  # タイムアウトで中断される
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                import signal
                
                class TimeoutError(Exception):
                    pass
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"関数 {func.__name__} が{timeout_seconds}秒でタイムアウトしました")
                
                # タイムアウト設定（Unixベースシステムのみ）
                try:
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(int(timeout_seconds))
                    
                    try:
                        result = func(*args, **kwargs)
                        return result
                    finally:
                        signal.alarm(0)  # タイマーをクリア
                        signal.signal(signal.SIGALRM, old_handler)
                        
                except (AttributeError, OSError):
                    # Windowsや一部環境では signal.SIGALRM が使用できない
                    logger.warning("⚠️ タイムアウト機能は使用できません（signal.SIGALRM非対応環境）")
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator


# 便利な事前定義済みデコレーター
def retry_on_api_error(max_retries: int = 5, base_delay: float = 1.0) -> Callable:
    """
    API関連エラー用のリトライデコレーター
    
    Args:
        max_retries: 最大リトライ回数
        base_delay: 基本待機時間
        
    Returns:
        デコレーター関数
        
    使用例:
        @retry_on_api_error(max_retries=3)
        def call_google_sheets_api():
            return sheets_client.read_range(...)
    """
    handler = RetryHandler(max_retries=max_retries, base_delay=base_delay)
    return handler.retry_on_error(
        exceptions=(HttpError, ConnectionError, TimeoutError),
        max_retries=max_retries,
        base_delay=base_delay
    )


def retry_on_network_error(max_retries: int = 3, base_delay: float = 2.0) -> Callable:
    """
    ネットワークエラー用のリトライデコレーター
    
    Args:
        max_retries: 最大リトライ回数
        base_delay: 基本待機時間
        
    Returns:
        デコレーター関数
        
    使用例:
        @retry_on_network_error()
        def download_file():
            return requests.get(url)
    """
    handler = RetryHandler(max_retries=max_retries, base_delay=base_delay)
    return handler.retry_on_error(
        exceptions=(ConnectionError, TimeoutError),
        max_retries=max_retries,
        base_delay=base_delay
    )


class ErrorCollector:
    """
    エラー情報を収集・管理するクラス
    
    複数の処理でエラーが発生した場合に、
    全てのエラー情報を収集して最後にまとめて報告
    """
    
    def __init__(self):
        """エラーコレクターを初期化"""
        self.errors: List[Dict[str, Any]] = []
        logger.debug("🗂️ ErrorCollector を初期化しました")
    
    def add_error(self, context: str, error: Exception, additional_info: Optional[Dict] = None):
        """
        エラー情報を追加
        
        Args:
            context: エラーが発生したコンテキスト（関数名、処理内容など）
            error: 発生した例外
            additional_info: 追加情報（行番号、データなど）
        """
        error_info = {
            'timestamp': time.time(),
            'context': context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'additional_info': additional_info or {}
        }
        
        self.errors.append(error_info)
        logger.error(f"❌ エラー収集: {context} - {type(error).__name__}: {error}")
    
    def has_errors(self) -> bool:
        """エラーが存在するかチェック"""
        return len(self.errors) > 0
    
    def get_error_count(self) -> int:
        """エラー件数を取得"""
        return len(self.errors)
    
    def get_error_summary(self) -> str:
        """
        エラーサマリーを生成
        
        Returns:
            エラー情報をまとめた文字列
        """
        if not self.errors:
            return "エラーはありません"
        
        summary_lines = [f"総エラー件数: {len(self.errors)}"]
        
        for i, error_info in enumerate(self.errors, 1):
            summary_lines.append(
                f"{i}. {error_info['context']}: "
                f"{error_info['error_type']} - {error_info['error_message']}"
            )
        
        return "\n".join(summary_lines)
    
    def clear_errors(self):
        """エラー情報をクリア"""
        error_count = len(self.errors)
        self.errors.clear()
        logger.info(f"🗑️ エラー情報をクリアしました: {error_count}件")