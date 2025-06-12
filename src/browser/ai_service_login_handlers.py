"""
AIサービス別ログイン処理ハンドラー
最新のログイン手法とセッション管理を実装
"""

import logging
import asyncio
import random
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class BaseAILoginHandler(ABC):
    """
    AIサービスログインハンドラーの基底クラス
    """
    
    def __init__(self, page: Page, context: BrowserContext):
        self.page = page
        self.context = context
        self.service_name = self.__class__.__name__.replace('LoginHandler', '').lower()
        
    @abstractmethod
    async def login(self, credentials: Dict[str, str]) -> bool:
        """
        ログイン処理を実行
        
        Args:
            credentials: ログイン情報
            
        Returns:
            成功時True
        """
        pass
    
    @abstractmethod
    async def is_logged_in(self) -> bool:
        """
        ログイン状態を確認
        
        Returns:
            ログイン済みの場合True
        """
        pass
    
    async def wait_and_click(self, selector: str, timeout: int = 10000) -> bool:
        """
        要素の出現を待機してクリック
        
        Args:
            selector: セレクター
            timeout: タイムアウト（ミリ秒）
            
        Returns:
            成功時True
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.click(selector)
            await asyncio.sleep(random.uniform(0.5, 1.5))  # 人間らしい遅延
            return True
        except PlaywrightTimeoutError:
            logger.error(f"Element not found: {selector}")
            return False
        except Exception as e:
            logger.error(f"Error clicking element {selector}: {e}")
            return False
    
    async def wait_and_fill(self, selector: str, text: str, timeout: int = 10000) -> bool:
        """
        要素の出現を待機してテキスト入力
        
        Args:
            selector: セレクター
            text: 入力テキスト
            timeout: タイムアウト（ミリ秒）
            
        Returns:
            成功時True
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.fill(selector, text)
            await asyncio.sleep(random.uniform(0.3, 0.8))  # 人間らしい遅延
            return True
        except PlaywrightTimeoutError:
            logger.error(f"Element not found: {selector}")
            return False
        except Exception as e:
            logger.error(f"Error filling element {selector}: {e}")
            return False
    
    async def human_type(self, selector: str, text: str, delay_range: tuple = (50, 150)) -> bool:
        """
        人間らしいタイピングでテキスト入力
        
        Args:
            selector: セレクター
            text: 入力テキスト
            delay_range: キー入力間の遅延範囲（ミリ秒）
            
        Returns:
            成功時True
        """
        try:
            await self.page.wait_for_selector(selector)
            element = await self.page.query_selector(selector)
            
            if not element:
                return False
            
            await element.click()
            await element.fill('')  # クリア
            
            for char in text:
                await element.type(char, delay=random.randint(*delay_range))
            
            return True
        except Exception as e:
            logger.error(f"Error typing in element {selector}: {e}")
            return False
    
    async def wait_for_navigation_or_element(
        self, 
        selectors: List[str], 
        timeout: int = 30000
    ) -> Optional[str]:
        """
        ナビゲーションまたは特定の要素の出現を待機
        
        Args:
            selectors: 待機するセレクターのリスト
            timeout: タイムアウト（ミリ秒）
            
        Returns:
            見つかったセレクター（見つからない場合None）
        """
        try:
            for selector in selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=timeout // len(selectors))
                    return selector
                except PlaywrightTimeoutError:
                    continue
            return None
        except Exception as e:
            logger.error(f"Error waiting for elements: {e}")
            return None


