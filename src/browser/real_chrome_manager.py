"""
実際のChromeプロファイルを使用するブラウザマネージャー
既にログイン済みのセッションを活用
"""

import os
import platform
import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class RealChromeManager:
    """実際のChromeプロファイルを使用するマネージャー"""
    
    def __init__(self, profile_name: str = "Default", headless: bool = False):
        self.profile_name = profile_name
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: Dict[str, Page] = {}
        self.chrome_path = self._get_chrome_path()
        self.user_data_dir = self._get_user_data_dir()
        
    def _get_chrome_path(self) -> str:
        """Chromeの実行ファイルパスを取得"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        elif system == "Windows":
            return "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        else:  # Linux
            return "/usr/bin/google-chrome"
    
    def _get_user_data_dir(self) -> str:
        """ChromeのUser Dataディレクトリを取得"""
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
    
    def get_available_profiles(self) -> list:
        """利用可能なChromeプロファイルを取得"""
        profiles = []
        
        # Local Stateファイルを読み込む
        local_state_path = os.path.join(self.user_data_dir, "Local State")
        if os.path.exists(local_state_path):
            try:
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                
                profile_info = local_state.get('profile', {}).get('info_cache', {})
                for profile_dir, info in profile_info.items():
                    profiles.append({
                        'dir': profile_dir,
                        'name': info.get('name', profile_dir),
                        'has_logged_in': True  # 既存プロファイルは基本的にログイン済み
                    })
            except Exception as e:
                logger.error(f"Failed to read profiles: {e}")
        
        # デフォルトプロファイルを追加
        if os.path.exists(os.path.join(self.user_data_dir, "Default")):
            profiles.insert(0, {
                'dir': 'Default',
                'name': 'デフォルト',
                'has_logged_in': True
            })
            
        return profiles
    
    async def initialize(self) -> bool:
        """実際のChromeを使用してブラウザを初期化"""
        try:
            logger.info(f"Using Chrome profile: {self.profile_name}")
            logger.info(f"User data dir: {self.user_data_dir}")
            
            # Playwrightを起動
            self.playwright = await async_playwright().start()
            
            # 実際のChromeを起動（プロファイルを指定）
            launch_args = [
                f'--profile-directory={self.profile_name}',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-component-extensions-with-background-pages',
                '--disable-extensions-file-access-check',
                '--disable-extensions-http-throttling',
                '--disable-extensions-streaming-logs',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-popup-blocking',
                '--disable-prompt-on-repost',
                '--disable-hang-monitor',
                '--disable-sync',
                '--metrics-recording-only',
                '--safebrowsing-disable-auto-update',
                '--password-store=basic',
                '--use-mock-keychain',
                '--disable-features=RendererCodeIntegrity',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
            
            if self.headless:
                launch_args.extend(['--headless=new'])
            
            # ブラウザを起動
            self.browser = await self.playwright.chromium.launch(
                executable_path=self.chrome_path,
                channel=None,  # カスタムパスを使用
                headless=False,  # 実際のChromeプロファイルはヘッドレスで使えない
                args=launch_args,
                ignore_default_args=[
                    '--enable-automation',
                    '--enable-blink-features=AutomationControlled'
                ],
                chromium_sandbox=False,
                handle_sigint=False,
                handle_sigterm=False,
                handle_sighup=False
            )
            
            # 既存のコンテキストを使用
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                logger.info("Using existing browser context")
            else:
                # 新しいコンテキストを作成（通常は不要）
                self.context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
                )
            
            # 既に開いているページを確認
            existing_pages = self.context.pages
            if existing_pages:
                logger.info(f"Found {len(existing_pages)} existing pages")
                for i, page in enumerate(existing_pages):
                    self.pages[f"existing_{i}"] = page
            
            logger.info("RealChromeManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize real Chrome: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def create_page(self, name: str, url: Optional[str] = None) -> Optional[Page]:
        """新しいページを作成"""
        try:
            if not self.context:
                logger.error("Browser context not initialized")
                return None
            
            # 新しいページを作成
            page = await self.context.new_page()
            self.pages[name] = page
            
            if url:
                logger.info(f"Navigating to {url}")
                try:
                    # ナビゲーション（タイムアウトを長めに）
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    logger.info(f"Successfully loaded {url}")
                    
                    # ページが完全に読み込まれるまで少し待つ
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.warning(f"Navigation warning: {e}")
                    # エラーでも続行
                    
            return page
            
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            return None
    
    async def get_logged_in_page(self, service_name: str, url: str) -> Optional[Page]:
        """ログイン済みのページを取得または作成"""
        try:
            # 既存のページでURLが一致するものを探す
            for name, page in self.pages.items():
                try:
                    current_url = page.url
                    if service_name.lower() in current_url.lower():
                        logger.info(f"Found existing {service_name} page")
                        return page
                except:
                    pass
            
            # 新しいページを作成
            return await self.create_page(service_name, url)
            
        except Exception as e:
            logger.error(f"Failed to get logged in page: {e}")
            return None
    
    async def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            # 実際のChromeプロファイルを使用している場合は
            # ブラウザを閉じない（ユーザーのセッションを保持）
            logger.info("Keeping browser open to preserve user session")
            
            # Playwrightのみ停止
            if self.playwright:
                await self.playwright.stop()
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        return {
            'browser_active': self.browser is not None,
            'context_active': self.context is not None,
            'pages': list(self.pages.keys()),
            'profile_name': self.profile_name,
            'user_data_dir': self.user_data_dir,
            'available_profiles': self.get_available_profiles()
        }