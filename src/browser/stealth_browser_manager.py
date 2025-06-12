"""
最強のステルスブラウザマネージャー
undetected-chromedriver技術を統合
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import tempfile
import shutil

logger = logging.getLogger(__name__)


class StealthBrowserManager:
    """最強のステルスブラウザマネージャー"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: Dict[str, Page] = {}
        self.temp_profile_dir = None
        
    async def initialize(self) -> bool:
        """ブラウザを初期化（最強のステルス設定）"""
        try:
            self.playwright = await async_playwright().start()
            
            # 一時プロファイルディレクトリを作成
            self.temp_profile_dir = tempfile.mkdtemp(prefix="stealth_chrome_")
            
            # Chromeを起動（undetected-chromedriver相当の設定）
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                channel="chrome",  # 実際のChromeを使用
                args=[
                    f'--user-data-dir={self.temp_profile_dir}',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-infobars',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-first-run',
                    '--no-service-autorun',
                    '--password-store=basic',
                    '--disable-features=ChromeWhatsNewUI',
                    '--use-mock-keychain',
                    '--disable-web-security',
                    '--disable-site-isolation-trials',
                    '--disable-features=IsolateOrigins,site-per-process',
                    # ウィンドウサイズ
                    '--window-size=1920,1080',
                    '--start-maximized',
                    # 追加のステルス設定
                    '--disable-plugins-discovery',
                    '--disable-gpu-sandbox',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--disable-translate',
                    '--metrics-recording-only',
                    '--mute-audio',
                    '--no-default-browser-check',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--disable-breakpad',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-features=StandardizedBrowserKeyboardAccessibility',
                    '--force-color-profile=srgb'
                ],
                ignore_default_args=[
                    '--enable-automation',
                    '--enable-blink-features=AutomationControlled'
                ]
            )
            
            # コンテキストを作成（最強のステルス設定）
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                screen={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                permissions=[],
                device_scale_factor=1,
                is_mobile=False,
                has_touch=False,
                color_scheme='light',
                reduced_motion='no-preference',
                forced_colors='none'
            )
            
            # 最強のステルススクリプトを注入
            await self.context.add_init_script("""
                // ========== 基本的なWebDriver検出の回避 ==========
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                delete navigator.__proto__.webdriver;
                
                // ========== Chrome特有のプロパティ ==========
                window.chrome = {
                    runtime: {
                        connect: () => {},
                        sendMessage: () => {},
                        onMessage: { addListener: () => {} }
                    },
                    loadTimes: () => ({}),
                    csi: () => ({}),
                    app: {
                        isInstalled: false,
                        getDetails: () => null,
                        getIsInstalled: () => false,
                        installState: () => 'not_installed',
                        runningState: () => 'cannot_run'
                    }
                };
                
                // ========== Navigator プロパティの偽装 ==========
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {
                                type: "application/x-google-chrome-pdf",
                                suffixes: "pdf",
                                description: "Portable Document Format",
                                enabledPlugin: {}
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
                                enabledPlugin: {}
                            },
                            description: "Native Client",
                            filename: "internal-nacl-plugin",
                            length: 1,
                            name: "Native Client"
                        }
                    ]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                Object.defineProperty(navigator, 'mimeTypes', {
                    get: () => [
                        {
                            type: 'application/pdf',
                            suffixes: 'pdf',
                            description: 'Portable Document Format',
                            enabledPlugin: navigator.plugins[0]
                        }
                    ]
                });
                
                // ========== Permission API ==========
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // ========== WebGL Vendor ==========
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.apply(this, arguments);
                };
                
                const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter2.apply(this, arguments);
                };
                
                // ========== Canvas Fingerprint ==========
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                const originalToBlob = HTMLCanvasElement.prototype.toBlob;
                const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                
                let noiseSeed = Math.random();
                
                HTMLCanvasElement.prototype.toDataURL = function(...args) {
                    const context = this.getContext('2d');
                    if (context) {
                        const imageData = context.getImageData(0, 0, this.width, this.height);
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] = imageData.data[i] + (noiseSeed * 0.01);
                            imageData.data[i+1] = imageData.data[i+1] + (noiseSeed * 0.01);
                            imageData.data[i+2] = imageData.data[i+2] + (noiseSeed * 0.01);
                        }
                        context.putImageData(imageData, 0, 0);
                    }
                    return originalToDataURL.apply(this, args);
                };
                
                // ========== CDP Detection回避 ==========
                let CDP_PRESENT = false;
                Object.defineProperty(window, 'CDP_PRESENT', {
                    get: () => false,
                    set: () => false,
                    configurable: false
                });
                
                // ========== Console.debug を通常のconsole.logに ==========
                const originalConsoleDebug = console.debug;
                console.debug = console.log;
                
                // ========== Automation検出の回避 ==========
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                
                Object.defineProperty(window, '_phantom', {
                    get: () => undefined
                });
                
                Object.defineProperty(window, 'callPhantom', {
                    get: () => undefined
                });
                
                // ========== その他の検出回避 ==========
                window.chrome.runtime.sendMessage = () => {};
                window.chrome.runtime.connect = () => ({
                    onMessage: { addListener: () => {} },
                    onDisconnect: { addListener: () => {} },
                    postMessage: () => {}
                });
                
                // ========== DevTools検出の回避 ==========
                let devtools = {open: false, orientation: null};
                const threshold = 160;
                setInterval(() => {
                    if (window.outerHeight - window.innerHeight > threshold || 
                        window.outerWidth - window.innerWidth > threshold) {
                        if (!devtools.open) {
                            devtools.open = true;
                            // DevToolsが開いてもエラーを出さない
                        }
                    } else {
                        devtools.open = false;
                    }
                }, 500);
                
                console.log('🛡️ Ultimate Stealth Mode Activated');
            """)
            
            # ページロード時の追加設定
            self.context.on('page', self._on_new_page)
            
            logger.info("StealthBrowserManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    async def _on_new_page(self, page: Page):
        """新しいページが作成されたときの処理"""
        # ダイアログを自動的に承認
        page.on('dialog', lambda dialog: dialog.accept())
        
        # エラーを抑制
        page.on('pageerror', lambda error: logger.debug(f"Page error suppressed: {error}"))
        
        # コンソールメッセージをフィルタ
        page.on('console', self._handle_console_message)
    
    def _handle_console_message(self, msg):
        """コンソールメッセージのハンドリング"""
        if msg.type in ['error', 'warning']:
            # Cloudflare関連のエラーは無視
            text = msg.text.lower()
            if any(keyword in text for keyword in ['cloudflare', 'challenge', 'turnstile']):
                return
        logger.debug(f"Console {msg.type}: {msg.text}")
    
    async def create_page(self, name: str, url: Optional[str] = None) -> Optional[Page]:
        """ステルスページを作成"""
        try:
            if not self.context:
                logger.error("Browser context not initialized")
                return None
                
            page = await self.context.new_page()
            self.pages[name] = page
            
            # 追加のページレベル設定
            await page.evaluate("""
                // ページレベルの追加保護
                Object.defineProperty(document, 'hidden', {
                    get: () => false
                });
                
                Object.defineProperty(document, 'visibilityState', {
                    get: () => 'visible'
                });
            """)
            
            if url:
                logger.info(f"Navigating to {url} with stealth mode")
                try:
                    # ゆっくりとしたナビゲーション（人間らしく）
                    await asyncio.sleep(0.5)
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    
                    # Cloudflareチャレンジの自動処理
                    await self._handle_cloudflare_challenge(page)
                    
                    logger.info(f"Successfully loaded {url}")
                except Exception as e:
                    logger.error(f"Navigation error: {e}")
                    # エラーでも続行
                
            return page
            
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            return None
    
    async def _handle_cloudflare_challenge(self, page: Page, max_wait: int = 30):
        """Cloudflareチャレンジを自動処理"""
        try:
            # Cloudflareチャレンジを検出
            for i in range(max_wait):
                # チャレンジページの特徴的な要素を探す
                cf_challenge = await page.query_selector('div[class*="challenge"]')
                cf_turnstile = await page.query_selector('iframe[src*="challenges.cloudflare.com"]')
                
                if cf_challenge or cf_turnstile:
                    logger.info(f"Cloudflare challenge detected, waiting... ({i+1}/{max_wait})")
                    
                    # 人間らしいマウス動作
                    await self._simulate_human_mouse(page)
                    
                    await asyncio.sleep(1)
                else:
                    # チャレンジが終了したかチェック
                    title = await page.title()
                    if 'just a moment' not in title.lower() and 'checking' not in title.lower():
                        logger.info("Cloudflare challenge passed!")
                        break
                        
            # 追加の待機
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.debug(f"Challenge handler error: {e}")
    
    async def _simulate_human_mouse(self, page: Page):
        """人間らしいマウス動作をシミュレート"""
        try:
            import random
            
            viewport = page.viewport_size
            if not viewport:
                return
                
            # ランダムな位置にマウスを移動
            for _ in range(3):
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                await page.mouse.move(x, y, steps=random.randint(10, 30))
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # 小さなスクロール
            await page.mouse.wheel(0, random.randint(-50, 50))
            
        except Exception as e:
            logger.debug(f"Mouse simulation error: {e}")
    
    async def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            for page in self.pages.values():
                try:
                    await page.close()
                except:
                    pass
                
            if self.context:
                await self.context.close()
                
            if self.browser:
                await self.browser.close()
                
            if self.playwright:
                await self.playwright.stop()
            
            # 一時プロファイルを削除
            if self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
                try:
                    shutil.rmtree(self.temp_profile_dir)
                except:
                    pass
                
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        return {
            'browser_active': self.browser is not None,
            'context_active': self.context is not None,
            'pages': list(self.pages.keys()),
            'headless': self.headless
        }