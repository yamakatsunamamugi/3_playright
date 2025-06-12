"""ブラウザ管理機能"""

import os
import logging
import platform
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserManager:
    """ブラウザインスタンスの管理クラス
    
    既存のChromeプロファイルを使用してブラウザを起動し、
    セッションを維持する機能を提供する。
    """
    
    def __init__(self, use_profile: Optional[str] = None):
        """初期化
        
        Args:
            use_profile: 使用するChromeプロファイル名（Noneでデフォルト）
        """
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: Dict[str, Page] = {}
        self.logger = logging.getLogger("BrowserManager")
        
        # Chrome プロファイル設定
        self.profile_name = use_profile or "Default"
        self.chrome_user_data_dir = self._get_chrome_user_data_dir()
        self.chrome_profile_path = os.path.join(self.chrome_user_data_dir, self.profile_name)
        
        # 利用可能なプロファイル一覧を取得
        self.available_profiles = self._get_available_profiles()
        
    def _get_chrome_user_data_dir(self) -> str:
        """ChromeのUser Dataディレクトリパスを取得
        
        Returns:
            str: Chrome User Dataディレクトリのパス
        """
        system = platform.system()
        
        if system == "Darwin":  # macOS
            home = os.path.expanduser("~")
            return os.path.join(home, "Library", "Application Support", "Google", "Chrome")
        elif system == "Windows":
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            return os.path.join(local_app_data, "Google", "Chrome", "User Data")
        else:  # Linux
            home = os.path.expanduser("~")
            return os.path.join(home, ".config", "google-chrome")
    
    def _get_available_profiles(self) -> List[str]:
        """利用可能なChromeプロファイル一覧を取得
        
        Returns:
            List[str]: プロファイル名のリスト
        """
        profiles = []
        
        if not os.path.exists(self.chrome_user_data_dir):
            self.logger.warning(f"Chrome User Dataディレクトリが見つかりません: {self.chrome_user_data_dir}")
            return profiles
        
        # Local Stateファイルからプロファイル情報を読み取る
        local_state_path = os.path.join(self.chrome_user_data_dir, "Local State")
        if os.path.exists(local_state_path):
            try:
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                
                # プロファイル情報を取得
                profile_info = local_state.get('profile', {}).get('info_cache', {})
                for profile_dir, info in profile_info.items():
                    profile_name = info.get('name', profile_dir)
                    profiles.append({
                        'dir': profile_dir,
                        'name': profile_name,
                        'gaia_name': info.get('gaia_name', ''),
                        'user_name': info.get('user_name', '')
                    })
            except Exception as e:
                self.logger.error(f"プロファイル情報の読み取りエラー: {e}")
        
        # デフォルトプロファイルを追加
        if os.path.exists(os.path.join(self.chrome_user_data_dir, "Default")):
            profiles.insert(0, {
                'dir': 'Default',
                'name': 'デフォルト',
                'gaia_name': '',
                'user_name': ''
            })
        
        return profiles

    async def start_browser(self, headless: bool = False, use_existing_profile: bool = True, 
                          profile_dir: Optional[str] = None) -> bool:
        """ブラウザを起動
        
        Args:
            headless (bool): ヘッドレスモードで起動するか
            use_existing_profile (bool): 既存のChromeプロファイルを使用するか
            profile_dir (str): 使用するプロファイルディレクトリ（Noneで現在の設定を使用）
            
        Returns:
            bool: 起動成功時True
        """
        try:
            self.playwright = await async_playwright().start()
            
            # プロファイルディレクトリの決定
            if profile_dir:
                target_profile_dir = os.path.join(self.chrome_user_data_dir, profile_dir)
            else:
                target_profile_dir = self.chrome_profile_path
            
            if use_existing_profile and os.path.exists(target_profile_dir):
                # 既存のChromeプロファイルを使用
                self.logger.info(f"既存のChromeプロファイルを使用: {target_profile_dir}")
                
                # 一時的なユーザーデータディレクトリを作成（元のプロファイルを保護）
                import tempfile
                import shutil
                
                temp_dir = tempfile.mkdtemp(prefix="chrome_temp_")
                temp_profile_dir = os.path.join(temp_dir, os.path.basename(target_profile_dir))
                
                # 必要なファイルのみコピー（Cookie、LocalStorage等）
                important_files = [
                    'Cookies', 'Cookies-journal',
                    'Local Storage', 'Session Storage',
                    'Web Data', 'Login Data',
                    'Preferences'
                ]
                
                os.makedirs(temp_profile_dir, exist_ok=True)
                for file_name in important_files:
                    src = os.path.join(target_profile_dir, file_name)
                    dst = os.path.join(temp_profile_dir, file_name)
                    if os.path.exists(src):
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src, dst)
                
                # ブラウザ起動オプション
                launch_args = [
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-dev-shm-usage",
                    f"--user-data-dir={temp_dir}",
                    f"--profile-directory={os.path.basename(temp_profile_dir)}"
                ]
                
                self.browser = await self.playwright.chromium.launch(
                    headless=headless,
                    args=launch_args,
                    ignore_default_args=["--enable-automation"]
                )
                self.context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                # 一時ディレクトリのパスを保存（クリーンアップ用）
                self.temp_dir = temp_dir
                
            else:
                # 新しいブラウザインスタンスを作成
                self.logger.info("新しいブラウザインスタンスを作成")
                self.browser = await self.playwright.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage"
                    ],
                    ignore_default_args=["--enable-automation"]
                )
                self.context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            
            # JavaScript実行でNavigator.webdriverを削除
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            self.logger.info("ブラウザ起動完了")
            return True
            
        except Exception as e:
            self.logger.error(f"ブラウザ起動エラー: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
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
            
            # 一時ディレクトリを削除
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                import shutil
                try:
                    shutil.rmtree(self.temp_dir)
                    self.logger.info(f"一時ディレクトリを削除: {self.temp_dir}")
                except Exception as e:
                    self.logger.warning(f"一時ディレクトリ削除エラー: {e}")
                
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
            "chrome_user_data_dir": self.chrome_user_data_dir,
            "chrome_profile_path": self.chrome_profile_path,
            "current_profile": self.profile_name,
            "available_profiles": self.available_profiles
        }
    
    def get_available_profiles_info(self) -> List[Dict[str, str]]:
        """利用可能なプロファイル情報を取得
        
        Returns:
            List[Dict[str, str]]: プロファイル情報のリスト
        """
        return self.available_profiles
    
    async def check_login_status(self, url: str, login_indicator: str) -> bool:
        """指定したURLでログイン状態を確認
        
        Args:
            url (str): 確認するURL
            login_indicator (str): ログイン状態を示すセレクターまたはテキスト
            
        Returns:
            bool: ログイン済みの場合True
        """
        try:
            # 一時的なページを作成
            page = await self.context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # ログインインジケーターを確認
            try:
                # セレクターとして試す
                await page.wait_for_selector(login_indicator, timeout=5000)
                is_logged_in = True
            except:
                # テキストとして試す
                is_logged_in = login_indicator in await page.content()
            
            await page.close()
            return is_logged_in
            
        except Exception as e:
            self.logger.error(f"ログイン状態確認エラー: {e}")
            return False