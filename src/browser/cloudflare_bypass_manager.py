"""
Cloudflare回避・AIサービス自動ログイン専用マネージャー
2024年最新技術を統合した高度なブラウザ自動化ソリューション
"""

import os
import json
import logging
import asyncio
import random
import time
from typing import Optional, Dict, Any, List, Callable, Union
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta

from playwright.async_api import (
    async_playwright, Browser, BrowserContext, Page, Playwright,
    TimeoutError as PlaywrightTimeoutError
)

logger = logging.getLogger(__name__)


class CloudflareBypassManager:
    """
    2024年最新技術を統合したCloudflare回避・AIサービス自動ログイン専用マネージャー
    
    主な機能:
    - 最新のbot検出回避技術
    - 高度なセッション管理
    - AIサービス別最適化
    - 自動リトライ・エラーハンドリング
    - パフォーマンス最適化
    """
    
    def __init__(
        self,
        headless: bool = False,
        use_existing_profile: bool = True,
        profile_name: Optional[str] = None,
        proxy: Optional[str] = None,
        debug_mode: bool = False
    ):
        """
        初期化
        
        Args:
            headless: ヘッドレスモードで動作するか
            use_existing_profile: 既存のChromeプロファイルを使用するか
            profile_name: 使用するプロファイル名
            proxy: 使用するプロキシ（形式: host:port）
            debug_mode: デバッグモードを有効にするか
        """
        self.headless = headless
        self.use_existing_profile = use_existing_profile
        self.profile_name = profile_name or "Default"
        self.proxy = proxy
        self.debug_mode = debug_mode
        
        # Playwright関連
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        
        # セッション管理
        self.session_dir = Path("auth_states")
        self.session_dir.mkdir(exist_ok=True)
        
        # 一時ディレクトリ管理
        self.temp_dirs: List[str] = []
        
        # パフォーマンス最適化設定
        self.performance_config = self._get_performance_config()
        
        # ステルス設定
        self.stealth_config = self._get_stealth_config()
        
        # エラーハンドリング設定
        self.retry_config = {
            'max_retries': 3,
            'base_delay': 1.0,
            'max_delay': 60.0,
            'backoff_factor': 2.0
        }
        
        # ログレベル設定
        if debug_mode:
            logging.basicConfig(level=logging.DEBUG)
        
        logger.info("CloudflareBypassManager initialized")
    
    def _get_performance_config(self) -> Dict[str, Any]:
        """パフォーマンス最適化設定を取得"""
        return {
            'block_resources': [
                # AIサイトでは全リソースを許可
            ],
            'block_domains': [
                'googletagmanager.com',
                'google-analytics.com',
                'googleadservices.com',
                'doubleclick.net',
                'facebook.com',
                'facebook.net',
                'twitter.com',
                'linkedin.com',
                'youtube.com',
                'googlesyndication.com',
                'adsystem.com'
            ],
            'viewport': {'width': 1920, 'height': 1080},
            'user_agents': [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            ]
        }
    
    def _get_stealth_config(self) -> Dict[str, Any]:
        """ステルス設定を取得"""
        return {
            'launch_args': [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-notifications',
                '--disable-popup-blocking',
                '--disable-geolocation',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-default-apps',
                '--no-default-browser-check',
                '--no-first-run',
                '--window-size=1920,1080',
                '--start-maximized'
            ],
            'ignore_default_args': [
                '--enable-automation',
                '--enable-blink-features=AutomationControlled'
            ]
        }
    
    async def initialize(self) -> bool:
        """
        ブラウザマネージャーを初期化
        
        Returns:
            成功時True
        """
        try:
            logger.info("Initializing CloudflareBypassManager...")
            
            # Playwright起動
            self.playwright = await async_playwright().start()
            
            # ブラウザ起動オプション設定
            launch_options = {
                'headless': self.headless,
                'args': self.stealth_config['launch_args'],
                'ignore_default_args': self.stealth_config['ignore_default_args']
            }
            
            # プロキシ設定
            if self.proxy:
                proxy_parts = self.proxy.split(':')
                if len(proxy_parts) == 2:
                    launch_options['proxy'] = {
                        'server': f"http://{proxy_parts[0]}:{proxy_parts[1]}"
                    }
            
            # ブラウザ起動
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            logger.info("Browser launched successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    async def create_stealth_context(
        self,
        service_name: str,
        restore_session: bool = True
    ) -> Optional[BrowserContext]:
        """
        ステルス機能付きのコンテキストを作成
        
        Args:
            service_name: サービス名
            restore_session: セッションを復元するか
            
        Returns:
            作成されたコンテキスト
        """
        try:
            logger.info(f"Creating stealth context for {service_name}")
            
            # ランダムなUser-Agentを選択
            user_agent = random.choice(self.performance_config['user_agents'])
            
            # コンテキストオプション
            context_options = {
                'viewport': self.performance_config['viewport'],
                'user_agent': user_agent,
                'accept_downloads': True,
                'ignore_https_errors': True,
                'java_script_enabled': True,
                'bypass_csp': True,
                'extra_http_headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            }
            
            # セッション復元
            if restore_session:
                session_file = self.session_dir / f"{service_name}_session.json"
                if session_file.exists():
                    try:
                        context_options['storage_state'] = str(session_file)
                        logger.info(f"Restored session for {service_name}")
                    except Exception as e:
                        logger.warning(f"Failed to restore session for {service_name}: {e}")
            
            # コンテキスト作成
            context = await self.browser.new_context(**context_options)
            
            # 高度なbot検出回避スクリプト
            await self._inject_stealth_scripts(context)
            
            # リクエストインターセプション設定（無効化）
            # await self._setup_request_interception(context)
            
            # コンテキストを保存
            self.contexts[service_name] = context
            
            logger.info(f"Stealth context created for {service_name}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create stealth context for {service_name}: {e}")
            return None
    
    async def _inject_stealth_scripts(self, context: BrowserContext):
        """
        高度なbot検出回避スクリプトを注入
        """
        stealth_script = """
        // 基本的なWebDriverプロパティを削除
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Chrome runtime を偽装
        window.chrome = {
            runtime: {
                onConnect: undefined,
                onMessage: undefined,
                onInstallStateChanged: undefined,
                onUpdateAvailable: undefined,
                onRestartRequired: undefined,
                onStartup: undefined,
                onSuspend: undefined,
                onSuspendCanceled: undefined
            }
        };
        
        // Permissions API を偽装
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Languages を偽装
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Platform を偽装
        Object.defineProperty(navigator, 'platform', {
            get: () => 'MacIntel'
        });
        
        // Plugins を偽装
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {
                        type: "application/x-google-chrome-pdf",
                        suffixes: "pdf",
                        description: "Portable Document Format",
                        enabledPlugin: Plugin
                    },
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {
                        type: "application/x-nacl",
                        suffixes: "",
                        description: "Native Client Executable",
                        enabledPlugin: Plugin
                    },
                    1: {
                        type: "application/x-pnacl",
                        suffixes: "",
                        description: "Portable Native Client Executable",
                        enabledPlugin: Plugin
                    },
                    description: "Native Client",
                    filename: "internal-nacl-plugin",
                    length: 2,
                    name: "Native Client"
                }
            ]
        });
        
        // WebGL Vendor を偽装
        const getParameter = WebGLRenderingContext.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter(parameter);
        };
        
        // Canvas fingerprinting を回避
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {
            const imageData = originalToDataURL.apply(this, args);
            // わずかにノイズを追加
            return imageData + Math.random().toString(36).substr(2, 5);
        };
        
        // WebRTC IP leak を防ぐ
        const originalRTCPeerConnection = window.RTCPeerConnection;
        window.RTCPeerConnection = function(...args) {
            const pc = new originalRTCPeerConnection(...args);
            pc.createDataChannel = () => {};
            return pc;
        };
        
        // Screen resolution を偽装
        Object.defineProperty(screen, 'width', {
            get: () => 1920
        });
        Object.defineProperty(screen, 'height', {
            get: () => 1080
        });
        Object.defineProperty(screen, 'availWidth', {
            get: () => 1920
        });
        Object.defineProperty(screen, 'availHeight', {
            get: () => 1080
        });
        
        // Battery API を無効化
        if ('getBattery' in navigator) {
            navigator.getBattery = () => Promise.reject(new Error('Battery API is not supported'));
        }
        
        // Timezone を偽装
        Object.defineProperty(Intl, 'DateTimeFormat', {
            value: function(...args) {
                const options = args[1] || {};
                options.timeZone = 'America/New_York';
                return new Intl.DateTimeFormat(args[0], options);
            }
        });
        
        // Mouse movements を自然に見せる
        let lastMouseX = 0;
        let lastMouseY = 0;
        document.addEventListener('mousemove', function(e) {
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
        });
        
        // Perform human-like actions
        const originalAddEventListener = EventTarget.prototype.addEventListener;
        EventTarget.prototype.addEventListener = function(type, listener, options) {
            if (type === 'click' || type === 'mousedown' || type === 'mouseup') {
                const newListener = function(event) {
                    // Add slight delay to simulate human reaction time
                    setTimeout(() => {
                        listener.call(this, event);
                    }, Math.random() * 10 + 5);
                };
                return originalAddEventListener.call(this, type, newListener, options);
            }
            return originalAddEventListener.call(this, type, listener, options);
        };
        
        console.log('🛡️ Stealth mode activated');
        """
        
        await context.add_init_script(stealth_script)
        logger.debug("Stealth scripts injected")
    
    async def _setup_request_interception(self, context: BrowserContext):
        """
        リクエストインターセプションを設定してパフォーマンスを最適化
        """
        # AI サービスではリクエストインターセプションを無効化
        logger.debug("Request interception disabled for AI services")
    
    async def create_page_with_stealth(
        self,
        service_name: str,
        url: Optional[str] = None
    ) -> Optional[Page]:
        """
        ステルス機能付きのページを作成
        
        Args:
            service_name: サービス名
            url: 初期URL
            
        Returns:
            作成されたページ
        """
        try:
            # コンテキストが存在しない場合は作成
            if service_name not in self.contexts:
                context = await self.create_stealth_context(service_name)
                if not context:
                    return None
            else:
                context = self.contexts[service_name]
            
            # ページを作成
            page = await context.new_page()
            
            # ページレベルのイベントハンドラー設定
            await self._setup_page_handlers(page, service_name)
            
            # URLが指定されている場合はナビゲート
            if url:
                logger.info(f"Navigating to {url}...")
                success = await self.safe_goto(page, url)
                if not success:
                    logger.error(f"Failed to navigate to {url}")
                    await page.close()
                    return None
                logger.info(f"Successfully navigated to {url}")
            else:
                logger.info("No URL specified, page created with blank page")
            
            # ページを保存
            self.pages[service_name] = page
            
            logger.info(f"Stealth page created for {service_name}")
            return page
            
        except Exception as e:
            logger.error(f"Failed to create stealth page for {service_name}: {e}")
            return None
    
    async def _setup_page_handlers(self, page: Page, service_name: str):
        """
        ページレベルのイベントハンドラーを設定
        """
        def handle_page_error(error):
            logger.error(f"Page error in {service_name}: {error}")
        
        def handle_console_message(msg):
            if msg.type in ['error', 'warning']:
                logger.warning(f"Console {msg.type} in {service_name}: {msg.text}")
            elif self.debug_mode:
                logger.debug(f"Console {msg.type} in {service_name}: {msg.text}")
        
        def handle_request_failed(request):
            logger.warning(f"Request failed in {service_name}: {request.url}")
        
        def handle_response(response):
            if response.status >= 400:
                logger.warning(f"HTTP {response.status} in {service_name}: {response.url}")
        
        # イベントハンドラーを登録
        page.on("pageerror", handle_page_error)
        page.on("console", handle_console_message)
        page.on("requestfailed", handle_request_failed)
        page.on("response", handle_response)
    
    async def safe_goto(
        self,
        page: Page,
        url: str,
        timeout: int = 30000,
        wait_until: str = "domcontentloaded"
    ) -> bool:
        """
        安全にページ遷移を行う（リトライ機能付き）
        
        Args:
            page: ページオブジェクト
            url: 遷移先URL
            timeout: タイムアウト（ミリ秒）
            wait_until: 待機条件
            
        Returns:
            成功時True
        """
        async def navigate():
            response = await page.goto(url, timeout=timeout, wait_until=wait_until)
            
            # Cloudflareチャレンジページかどうかを確認
            if await self._is_cloudflare_challenge(page):
                logger.info(f"Cloudflare challenge detected on {url}")
                await self._handle_cloudflare_challenge(page)
            
            # レスポンスステータスを確認
            if response and response.status >= 400:
                raise Exception(f"HTTP {response.status}")
            
            return True
        
        return await self._execute_with_retry(navigate)
    
    async def _is_cloudflare_challenge(self, page: Page) -> bool:
        """
        Cloudflareチャレンジページかどうかを判定
        """
        try:
            # Cloudflareの特徴的な要素をチェック
            cloudflare_indicators = [
                'div[id*="challenge"]',
                'div[class*="challenge"]',
                'div[class*="cf-"]',
                'title:has-text("Just a moment")',
                'title:has-text("Checking your browser")',
                'h1:has-text("Checking your browser")',
                'h2:has-text("Checking your browser")'
            ]
            
            for indicator in cloudflare_indicators:
                try:
                    await page.wait_for_selector(indicator, timeout=2000)
                    return True
                except PlaywrightTimeoutError:
                    continue
            
            # ページタイトルとURLからも判定
            title = await page.title()
            url = page.url
            
            if ("cloudflare" in title.lower() or 
                "challenge" in title.lower() or
                "checking" in title.lower() or
                "challenge" in url.lower()):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking Cloudflare challenge: {e}")
            return False
    
    async def _handle_cloudflare_challenge(self, page: Page, max_wait: int = 30):
        """
        Cloudflareチャレンジを処理
        
        Args:
            page: ページオブジェクト
            max_wait: 最大待機時間（秒）
        """
        logger.info("Handling Cloudflare challenge...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # チャレンジが完了したかチェック
                if not await self._is_cloudflare_challenge(page):
                    logger.info("Cloudflare challenge passed")
                    return True
                
                # 少し待機
                await asyncio.sleep(1)
                
                # 人間らしいマウス動作を追加
                await self._simulate_human_behavior(page)
                
            except Exception as e:
                logger.error(f"Error during Cloudflare challenge: {e}")
                break
        
        logger.warning("Cloudflare challenge timeout")
        return False
    
    async def _simulate_human_behavior(self, page: Page):
        """
        人間らしい動作をシミュレート
        """
        try:
            # ランダムなマウス移動
            viewport = page.viewport_size
            if viewport:
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # ランダムなスクロール
            scroll_delta = random.randint(-100, 100)
            await page.mouse.wheel(0, scroll_delta)
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
        except Exception as e:
            logger.debug(f"Error simulating human behavior: {e}")
    
    async def _execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        リトライ機能付きで関数を実行
        
        Args:
            func: 実行する関数
            *args, **kwargs: 関数の引数
            
        Returns:
            関数の戻り値
        """
        max_retries = self.retry_config['max_retries']
        base_delay = self.retry_config['base_delay']
        backoff_factor = self.retry_config['backoff_factor']
        max_delay = self.retry_config['max_delay']
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                
                if attempt < max_retries - 1:
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
        
        logger.error(f"All {max_retries} attempts failed")
        raise last_exception
    
    async def save_session(self, service_name: str) -> bool:
        """
        セッション状態を保存
        
        Args:
            service_name: サービス名
            
        Returns:
            成功時True
        """
        try:
            context = self.contexts.get(service_name)
            if not context:
                logger.error(f"Context not found for {service_name}")
                return False
            
            session_file = self.session_dir / f"{service_name}_session.json"
            
            # セッション状態を保存
            await context.storage_state(path=str(session_file))
            
            logger.info(f"Session saved for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session for {service_name}: {e}")
            return False
    
    async def load_session(self, service_name: str) -> bool:
        """
        セッション状態を読み込み
        
        Args:
            service_name: サービス名
            
        Returns:
            成功時True
        """
        try:
            session_file = self.session_dir / f"{service_name}_session.json"
            
            if not session_file.exists():
                logger.warning(f"Session file not found for {service_name}")
                return False
            
            # セッションファイルが古すぎる場合は無視
            file_age = datetime.now() - datetime.fromtimestamp(session_file.stat().st_mtime)
            if file_age > timedelta(days=7):  # 7日以上古い
                logger.warning(f"Session file too old for {service_name}")
                return False
            
            logger.info(f"Session loaded for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load session for {service_name}: {e}")
            return False
    
    async def cleanup(self):
        """
        リソースのクリーンアップ
        """
        try:
            logger.info("Starting cleanup...")
            
            # セッションを保存
            for service_name in self.contexts.keys():
                await self.save_session(service_name)
            
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
                except:
                    pass
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        現在の状態を取得
        
        Returns:
            状態情報
        """
        return {
            'browser_active': self.browser is not None,
            'contexts': list(self.contexts.keys()),
            'pages': list(self.pages.keys()),
            'headless': self.headless,
            'use_existing_profile': self.use_existing_profile,
            'profile_name': self.profile_name,
            'proxy': self.proxy,
            'debug_mode': self.debug_mode,
            'session_dir': str(self.session_dir),
            'temp_dirs_count': len(self.temp_dirs)
        }