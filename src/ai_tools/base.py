"""AI自動化ツールの基底クラス"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import logging
from playwright.async_api import Browser, Page


class AIToolBase(ABC):
    """AI自動化ツールの基底クラス
    
    各AIツール（ChatGPT、Claude、Gemini等）は、このクラスを継承して実装する。
    基本的な動作として以下を提供する：
    - ブラウザでのログイン処理
    - モデル選択
    - プロンプト送信と応答取得
    - エラーハンドリング
    """
    
    def __init__(self, tool_name: str):
        """初期化
        
        Args:
            tool_name (str): ツール名（ChatGPT、Claude等）
        """
        self.tool_name = tool_name
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.logger = logging.getLogger(f"AITool.{tool_name}")
        self.is_logged_in = False
        self.current_model = None
        
        # 各AIツール固有のセレクター辞書
        self.selectors: Dict[str, str] = {}
        
        # 設定可能な項目
        self.available_models: List[str] = []
        self.available_settings: Dict[str, Any] = {}

    @abstractmethod
    async def login(self) -> bool:
        """ログイン処理
        
        既存のChromeプロファイルを使用してログイン済みの場合はスキップ
        
        Returns:
            bool: ログイン成功時True
        """
        pass

    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """利用可能なモデルを取得
        
        Returns:
            List[str]: 利用可能なモデル名リスト
        """
        pass

    @abstractmethod
    async def select_model(self, model_name: str) -> bool:
        """モデル選択
        
        Args:
            model_name (str): 選択するモデル名
            
        Returns:
            bool: 選択成功時True
        """
        pass

    @abstractmethod
    async def get_available_settings(self) -> Dict[str, Any]:
        """利用可能な設定を取得
        
        Returns:
            Dict[str, Any]: 利用可能な設定とその選択肢
        """
        pass

    @abstractmethod
    async def apply_settings(self, settings: Dict[str, Any]) -> bool:
        """設定を適用
        
        Args:
            settings (Dict[str, Any]): 適用する設定
            
        Returns:
            bool: 適用成功時True
        """
        pass

    @abstractmethod
    async def send_prompt(self, text: str) -> str:
        """プロンプト送信と応答取得
        
        Args:
            text (str): 送信するプロンプトテキスト
            
        Returns:
            str: AIからの応答テキスト
        """
        pass

    @abstractmethod
    async def wait_for_response_complete(self) -> bool:
        """応答完了の待機
        
        ストリーミング対応で応答が完全に終了するまで待機
        
        Returns:
            bool: 応答完了時True
        """
        pass

    async def wait_for_element(self, selector: str, timeout: int = 30) -> bool:
        """要素の出現を待機
        
        Args:
            selector (str): 待機する要素のセレクター
            timeout (int): タイムアウト時間（秒）
            
        Returns:
            bool: 要素が見つかった場合True
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            return True
        except Exception as e:
            self.logger.error(f"要素の待機中にエラー: {selector}, {e}")
            return False

    async def take_screenshot(self, filename: str = None) -> str:
        """スクリーンショットを撮影
        
        Args:
            filename (str): 保存ファイル名（None時は自動生成）
            
        Returns:
            str: 保存されたファイルパス
        """
        if not filename:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{self.tool_name}_{timestamp}.png"
        
        try:
            await self.page.screenshot(path=filename)
            self.logger.info(f"スクリーンショット保存: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"スクリーンショット撮影エラー: {e}")
            return ""

    async def cleanup(self):
        """リソースのクリーンアップ
        
        ブラウザとページのクリーンアップを行う
        """
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")

    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得
        
        Returns:
            Dict[str, Any]: 現在の状態情報
        """
        return {
            "tool_name": self.tool_name,
            "is_logged_in": self.is_logged_in,
            "current_model": self.current_model,
            "available_models": self.available_models,
            "browser_connected": self.browser is not None,
            "page_connected": self.page is not None
        }