class ChatGPTLoginHandler(BaseAILoginHandler):
    """
    ChatGPTログイン処理ハンドラー
    """
    
    LOGIN_URL = "https://chat.openai.com/auth/login"
    LOGGED_IN_INDICATORS = [
        'div[data-testid="conversation-turn"]',
        'textarea[placeholder*="Message"]',
        'button[data-testid="send-button"]',
        'div[class*="text-center"] button'
    ]
    
    async def login(self, credentials: Dict[str, str]) -> bool:
        """
        ChatGPTログイン処理
        
        Args:
            credentials: {'email': str, 'password': str} または {'use_google': True}
            
        Returns:
            成功時True
        """
        try:
            logger.info("Starting ChatGPT login process")
            
            # ログインページに移動
            await self.page.goto(self.LOGIN_URL, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # 既にログイン済みかチェック
            if await self.is_logged_in():
                logger.info("Already logged in to ChatGPT")
                return True
            
            # Google認証を使用する場合
            if credentials.get('use_google', False):
                return await self._login_with_google()
            
            # Email/Password認証
            email = credentials.get('email')
            password = credentials.get('password')
            
            if not email or not password:
                logger.error("Email and password are required for ChatGPT login")
                return False
            
            return await self._login_with_email_password(email, password)
            
        except Exception as e:
            logger.error(f"ChatGPT login failed: {e}")
            return False
    
    async def _login_with_google(self) -> bool:
        """
        Google認証でログイン
        """
        try:
            # Googleログインボタンを探してクリック
            google_selectors = [
                'button[data-provider="google"]',
                'button:has-text("Continue with Google")',
                'a:has-text("Continue with Google")',
                'div:has-text("Continue with Google")'
            ]
            
            google_button_found = False
            for selector in google_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.click(selector)
                    google_button_found = True
                    break
                except PlaywrightTimeoutError:
                    continue
            
            if not google_button_found:
                logger.error("Google login button not found")
                return False
            
            # Googleアカウント選択画面で既存のアカウントを選択
            await asyncio.sleep(3)
            
            # 既存のアカウントがある場合は選択
            account_selectors = [
                'div[data-identifier]',
                'div[class*="BHzsHc"]',  # Google account selection
                'li[data-value]'
            ]
            
            for selector in account_selectors:
                try:
                    accounts = await self.page.query_selector_all(selector)
                    if accounts:
                        await accounts[0].click()  # 最初のアカウントを選択
                        break
                except:
                    continue
            
            # ログイン完了を待機
            return await self._wait_for_login_completion()
            
        except Exception as e:
            logger.error(f"Google login failed: {e}")
            return False
    
    async def _login_with_email_password(self, email: str, password: str) -> bool:
        """
        Email/Passwordでログイン
        """
        try:
            # Email入力
            email_selectors = [
                'input[name="email"]',
                'input[type="email"]',
                'input[id="email"]',
                'input[placeholder*="email"]'
            ]
            
            email_filled = False
            for selector in email_selectors:
                if await self.wait_and_fill(selector, email):
                    email_filled = True
                    break
            
            if not email_filled:
                logger.error("Could not find email input field")
                return False
            
            # Continue/Nextボタンをクリック
            continue_selectors = [
                'button[type="submit"]',
                'button:has-text("Continue")',
                'button:has-text("Next")',
                'input[type="submit"]'
            ]
            
            for selector in continue_selectors:
                if await self.wait_and_click(selector):
                    break
            
            await asyncio.sleep(2)
            
            # Password入力
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[id="password"]'
            ]
            
            password_filled = False
            for selector in password_selectors:
                if await self.wait_and_fill(selector, password):
                    password_filled = True
                    break
            
            if not password_filled:
                logger.error("Could not find password input field")
                return False
            
            # ログインボタンをクリック
            login_selectors = [
                'button[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                'input[type="submit"]'
            ]
            
            for selector in login_selectors:
                if await self.wait_and_click(selector):
                    break
            
            # ログイン完了を待機
            return await self._wait_for_login_completion()
            
        except Exception as e:
            logger.error(f"Email/Password login failed: {e}")
            return False
    
    async def _wait_for_login_completion(self, timeout: int = 30000) -> bool:
        """
        ログイン完了を待機
        """
        try:
            # 2FA確認
            twofa_selectors = [
                'input[placeholder*="code"]',
                'input[name*="code"]',
                'div:has-text("verification code")'
            ]
            
            for selector in twofa_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    logger.warning("2FA required - manual intervention needed")
                    # 2FAが必要な場合は手動介入を待つ
                    await asyncio.sleep(60)  # 1分待機
                    break
                except PlaywrightTimeoutError:
                    continue
            
            # ログイン完了インジケーターを待機
            found_selector = await self.wait_for_navigation_or_element(
                self.LOGGED_IN_INDICATORS, timeout
            )
            
            if found_selector:
                logger.info("ChatGPT login completed successfully")
                return True
            else:
                logger.error("Login completion indicators not found")
                return False
                
        except Exception as e:
            logger.error(f"Error waiting for login completion: {e}")
            return False
    
    async def is_logged_in(self) -> bool:
        """
        ChatGPTログイン状態を確認
        """
        try:
            # ログイン状態を示すページ要素をチェック
            for selector in self.LOGGED_IN_INDICATORS:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    return True
                except PlaywrightTimeoutError:
                    continue
            
            # URLでも確認
            current_url = self.page.url
            if '/auth/' not in current_url and 'chat.openai.com' in current_url:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking ChatGPT login status: {e}")
            return False


