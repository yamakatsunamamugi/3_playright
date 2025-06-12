"""拡張ブラウザマネージャー - Playwright MCPベースの改善版"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import tempfile
import shutil

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from .enhanced_session_manager import EnhancedSessionManager
from .enhanced_selector_strategy import EnhancedSelectorStrategy

logger = logging.getLogger(__name__)


class EnhancedBrowserManager:
    """Playwright MCPの概念を取り入れた拡張ブラウザマネージャー
    
    主な改善点:
    - セッション永続化と自動復元
    - インテリジェントなセレクター戦略
    - ネットワークレベルの最適化
    - エラーハンドリングの改善
    - リソース管理の最適化
    """
    
    def __init__(
        self,
        use_existing_profile: bool = True,
        headless: bool = False,
        profile_name: Optional[str] = None
    ):
        self.use_existing_profile = use_existing_profile
        self.headless = headless
        self.profile_name = profile_name or "Default"
        
        # コンポーネント
        self.session_manager = EnhancedSessionManager()
        self.selector_strategy = EnhancedSelectorStrategy()
        
        # Playwright関連
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        
        # パフォーマンス設定
        self.performance_config = {
            'block_resources': ['image', 'font', 'media'],
            'block_domains': ['analytics.', 'googletagmanager.', 'facebook.', 'doubleclick.'],
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # 一時ディレクトリ（クリーンアップ用）
        self.temp_dirs: List[str] = []
    
    async def initialize(self) -> bool:
        """ブラウザマネージャーを初期化"""
        try:
            self.playwright = await async_playwright().start()
            
            # ブラウザ起動オプション
            launch_options = {
                'headless': self.headless,
                'args': [
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-notifications',
                    '--disable-geolocation',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ],
                'ignore_default_args': ['--enable-automation']
            }
            
            # 既存プロファイルを使用する場合
            if self.use_existing_profile:
                profile_path = self._get_chrome_profile_path()
                if profile_path:
                    temp_profile = self._create_temp_profile(profile_path)
                    if temp_profile:
                        launch_options['args'].extend([
                            f'--user-data-dir={temp_profile["dir"]}',
                            f'--profile-directory={temp_profile["name"]}'
                        ])
            
            # ブラウザを起動
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            logger.info("Browser manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser manager: {e}")
            return False
    
    def _get_chrome_profile_path(self) -> Optional[str]:
        """Chromeプロファイルのパスを取得"""
        import platform
        
        system = platform.system()
        home = os.path.expanduser("~")
        
        if system == "Darwin":  # macOS
            base_path = os.path.join(home, "Library", "Application Support", "Google", "Chrome")
        elif system == "Windows":
            base_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
        else:  # Linux
            base_path = os.path.join(home, ".config", "google-chrome")
        
        profile_path = os.path.join(base_path, self.profile_name)
        
        if os.path.exists(profile_path):
            return profile_path
        
        logger.warning(f"Chrome profile not found: {profile_path}")
        return None
    
    def _create_temp_profile(self, original_profile: str) -> Optional[Dict[str, str]]:
        """一時プロファイルを作成"""
        try:
            # 一時ディレクトリを作成
            temp_dir = tempfile.mkdtemp(prefix="chrome_temp_")
            self.temp_dirs.append(temp_dir)
            
            profile_name = os.path.basename(original_profile)
            temp_profile_path = os.path.join(temp_dir, profile_name)
            os.makedirs(temp_profile_path, exist_ok=True)
            
            # 重要なファイルのみコピー
            important_files = [
                'Cookies', 'Cookies-journal',
                'Local Storage', 'Session Storage',
                'Web Data', 'Login Data',
                'Preferences'
            ]
            
            for file_name in important_files:
                src = os.path.join(original_profile, file_name)
                dst = os.path.join(temp_profile_path, file_name)
                
                if os.path.exists(src):
                    try:
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src, dst)
                    except Exception as e:
                        logger.warning(f"Failed to copy {file_name}: {e}")
            
            return {'dir': temp_dir, 'name': profile_name}
            
        except Exception as e:
            logger.error(f"Failed to create temp profile: {e}")
            return None
    
    async def create_service_context(
        self,
        service_name: str,
        restore_session: bool = True
    ) -> Optional[BrowserContext]:
        """サービス用のコンテキストを作成
        
        Args:
            service_name: サービス名
            restore_session: セッションを復元するか
            
        Returns:
            作成されたコンテキスト
        """
        try:
            # コンテキストオプション
            context_options = {
                'viewport': self.performance_config['viewport'],
                'user_agent': self.performance_config['user_agent'],
                'accept_downloads': True,
                'ignore_https_errors': True
            }
            
            # コンテキストを作成
            context = await self.browser.new_context(**context_options)
            
            # JavaScript実行でbot検出を回避
            await context.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override navigator.plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        }
                    ]
                });
                
                // Override navigator.languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Override Permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            # パフォーマンス最適化: 不要なリソースをブロック
            await self._setup_request_interception(context)
            
            # セッションを復元
            if restore_session:
                await self.session_manager.restore_session(context, service_name)
            
            self.contexts[service_name] = context
            logger.info(f"Created context for {service_name}")
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to create context for {service_name}: {e}")
            return None
    
    async def _setup_request_interception(self, context: BrowserContext):
        """リクエストインターセプションを設定"""
        
        async def handle_route(route):
            request = route.request
            url = request.url
            resource_type = request.resource_type
            
            # リソースタイプでブロック
            if resource_type in self.performance_config['block_resources']:
                await route.abort()
                return
            
            # ドメインでブロック
            for blocked_domain in self.performance_config['block_domains']:
                if blocked_domain in url:
                    await route.abort()
                    return
            
            # その他は通常通り処理
            await route.continue_()
        
        # すべてのリクエストをインターセプト
        await context.route("**/*", handle_route)
    
    async def create_service_page(
        self,
        service_name: str,
        url: Optional[str] = None
    ) -> Optional[Page]:
        """サービス用のページを作成
        
        Args:
            service_name: サービス名
            url: 初期URL
            
        Returns:
            作成されたページ
        """
        try:
            # コンテキストが存在しない場合は作成
            if service_name not in self.contexts:
                context = await self.create_service_context(service_name)
                if not context:
                    return None
            else:
                context = self.contexts[service_name]
            
            # ページを作成
            page = await context.new_page()
            
            # エラーハンドリング
            page.on("pageerror", lambda e: logger.error(f"Page error in {service_name}: {e}"))
            page.on("console", lambda msg: self._handle_console_message(service_name, msg))
            
            # URLが指定されている場合はナビゲート
            if url:
                await self.safe_goto(page, url)
            
            self.pages[service_name] = page
            logger.info(f"Created page for {service_name}")
            
            return page
            
        except Exception as e:
            logger.error(f"Failed to create page for {service_name}: {e}")
            return None
    
    def _handle_console_message(self, service_name: str, msg):
        """コンソールメッセージを処理"""
        msg_type = msg.type
        text = msg.text
        
        if msg_type in ['error', 'warning']:
            logger.warning(f"Console {msg_type} in {service_name}: {text}")
    
    async def safe_goto(
        self,
        page: Page,
        url: str,
        timeout: int = 30000,
        wait_until: str = "domcontentloaded"
    ) -> bool:
        """安全にページ遷移を行う
        
        Args:
            page: ページオブジェクト
            url: 遷移先URL
            timeout: タイムアウト（ミリ秒）
            wait_until: 待機条件
            
        Returns:
            成功時True
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = await page.goto(
                    url,
                    timeout=timeout,
                    wait_until=wait_until
                )
                
                # レスポンスチェック
                if response and response.status >= 400:
                    logger.warning(f"HTTP {response.status} for {url}")
                
                return True
                
            except Exception as e:
                logger.error(f"Navigation failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数バックオフ
                else:
                    return False
        
        return False
    
    async def execute_with_retry(
        self,
        func: Callable,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        *args,
        **kwargs
    ) -> Any:
        """リトライ機能付きで関数を実行
        
        Args:
            func: 実行する関数
            max_retries: 最大リトライ回数
            delay: 初期遅延時間（秒）
            backoff: バックオフ係数
            *args, **kwargs: 関数の引数
            
        Returns:
            関数の戻り値
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = delay * (backoff ** attempt)
                    await asyncio.sleep(wait_time)
        
        raise last_exception
    
    async def save_all_sessions(self):
        """すべてのセッションを保存"""
        for service_name, context in self.contexts.items():
            try:
                await self.session_manager.save_session(context, service_name)
            except Exception as e:
                logger.error(f"Failed to save session for {service_name}: {e}")
    
    async def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            # セッションを保存
            await self.save_all_sessions()
            
            # ページを閉じる
            for page in self.pages.values():
                try:
                    await page.close()
                except:
                    pass
            
            # コンテキストを閉じる
            for context in self.contexts.values():
                try:
                    await context.close()
                except:
                    pass
            
            # ブラウザを閉じる
            if self.browser:
                await self.browser.close()
            
            # Playwrightを停止
            if self.playwright:
                await self.playwright.stop()
            
            # 一時ディレクトリを削除
            for temp_dir in self.temp_dirs:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to remove temp dir: {e}")
            
            logger.info("Browser manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        return {
            'browser_active': self.browser is not None,
            'contexts': list(self.contexts.keys()),
            'pages': list(self.pages.keys()),
            'session_status': self.session_manager.get_session_status(),
            'performance_config': self.performance_config
        }