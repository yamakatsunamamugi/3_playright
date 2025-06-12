"""
シンプルなブラウザマネージャー（Cloudflare回避機能付き）
"""

import os
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)


class SimpleBrowserManager:
    """シンプルなブラウザマネージャー"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: Dict[str, Page] = {}
        
    async def initialize(self) -> bool:
        """ブラウザを初期化"""
        try:
            self.playwright = await async_playwright().start()
            
            # Chromeを起動（最小限のオプション）
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                channel="chrome",  # 実際のChromeを使用
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox'
                ]
            )
            
            # コンテキストを作成
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ja-JP',
                timezone_id='Asia/Tokyo'
            )
            
            # 基本的なbot検出回避
            await self.context.add_init_script("""
                // webdriverを隠す
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Chromeを偽装
                window.chrome = {
                    runtime: {},
                };
            """)
            
            logger.info("SimpleBrowserManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    async def create_page(self, name: str, url: Optional[str] = None) -> Optional[Page]:
        """ページを作成"""
        try:
            if not self.context:
                logger.error("Browser context not initialized")
                return None
                
            page = await self.context.new_page()
            self.pages[name] = page
            
            if url:
                logger.info(f"Navigating to {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                logger.info(f"Successfully loaded {url}")
                
            return page
            
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            return None
    
    async def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            for page in self.pages.values():
                await page.close()
                
            if self.context:
                await self.context.close()
                
            if self.browser:
                await self.browser.close()
                
            if self.playwright:
                await self.playwright.stop()
                
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")