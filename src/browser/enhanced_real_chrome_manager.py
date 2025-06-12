"""
拡張版実際のChromeマネージャー
CDP接続を優先し、手動起動のChromeを活用
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
import json
from pathlib import Path
import random

logger = logging.getLogger(__name__)


class EnhancedRealChromeManager:
    """拡張版実際のChromeマネージャー（CDP接続優先）"""
    
    def __init__(self, cdp_port: int = 9222, profile_name: str = "Default"):
        self.cdp_port = cdp_port
        self.profile_name = profile_name
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: Dict[str, Page] = {}
        self.chrome_path = self._get_chrome_path()
        self.user_data_dir = self._get_user_data_dir()
        self.is_cdp_connection = False
        
    def _get_chrome_path(self) -> str:
        """Chromeの実行ファイルパスを取得"""
        import platform
        system = platform.system()
        
        if system == "Darwin":  # macOS
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        elif system == "Windows":
            return "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        else:  # Linux
            return "/usr/bin/google-chrome"
    
    def _get_user_data_dir(self) -> str:
        """ChromeのUser Dataディレクトリを取得"""
        import platform
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
    
    async def initialize(self) -> bool:
        """ブラウザを初期化（CDP接続を優先）"""
        try:
            logger.info("EnhancedRealChromeManager initializing...")
            
            # Playwrightを起動
            self.playwright = await async_playwright().start()
            
            # 1. まずCDP接続を試みる
            if await self._try_cdp_connection():
                logger.info("✅ CDP接続成功 - 既存のChromeセッションを使用")
                self.is_cdp_connection = True
                return True
            
            # 2. CDP接続失敗時は通常のプロファイル起動
            logger.info("CDP接続失敗 - 通常のプロファイル起動を試行")
            return await self._launch_with_profile()
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def _try_cdp_connection(self) -> bool:
        """CDP経由で既存のChromeに接続を試みる"""
        try:
            logger.info(f"Attempting CDP connection on port {self.cdp_port}...")
            
            # CDP URLを構築
            cdp_url = f"http://localhost:{self.cdp_port}"
            
            # CDP接続を試行
            self.browser = await self.playwright.chromium.connect_over_cdp(cdp_url)
            
            # 既存のコンテキストを取得
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                logger.info(f"Using existing context with {len(self.context.pages)} pages")
            else:
                # 新しいコンテキストを作成
                self.context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
            
            # 既存のページを確認
            existing_pages = self.context.pages
            for i, page in enumerate(existing_pages):
                self.pages[f"existing_{i}"] = page
                logger.info(f"Found existing page {i}: {page.url}")
            
            return True
            
        except Exception as e:
            logger.debug(f"CDP connection failed: {e}")
            return False
    
    async def _launch_with_profile(self) -> bool:
        """プロファイルを指定してChromeを起動"""
        try:
            logger.info(f"Launching Chrome with profile: {self.profile_name}")
            
            # プロファイルディレクトリのパス
            profile_path = os.path.join(self.user_data_dir, self.profile_name)
            
            launch_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-popup-blocking',
                '--disable-extensions-file-access-check',
                '--disable-extensions-http-throttling',
                f'--remote-debugging-port={self.cdp_port}'  # CDP用ポートを開く
            ]
            
            # launch_persistent_contextを使用
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                executable_path=self.chrome_path,
                channel=None,
                headless=False,
                args=launch_args,
                ignore_default_args=[
                    '--enable-automation',
                    '--enable-blink-features=AutomationControlled'
                ],
                chromium_sandbox=False,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            
            # ブラウザオブジェクトを取得
            self.browser = self.context.browser
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch with profile: {e}")
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
            
            # 人間らしい動作を追加
            await self._add_human_like_behavior(page)
            
            if url:
                logger.info(f"Navigating to {url}")
                try:
                    # ナビゲーション前にランダムな待機
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    logger.info(f"Successfully loaded {url}")
                    
                    # Cloudflareチャレンジのチェック
                    await self._handle_cloudflare_challenge(page)
                    
                except Exception as e:
                    logger.warning(f"Navigation warning: {e}")
                    
            return page
            
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            return None
    
    async def _add_human_like_behavior(self, page: Page):
        """人間らしい動作を追加"""
        # ページロード時のランダムなマウス動作
        page.on('load', lambda: asyncio.create_task(self._simulate_human_mouse(page)))
        
        # 定期的なマイクロ動作
        async def periodic_actions():
            while page in self.pages.values():
                try:
                    await asyncio.sleep(random.uniform(5, 15))
                    await self._simulate_micro_movements(page)
                except:
                    break
        
        asyncio.create_task(periodic_actions())
    
    async def _simulate_human_mouse(self, page: Page):
        """人間らしいマウス動作をシミュレート"""
        try:
            viewport = page.viewport_size
            if not viewport:
                return
            
            # ランダムなパスでマウスを移動
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                
                # ベジェ曲線的な動きを再現
                steps = random.randint(20, 40)
                await page.mouse.move(x, y, steps=steps)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # 時々小さなスクロール
            if random.random() < 0.3:
                await page.mouse.wheel(0, random.randint(-100, 100))
            
        except Exception as e:
            logger.debug(f"Mouse simulation error: {e}")
    
    async def _simulate_micro_movements(self, page: Page):
        """マイクロ動作をシミュレート"""
        try:
            # 小さなマウス移動
            current_pos = await page.evaluate("() => ({ x: window.mouseX || 0, y: window.mouseY || 0 })")
            if current_pos['x'] > 0 and current_pos['y'] > 0:
                new_x = current_pos['x'] + random.randint(-5, 5)
                new_y = current_pos['y'] + random.randint(-5, 5)
                await page.mouse.move(new_x, new_y, steps=random.randint(3, 7))
        except:
            pass
    
    async def _handle_cloudflare_challenge(self, page: Page, max_wait: int = 30):
        """Cloudflareチャレンジを処理"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < max_wait:
                # チャレンジページの検出
                is_challenge = await page.evaluate("""
                    () => {
                        const title = document.title.toLowerCase();
                        const hasCfChallenge = document.querySelector('[class*="challenge"]') !== null;
                        const hasTurnstile = document.querySelector('iframe[src*="challenges.cloudflare.com"]') !== null;
                        return title.includes('just a moment') || 
                               title.includes('checking') || 
                               hasCfChallenge || 
                               hasTurnstile;
                    }
                """)
                
                if is_challenge:
                    logger.info("Cloudflare challenge detected, waiting...")
                    
                    # 人間らしい動作を継続
                    await self._simulate_human_mouse(page)
                    
                    # ページの任意の場所をクリック（非インタラクティブ）
                    if random.random() < 0.2:
                        viewport = page.viewport_size
                        if viewport:
                            x = random.randint(200, viewport['width'] - 200)
                            y = random.randint(200, viewport['height'] - 200)
                            await page.mouse.click(x, y)
                    
                    await asyncio.sleep(1)
                else:
                    logger.info("Cloudflare challenge passed!")
                    break
                    
        except Exception as e:
            logger.debug(f"Challenge handler error: {e}")
    
    async def get_logged_in_page(self, service_name: str, url: str) -> Optional[Page]:
        """ログイン済みのページを取得または作成"""
        try:
            # 既存のページでサービスが開いているか確認
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
    
    async def ensure_logged_in(self, page: Page, service_name: str) -> bool:
        """ログイン状態を確認"""
        try:
            if service_name.lower() == "chatgpt":
                # ChatGPTのログイン状態確認
                login_button = await page.query_selector('[data-testid="login-button"]')
                if login_button:
                    logger.info("ChatGPT: ログインが必要です")
                    return False
                
                # チャット入力欄があればログイン済み
                chat_input = await page.query_selector('[data-testid="prompt-textarea"]')
                return chat_input is not None
                
            elif service_name.lower() == "claude":
                # Claudeのログイン状態確認
                chat_input = await page.query_selector('div[contenteditable="true"]')
                return chat_input is not None
                
            elif service_name.lower() == "gemini":
                # Geminiのログイン状態確認
                chat_input = await page.query_selector('rich-textarea textarea')
                return chat_input is not None
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to check login status: {e}")
            return False
    
    async def wait_for_manual_login(self, page: Page, service_name: str, timeout: int = 300) -> bool:
        """手動ログインを待機"""
        logger.info(f"⏳ {service_name}への手動ログインを待機中... (最大{timeout}秒)")
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if await self.ensure_logged_in(page, service_name):
                logger.info(f"✅ {service_name}ログイン完了を確認")
                return True
            
            await asyncio.sleep(2)
            
            # 進捗表示
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            if elapsed % 10 == 0:
                logger.info(f"⏳ ログイン待機中... ({elapsed}/{timeout}秒)")
        
        logger.error(f"❌ {service_name}ログインタイムアウト")
        return False
    
    async def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            if self.is_cdp_connection:
                # CDP接続の場合はブラウザを閉じない
                logger.info("CDP connection - keeping browser open")
                
                # Playwrightのみ停止
                if self.playwright:
                    await self.playwright.stop()
            else:
                # 通常起動の場合は全てクリーンアップ
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
                
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        return {
            'browser_active': self.browser is not None,
            'context_active': self.context is not None,
            'pages': list(self.pages.keys()),
            'profile_name': self.profile_name,
            'cdp_port': self.cdp_port,
            'is_cdp_connection': self.is_cdp_connection,
            'user_data_dir': self.user_data_dir
        }
    
    def show_manual_instructions(self):
        """手動起動の手順を表示"""
        instructions = f"""
        ===== Chrome手動起動手順 =====
        
        1. ターミナルで以下のコマンドを実行:
           {self.chrome_path} --remote-debugging-port={self.cdp_port}
        
        2. Chromeが起動したら:
           - ChatGPT (https://chat.openai.com) にアクセスしてログイン
           - Claude (https://claude.ai) にアクセスしてログイン
           - その他必要なAIサービスにログイン
        
        3. ログインが完了したら、このスクリプトを実行
        
        ===========================
        """
        print(instructions)
        return instructions