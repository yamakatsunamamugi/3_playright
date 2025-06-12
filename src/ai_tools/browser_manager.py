"""ブラウザ管理機能"""

import os
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserManager:
    """ブラウザインスタンスの管理クラス
    
    既存のChromeプロファイルを使用してブラウザを起動し、
    セッションを維持する機能を提供する。
    """
    
    def __init__(self):
        """初期化"""
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: Dict[str, Page] = {}
        self.logger = logging.getLogger("BrowserManager")
        
        # Chrome プロファイルのデフォルトパス
        self.chrome_profile_path = self._get_default_chrome_profile_path()
        
    def _get_default_chrome_profile_path(self) -> str:
        """デフォルトのChromeプロファイルパスを取得
        
        Returns:
            str: Chromeプロファイルのパス
        """
        import platform
        system = platform.system()
        
        if system == "Darwin":  # macOS
            home = os.path.expanduser("~")
            return f"{home}/Library/Application Support/Google/Chrome/Default"
        elif system == "Windows":
            user_data = os.environ.get("LOCALAPPDATA", "")
            return f"{user_data}\\Google\\Chrome\\User Data\\Default"
        else:  # Linux
            home = os.path.expanduser("~")
            return f"{home}/.config/google-chrome/Default"

    async def start_browser(self, headless: bool = False, use_existing_profile: bool = True) -> bool:
        """ブラウザを起動
        
        Args:
            headless (bool): ヘッドレスモードで起動するか
            use_existing_profile (bool): 既存のChromeプロファイルを使用するか
            
        Returns:
            bool: 起動成功時True
        """
        try:
            self.playwright = await async_playwright().start()
            
            if use_existing_profile and os.path.exists(self.chrome_profile_path):
                # 既存のChromeプロファイルを使用
                self.logger.info(f"既存のChromeプロファイルを使用: {self.chrome_profile_path}")
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=os.path.dirname(self.chrome_profile_path),
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-extensions-except",
                        "--disable-extensions",
                    ]
                )
                self.browser = self.context.browser
            else:
                # 新しいブラウザインスタンスを作成
                self.logger.info("新しいブラウザインスタンスを作成")
                self.browser = await self.playwright.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )
                self.context = await self.browser.new_context()
                
            # User-Agentを設定してbot検出を回避
            await self.context.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            self.logger.info("ブラウザ起動完了")
            return True
            
        except Exception as e:
            self.logger.error(f"ブラウザ起動エラー: {e}")
            return False

    async def create_page(self, page_name: str, url: str = None) -> Optional[Page]:
        """新しいページを作成
        
        Args:
            page_name (str): ページの識別名
            url (str): 初期表示するURL
            
        Returns:
            Optional[Page]: 作成されたページ（失敗時None）
        """
        try:
            if not self.context:
                self.logger.error("ブラウザコンテキストが初期化されていません")
                return None
                
            page = await self.context.new_page()
            self.pages[page_name] = page
            
            if url:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
            self.logger.info(f"ページ作成完了: {page_name}")
            return page
            
        except Exception as e:
            self.logger.error(f"ページ作成エラー: {page_name}, {e}")
            return None

    async def get_page(self, page_name: str) -> Optional[Page]:
        """ページを取得
        
        Args:
            page_name (str): ページの識別名
            
        Returns:
            Optional[Page]: ページ（存在しない場合None）
        """
        return self.pages.get(page_name)

    async def close_page(self, page_name: str) -> bool:
        """ページを閉じる
        
        Args:
            page_name (str): ページの識別名
            
        Returns:
            bool: 成功時True
        """
        try:
            page = self.pages.get(page_name)
            if page:
                await page.close()
                del self.pages[page_name]
                self.logger.info(f"ページ閉じる完了: {page_name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"ページクローズエラー: {page_name}, {e}")
            return False

    async def navigate_to(self, page_name: str, url: str, wait_until: str = "domcontentloaded") -> bool:
        """指定したページでURLに移動
        
        Args:
            page_name (str): ページの識別名
            url (str): 移動先URL
            wait_until (str): 待機条件
            
        Returns:
            bool: 成功時True
        """
        try:
            page = self.pages.get(page_name)
            if not page:
                self.logger.error(f"ページが存在しません: {page_name}")
                return False
                
            await page.goto(url, wait_until=wait_until, timeout=30000)
            self.logger.info(f"ページナビゲーション完了: {page_name} -> {url}")
            return True
            
        except Exception as e:
            self.logger.error(f"ページナビゲーションエラー: {page_name}, {url}, {e}")
            return False

    async def wait_for_selector(self, page_name: str, selector: str, timeout: int = 30) -> bool:
        """要素の出現を待機
        
        Args:
            page_name (str): ページの識別名
            selector (str): 待機する要素のセレクター
            timeout (int): タイムアウト時間（秒）
            
        Returns:
            bool: 要素が見つかった場合True
        """
        try:
            page = self.pages.get(page_name)
            if not page:
                self.logger.error(f"ページが存在しません: {page_name}")
                return False
                
            await page.wait_for_selector(selector, timeout=timeout * 1000)
            return True
            
        except Exception as e:
            self.logger.error(f"要素待機エラー: {page_name}, {selector}, {e}")
            return False

    async def take_screenshot(self, page_name: str, filename: str = None) -> str:
        """スクリーンショットを撮影
        
        Args:
            page_name (str): ページの識別名
            filename (str): 保存ファイル名（None時は自動生成）
            
        Returns:
            str: 保存されたファイルパス
        """
        try:
            page = self.pages.get(page_name)
            if not page:
                self.logger.error(f"ページが存在しません: {page_name}")
                return ""
                
            if not filename:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{page_name}_{timestamp}.png"
            
            await page.screenshot(path=filename)
            self.logger.info(f"スクリーンショット保存: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"スクリーンショット撮影エラー: {page_name}, {e}")
            return ""

    async def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            # 全ページを閉じる
            for page_name in list(self.pages.keys()):
                await self.close_page(page_name)
            
            # ブラウザを閉じる
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
                
            self.logger.info("ブラウザマネージャーのクリーンアップ完了")
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")

    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得
        
        Returns:
            Dict[str, Any]: 現在の状態情報
        """
        return {
            "browser_running": self.browser is not None,
            "context_available": self.context is not None,
            "active_pages": list(self.pages.keys()),
            "chrome_profile_path": self.chrome_profile_path
        }