class ClaudeLoginHandler(BaseAILoginHandler):
    """
    Claudeログイン処理ハンドラー
    """
    
    LOGIN_URL = "https://claude.ai/login"
    LOGGED_IN_INDICATORS = [
        'div[data-testid="chat-input"]',
        'textarea[placeholder*="Talk"]',
        'button[aria-label*="Send"]',
        'div[class*="font-user-message"]'
    ]
    
    async def login(self, credentials: Dict[str, str]) -> bool:
        """
        Claudeログイン処理
        
        Args:
            credentials: {'email': str} または {'use_google': True}
            
        Returns:
            成功時True
        """
        try:
            logger.info("Starting Claude login process")
            
            # ログインページに移動
            await self.page.goto(self.LOGIN_URL, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # 既にログイン済みかチェック
            if await self.is_logged_in():
                logger.info("Already logged in to Claude")
                return True
            
            # Google認証を使用する場合
            if credentials.get('use_google', False):
                return await self._login_with_google()
            
            # Email認証
            email = credentials.get('email')
            if not email:
                logger.error("Email is required for Claude login")
                return False
            
            return await self._login_with_email(email)
            
        except Exception as e:
            logger.error(f"Claude login failed: {e}")
            return False
    
    async def _login_with_google(self) -> bool:
        """
        Google認証でログイン
        """
        try:
            # Googleログインボタンを探してクリック
            google_selectors = [
                'button:has-text("Continue with Google")',
                'a:has-text("Continue with Google")',
                'button[data-provider="google"]',
                'div:has-text("Continue with Google")'
            ]
            
            for selector in google_selectors:
                if await self.wait_and_click(selector):
                    break
            else:
                logger.error("Google login button not found")
                return False
            
            # ログイン完了を待機
            return await self._wait_for_login_completion()
            
        except Exception as e:
            logger.error(f"Claude Google login failed: {e}")
            return False
    
    async def _login_with_email(self, email: str) -> bool:
        """
        Emailでログイン（Magic Link方式）
        """
        try:
            # Email入力
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="email"]'
            ]
            
            email_filled = False
            for selector in email_selectors:
                if await self.wait_and_fill(selector, email):
                    email_filled = True
                    break
            
            if not email_filled:
                logger.error("Could not find email input field")
                return False
            
            # Continue/Send Linkボタンをクリック
            continue_selectors = [
                'button[type="submit"]',
                'button:has-text("Continue")',
                'button:has-text("Send Link")',
                'button:has-text("Continue with Email")'
            ]
            
            for selector in continue_selectors:
                if await self.wait_and_click(selector):
                    break
            
            # Magic Linkの案内メッセージを確認
            await asyncio.sleep(3)
            
            # Emailリンクがクリックされるまで待機
            logger.info("Waiting for email verification link to be clicked...")
            
            # ログイン完了を待機（長めのタイムアウト）
            return await self._wait_for_login_completion(timeout=120000)  # 2分
            
        except Exception as e:
            logger.error(f"Claude email login failed: {e}")
            return False
    
    async def _wait_for_login_completion(self, timeout: int = 30000) -> bool:
        """
        ログイン完了を待機
        """
        try:
            found_selector = await self.wait_for_navigation_or_element(
                self.LOGGED_IN_INDICATORS, timeout
            )
            
            if found_selector:
                logger.info("Claude login completed successfully")
                return True
            else:
                logger.error("Claude login completion indicators not found")
                return False
                
        except Exception as e:
            logger.error(f"Error waiting for Claude login completion: {e}")
            return False
    
    async def is_logged_in(self) -> bool:
        """
        Claudeログイン状態を確認
        """
        try:
            # ログイン状態を示すページ要素をチェック
            for selector in self.LOGGED_IN_INDICATORS:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    return True
                except PlaywrightTimeoutError:
                    continue
            
            # URLでも確認
            current_url = self.page.url
            if '/login' not in current_url and 'claude.ai' in current_url:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking Claude login status: {e}")
            return False


