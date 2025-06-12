from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from enum import Enum


class AIToolStatus(Enum):
    """AIツールの状態"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    PROCESSING = "processing"
    ERROR = "error"


class IAITool(ABC):
    """チームCが実装するAIツール操作のインターフェース"""
    
    @abstractmethod
    def initialize(self, profile_path: Optional[str] = None) -> bool:
        """
        ブラウザとAIツールの初期化
        
        Args:
            profile_path: Chromeプロファイルのパス
            
        Returns:
            初期化成功時True
        """
        pass
    
    @abstractmethod
    def get_status(self) -> AIToolStatus:
        """現在の接続状態を取得"""
        pass
    
    @abstractmethod
    def login(self) -> bool:
        """
        ログイン処理（既にログイン済みの場合はスキップ）
        
        Returns:
            ログイン成功時True
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """利用可能なモデル一覧を取得"""
        pass
    
    @abstractmethod
    def select_model(self, model_name: str) -> bool:
        """
        モデルを選択
        
        Args:
            model_name: 選択するモデル名
            
        Returns:
            選択成功時True
        """
        pass
    
    @abstractmethod
    def send_prompt(self, text: str, timeout: int = 300) -> str:
        """
        プロンプトを送信して応答を取得
        
        Args:
            text: 送信するテキスト
            timeout: タイムアウト秒数
            
        Returns:
            AIの応答テキスト
            
        Raises:
            TimeoutError: タイムアウト時
            ConnectionError: 接続エラー時
        """
        pass
    
    @abstractmethod
    def close(self):
        """ブラウザを閉じてリソース解放"""
        pass


class IAIManager(ABC):
    """AIツール管理のインターフェース"""
    
    @abstractmethod
    def get_tool(self, tool_name: str) -> IAITool:
        """指定されたAIツールのインスタンスを取得"""
        pass
    
    @abstractmethod
    def get_supported_tools(self) -> List[str]:
        """サポートされているAIツール一覧を取得"""
        pass
    
    @abstractmethod
    def initialize_all_tools(self, config: Dict[str, Dict]) -> Dict[str, bool]:
        """
        全てのAIツールを初期化
        
        Args:
            config: {tool_name: {model: str, enabled: bool, ...}}
            
        Returns:
            {tool_name: success_status}
        """
        pass