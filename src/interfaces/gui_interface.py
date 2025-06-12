from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Any
from enum import Enum


class ProcessStatus(Enum):
    """処理状態"""
    IDLE = "idle"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class IGUIController(ABC):
    """チームAが実装するGUIコントローラーのインターフェース"""
    
    @abstractmethod
    def update_progress(self, current: int, total: int, message: str = ""):
        """
        進捗表示を更新
        
        Args:
            current: 現在の処理数
            total: 総処理数
            message: 追加メッセージ
        """
        pass
    
    @abstractmethod
    def add_log(self, message: str, level: str = "INFO"):
        """
        ログを追加表示
        
        Args:
            message: ログメッセージ
            level: ログレベル（INFO, WARNING, ERROR）
        """
        pass
    
    @abstractmethod
    def update_status(self, status: ProcessStatus):
        """処理状態を更新"""
        pass
    
    @abstractmethod
    def get_spreadsheet_config(self) -> Dict[str, str]:
        """
        スプレッドシートの設定を取得
        
        Returns:
            {'url': str, 'sheet_name': str}
        """
        pass
    
    @abstractmethod
    def get_ai_config(self) -> Dict[str, Dict]:
        """
        AI設定を取得
        
        Returns:
            {tool_name: {'enabled': bool, 'model': str, 'settings': dict}}
        """
        pass
    
    @abstractmethod
    def set_process_callback(self, callback: Callable):
        """処理開始時のコールバック関数を設定"""
        pass
    
    @abstractmethod
    def set_stop_callback(self, callback: Callable):
        """処理停止時のコールバック関数を設定"""
        pass


class IProgressWidget(ABC):
    """進捗表示ウィジェットのインターフェース"""
    
    @abstractmethod
    def set_maximum(self, maximum: int):
        """最大値を設定"""
        pass
    
    @abstractmethod
    def set_value(self, value: int):
        """現在値を設定"""
        pass
    
    @abstractmethod
    def set_text(self, text: str):
        """表示テキストを設定"""
        pass


class ILogWidget(ABC):
    """ログ表示ウィジェットのインターフェース"""
    
    @abstractmethod
    def append_log(self, message: str, level: str):
        """ログメッセージを追加"""
        pass
    
    @abstractmethod
    def clear_logs(self):
        """ログをクリア"""
        pass
    
    @abstractmethod
    def export_logs(self, filepath: str):
        """ログをファイルに出力"""
        pass