class GeminiLoginHandler(BaseAILoginHandler):
    """
    Geminiログイン処理ハンドラー
    """
    
    LOGIN_URL = "https://gemini.google.com/"
    LOGGED_IN_INDICATORS = [
        'textarea[placeholder*="Enter a prompt"]',
        'div[data-test-id="input-area"]',
        'button[aria-label*="Send"]',
        'div[class*="conversation"]'
    ]
    
    async def login(self, credentials: Dict[str, str]) -> bool:
        """
        Geminiログイン処理（Googleアカウント必須）
        
        Args:
            credentials: {'google_account': str} または空のdict
            
        Returns:
            成功時True
        """
        try:
            logger.info("Starting Gemini login process")
            
            # Geminiページに移動
            await self.page.goto(self.LOGIN_URL, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # 既にログイン済みかチェック
            if await self.is_logged_in():
                logger.info("Already logged in to Gemini")
                return True
            
            # Googleアカウントでログイン
            return await self._login_with_google_account(credentials.get('google_account'))
            
        except Exception as e:
            logger.error(f"Gemini login failed: {e}")
            return False
    
    async def _login_with_google_account(self, google_account: Optional[str] = None) -> bool:
        """
        Googleアカウントでログイン
        """
        try:
            # Sign Inボタンをクリック
            signin_selectors = [
                'button:has-text("Sign in")',
                'a:has-text("Sign in")',
                'button[data-testid="sign-in"]',
                'div:has-text("Sign in")'
            ]
            
            for selector in signin_selectors:
                if await self.wait_and_click(selector):
                    break
            
            await asyncio.sleep(3)
            
            # アカウント選択画面で特定のアカウントを選択
            if google_account:
                account_selectors = [
                    f'div[data-email="{google_account}"]',
                    f'div:has-text("{google_account}")',
                    f'span:has-text("{google_account}")'
                ]
                
                for selector in account_selectors:
                    if await self.wait_and_click(selector):
                        break
            else:
                # 最初に見つかったアカウントを選択
                account_selectors = [
                    'div[data-identifier]',
                    'div[class*="BHzsHc"]',
                    'li[data-value]'
                ]
                
                for selector in account_selectors:
                    try:
                        accounts = await self.page.query_selector_all(selector)
                        if accounts:
                            await accounts[0].click()
                            break
                    except:
                        continue
            
            # ログイン完了を待機
            return await self._wait_for_login_completion()
            
        except Exception as e:
            logger.error(f"Gemini Google login failed: {e}")
            return False
    
    async def _wait_for_login_completion(self, timeout: int = 30000) -> bool:
        """
        ログイン完了を待機
        """
        try:
            found_selector = await self.wait_for_navigation_or_element(
                self.LOGGED_IN_INDICATORS, timeout
            )
            
            if found_selector:
                logger.info("Gemini login completed successfully")
                return True
            else:
                logger.error("Gemini login completion indicators not found")
                return False
                
        except Exception as e:
            logger.error(f"Error waiting for Gemini login completion: {e}")
            return False
    
    async def is_logged_in(self) -> bool:
        """
        Geminiログイン状態を確認
        """
        try:
            # ログイン状態を示すページ要素をチェック
            for selector in self.LOGGED_IN_INDICATORS:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    return True
                except PlaywrightTimeoutError:
                    continue
            
            # Sign Inボタンがない場合はログイン済み
            try:
                await self.page.wait_for_selector('button:has-text("Sign in")', timeout=3000)
                return False  # Sign Inボタンがある = ログインしていない
            except PlaywrightTimeoutError:
                return True  # Sign Inボタンがない = ログイン済み
            
        except Exception as e:
            logger.error(f"Error checking Gemini login status: {e}")
            return False


class AIServiceLoginManager:
    """
    AIサービス統合ログイン管理クラス
    """
    
    def __init__(self):
        self.handlers = {
            'chatgpt': ChatGPTLoginHandler,
            'claude': ClaudeLoginHandler,
            'gemini': GeminiLoginHandler
        }
    
    def get_handler(self, service_name: str, page: Page, context: BrowserContext) -> Optional[BaseAILoginHandler]:
        """
        指定されたサービスのハンドラーを取得
        
        Args:
            service_name: サービス名
            page: ページオブジェクト
            context: コンテキストオブジェクト
            
        Returns:
            ハンドラーインスタンス
        """
        handler_class = self.handlers.get(service_name.lower())
        if handler_class:
            return handler_class(page, context)
        else:
            logger.error(f"Unsupported service: {service_name}")
            return None
    
    async def login_to_service(
        self,
        service_name: str,
        page: Page,
        context: BrowserContext,
        credentials: Dict[str, str]
    ) -> bool:
        """
        指定されたサービスにログイン
        
        Args:
            service_name: サービス名
            page: ページオブジェクト
            context: コンテキストオブジェクト
            credentials: ログイン情報
            
        Returns:
            成功時True
        """
        handler = self.get_handler(service_name, page, context)
        if handler:
            return await handler.login(credentials)
        return False
    
    async def check_login_status(
        self,
        service_name: str,
        page: Page,
        context: BrowserContext
    ) -> bool:
        """
        指定されたサービスのログイン状態を確認
        
        Args:
            service_name: サービス名
            page: ページオブジェクト
            context: コンテキストオブジェクト
            
        Returns:
            ログイン済みの場合True
        """
        handler = self.get_handler(service_name, page, context)
        if handler:
            return await handler.is_logged_in()
        return False