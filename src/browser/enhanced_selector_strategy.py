"""拡張セレクター戦略 - より安定したUI要素の検出"""

import logging
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, ElementHandle
import asyncio

logger = logging.getLogger(__name__)


class EnhancedSelectorStrategy:
    """アクセシビリティベースの安定したセレクター戦略
    
    UIの変更に強い、複数のフォールバック戦略を持つセレクター実装
    """
    
    def __init__(self):
        # 各AIツール用のセレクター定義
        self.selector_definitions = {
            'chatgpt': {
                'input': [
                    'role=textbox[name*="Send a message"]',
                    'textarea[data-testid="textbox"]',
                    'textarea[placeholder*="Send a message"]',
                    'div[contenteditable="true"][data-placeholder*="Send"]',
                    'textarea#prompt-textarea'
                ],
                'send_button': [
                    'button[data-testid="send-button"]',
                    'button[aria-label*="Send message"]',
                    'button:has-text("Send")',
                    'svg[aria-label="Send"] >> xpath=ancestor::button'
                ],
                'response_container': [
                    'div[data-message-author-role="assistant"]',
                    'div.agent-turn',
                    'div[class*="message"][class*="assistant"]'
                ],
                'model_selector': [
                    'button[data-testid="model-switcher-button"]',
                    'button:has-text("GPT-")',
                    'div[role="button"]:has-text("Model:")'
                ],
                'stop_button': [
                    'button[data-testid="stop-button"]',
                    'button[aria-label="Stop generating"]',
                    'button:has-text("Stop")'
                ]
            },
            'claude': {
                'input': [
                    'div[contenteditable="true"][placeholder*="Talk to Claude"]',
                    'textarea[placeholder*="Start a conversation"]',
                    'div.ProseMirror[contenteditable="true"]',
                    'div[role="textbox"]'
                ],
                'send_button': [
                    'button[aria-label="Send Message"]',
                    'button:has(svg[class*="send"])',
                    'button[type="submit"]:visible'
                ],
                'response_container': [
                    'div[data-test-render-type="message"]',
                    'div.message-content',
                    'div[class*="assistant-message"]'
                ],
                'model_selector': [
                    'button[aria-label*="Model"]',
                    'button:has-text("Claude")',
                    'div[role="button"]:has-text("Model")'
                ]
            },
            'gemini': {
                'input': [
                    'div[contenteditable="true"][aria-label*="prompt"]',
                    'textarea[placeholder*="Enter a prompt"]',
                    'div.ql-editor[contenteditable="true"]',
                    'rich-textarea[label*="prompt"]'
                ],
                'send_button': [
                    'button[aria-label*="Send"]',
                    'button[mattooltip*="Send"]',
                    'button:has(mat-icon:has-text("send"))'
                ],
                'response_container': [
                    'model-response',
                    'div[class*="model-response"]',
                    'message-content[participant="MODEL"]'
                ],
                'model_selector': [
                    'button:has-text("Gemini")',
                    'mat-select[aria-label*="model"]',
                    'button[aria-label*="Select model"]'
                ]
            }
        }
        
        # 汎用セレクター（すべてのサービスで試すフォールバック）
        self.generic_selectors = {
            'input': [
                'textarea:visible',
                'div[contenteditable="true"]:visible',
                'input[type="text"]:visible'
            ],
            'button': [
                'button:visible:not([disabled])',
                'div[role="button"]:visible'
            ]
        }
    
    async def find_element(
        self, 
        page: Page, 
        service: str, 
        element_type: str,
        timeout: int = 5000
    ) -> Optional[ElementHandle]:
        """要素を見つける（複数の戦略を試行）
        
        Args:
            page: Playwrightのページオブジェクト
            service: AIサービス名（chatgpt, claude, gemini等）
            element_type: 要素タイプ（input, send_button等）
            timeout: 各セレクターのタイムアウト（ミリ秒）
            
        Returns:
            見つかった要素、見つからない場合はNone
        """
        # サービス固有のセレクターを試す
        if service in self.selector_definitions:
            selectors = self.selector_definitions[service].get(element_type, [])
            
            for selector in selectors:
                try:
                    logger.debug(f"Trying selector for {service}.{element_type}: {selector}")
                    element = await page.wait_for_selector(
                        selector, 
                        timeout=timeout,
                        state='visible'
                    )
                    if element:
                        logger.info(f"Found element using selector: {selector}")
                        return element
                except Exception as e:
                    logger.debug(f"Selector failed: {selector}, error: {e}")
                    continue
        
        # 汎用セレクターを試す
        if element_type in self.generic_selectors:
            for selector in self.generic_selectors[element_type]:
                try:
                    logger.debug(f"Trying generic selector: {selector}")
                    element = await page.wait_for_selector(
                        selector,
                        timeout=timeout,
                        state='visible'
                    )
                    if element:
                        logger.info(f"Found element using generic selector: {selector}")
                        return element
                except Exception:
                    continue
        
        logger.warning(f"Could not find element: {service}.{element_type}")
        return None
    
    async def wait_for_any_selector(
        self,
        page: Page,
        selectors: List[str],
        timeout: int = 30000
    ) -> Optional[ElementHandle]:
        """複数のセレクターのいずれかが現れるまで待機
        
        Args:
            page: Playwrightのページオブジェクト
            selectors: セレクターのリスト
            timeout: 全体のタイムアウト（ミリ秒）
            
        Returns:
            最初に見つかった要素
        """
        tasks = []
        
        for selector in selectors:
            task = asyncio.create_task(
                self._wait_for_selector_with_result(page, selector, timeout)
            )
            tasks.append(task)
        
        # 最初に完了したタスクを待つ
        done, pending = await asyncio.wait(
            tasks, 
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 残りのタスクをキャンセル
        for task in pending:
            task.cancel()
        
        # 成功したタスクの結果を返す
        for task in done:
            result = await task
            if result:
                return result
        
        return None
    
    async def _wait_for_selector_with_result(
        self,
        page: Page,
        selector: str,
        timeout: int
    ) -> Optional[ElementHandle]:
        """セレクターを待機し、結果を返す（内部用）"""
        try:
            return await page.wait_for_selector(
                selector,
                timeout=timeout,
                state='visible'
            )
        except Exception:
            return None
    
    def get_interaction_strategies(self, service: str) -> Dict[str, Any]:
        """サービス固有のインタラクション戦略を取得
        
        Args:
            service: AIサービス名
            
        Returns:
            インタラクション戦略の辞書
        """
        strategies = {
            'chatgpt': {
                'input_method': 'fill',  # fill, type, or paste
                'clear_method': 'select_all_delete',  # select_all_delete or clear
                'send_method': 'button',  # button or enter
                'wait_after_send': 1000,  # ミリ秒
                'response_detection': 'stop_button_disappears'
            },
            'claude': {
                'input_method': 'type',
                'clear_method': 'select_all_delete',
                'send_method': 'button_or_enter',
                'wait_after_send': 500,
                'response_detection': 'new_message_appears'
            },
            'gemini': {
                'input_method': 'type',
                'clear_method': 'clear',
                'send_method': 'button',
                'wait_after_send': 1000,
                'response_detection': 'loading_indicator'
            }
        }
        
        return strategies.get(service, {
            'input_method': 'fill',
            'clear_method': 'select_all_delete',
            'send_method': 'button_or_enter',
            'wait_after_send': 1000,
            'response_detection': 'generic'
        })
    
    async def smart_fill(
        self,
        page: Page,
        element: ElementHandle,
        text: str,
        service: str
    ) -> bool:
        """サービスに応じた最適な方法でテキストを入力
        
        Args:
            page: Playwrightのページオブジェクト
            element: 入力要素
            text: 入力するテキスト
            service: AIサービス名
            
        Returns:
            成功した場合True
        """
        strategy = self.get_interaction_strategies(service)
        
        try:
            # 既存のテキストをクリア
            if strategy['clear_method'] == 'select_all_delete':
                await element.click()
                await page.keyboard.press('Control+A')
                await page.keyboard.press('Delete')
            else:
                await element.clear()
            
            # テキストを入力
            if strategy['input_method'] == 'fill':
                await element.fill(text)
            elif strategy['input_method'] == 'type':
                await element.type(text, delay=50)
            elif strategy['input_method'] == 'paste':
                await page.evaluate(f'''
                    navigator.clipboard.writeText(`{text}`)
                ''')
                await element.click()
                await page.keyboard.press('Control+V')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to input text: {e}")
            return False
    
    async def detect_response_complete(
        self,
        page: Page,
        service: str,
        timeout: int = 120000
    ) -> bool:
        """応答が完了したかを検出
        
        Args:
            page: Playwrightのページオブジェクト
            service: AIサービス名
            timeout: タイムアウト（ミリ秒）
            
        Returns:
            応答完了を検出した場合True
        """
        strategy = self.get_interaction_strategies(service)
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout:
            try:
                if strategy['response_detection'] == 'stop_button_disappears':
                    # 停止ボタンが消えるまで待つ
                    stop_button = await self.find_element(
                        page, service, 'stop_button', timeout=1000
                    )
                    if not stop_button:
                        return True
                        
                elif strategy['response_detection'] == 'new_message_appears':
                    # 新しいメッセージが完全に表示されるまで待つ
                    await asyncio.sleep(1)
                    # 入力欄が再び使用可能になったかチェック
                    input_element = await self.find_element(
                        page, service, 'input', timeout=1000
                    )
                    if input_element:
                        is_enabled = await input_element.is_enabled()
                        if is_enabled:
                            return True
                            
                elif strategy['response_detection'] == 'loading_indicator':
                    # ローディングインジケーターが消えるまで待つ
                    loading = await page.query_selector('.loading-indicator')
                    if not loading:
                        await asyncio.sleep(1)
                        return True
                        
                else:
                    # 汎用的な検出方法
                    await asyncio.sleep(2)
                    return True
                    
            except Exception as e:
                logger.debug(f"Response detection error: {e}")
            
            await asyncio.sleep(1)
        
        logger.warning("Response detection timed out")
        return False