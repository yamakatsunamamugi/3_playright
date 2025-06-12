"""Gemini自動操作ツール"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from .base import AIToolBase
from .browser_manager import BrowserManager


class GeminiTool(AIToolBase):
    """Gemini自動操作クラス
    
    Google Geminiウェブサイトでの自動操作を行う。
    - 既存のChromeプロファイルでログイン済みを前提
    - モデル選択
    - プロンプト送信と応答取得
    - ストリーミング応答の完了待機
    """
    
    URL = "https://gemini.google.com"
    
    def __init__(self, browser_manager: BrowserManager):
        """初期化
        
        Args:
            browser_manager (BrowserManager): ブラウザマネージャーインスタンス
        """
        super().__init__("Gemini")
        self.browser_manager = browser_manager
        
        # Gemini固有のセレクター
        self.selectors = {
            'input': 'div[contenteditable="true"]',  # メイン入力欄
            'send_button': 'button[aria-label="Send message"]',  # 送信ボタン
            'response_container': 'div[data-test-id="conversation-turn"]',  # 応答コンテナ
            'response_text': '.markdown',  # 応答テキスト
            'model_selector': 'button[data-test-id="model-selector"]',  # モデル選択ボタン
            'model_dropdown': 'div[role="listbox"]',  # モデル選択メニュー
            'model_option': 'div[role="option"]',  # モデル選択オプション
            'stop_button': 'button[aria-label="Stop generating"]',  # 停止ボタン
            'new_chat_button': 'button[aria-label="New chat"]',  # 新しいチャットボタン
            'loading_indicator': 'div[data-test-id="loading"]',  # ローディング表示
            'error_message': 'div[data-test-id="error"]',  # エラー表示
            'thinking_dots': '.thinking-animation',  # 思考中のアニメーション
        }
        
        # 利用可能なモデル（Gemini Pro、Gemini Advanced等）
        self.available_models = [
            "Gemini Advanced",
            "Gemini Pro",
            "Gemini 1.5 Pro",
            "Gemini 1.5 Flash",
            "Gemini Ultra"
        ]
        
        # 利用可能な設定
        self.available_settings = {
            "response_length": {"type": "select", "options": ["Short", "Medium", "Long"], "default": "Medium"},
            "creativity": {"type": "select", "options": ["Conservative", "Balanced", "Creative"], "default": "Balanced"},
            "safety_settings": {"type": "select", "options": ["Default", "Relaxed"], "default": "Default"}
        }

    async def login(self) -> bool:
        """ログイン処理
        
        既存のChromeプロファイルでログイン済みを前提とする
        
        Returns:
            bool: ログイン成功時True
        """
        try:
            # ページを作成してGeminiにアクセス
            self.page = await self.browser_manager.create_page("gemini", self.URL)
            if not self.page:
                self.logger.error("Geminiページの作成に失敗")
                return False
            
            # ページ読み込み完了を待機
            await asyncio.sleep(3)
            
            # ログイン状態の確認
            # 入力欄が表示されていればログイン済みと判断
            if await self.wait_for_element(self.selectors['input'], timeout=10):
                self.is_logged_in = True
                self.logger.info("Geminiログイン確認完了")
                return True
            else:
                # Googleアカウントでのログインボタンを探す
                login_selectors = [
                    'button:has-text("Sign in")',
                    'a:has-text("Sign in")',
                    'button[data-test-id="sign-in"]'
                ]
                
                for selector in login_selectors:
                    login_button = await self.page.query_selector(selector)
                    if login_button:
                        self.logger.error("Geminiログインが必要です。手動でログインしてください。")
                        return False
                
                self.logger.error("Gemini入力欄またはログインボタンが見つかりません")
                return False
                
        except Exception as e:
            self.logger.error(f"Geminiログインエラー: {e}")
            return False

    async def get_available_models(self) -> List[str]:
        """利用可能なモデルを取得
        
        Returns:
            List[str]: 利用可能なモデル名リスト
        """
        try:
            # モデルセレクターが存在するかチェック
            if not await self.wait_for_element(self.selectors['model_selector'], timeout=5):
                self.logger.warning("モデルセレクターが見つかりません")
                return self.available_models
            
            await self.page.click(self.selectors['model_selector'])
            await asyncio.sleep(1)
            
            # モデル選択メニューの表示を待機
            if await self.wait_for_element(self.selectors['model_dropdown']):
                # 利用可能なモデルを取得
                model_elements = await self.page.query_selector_all(self.selectors['model_option'])
                models = []
                for element in model_elements:
                    text = await element.text_content()
                    if text and text.strip():
                        models.append(text.strip())
                
                # メニューを閉じる（ESCキー）
                await self.page.keyboard.press('Escape')
                
                if models:
                    self.available_models = models
                    self.logger.info(f"利用可能なモデル: {models}")
                
            return self.available_models
            
        except Exception as e:
            self.logger.error(f"モデル取得エラー: {e}")
            return self.available_models

    async def select_model(self, model_name: str) -> bool:
        """モデル選択
        
        Args:
            model_name (str): 選択するモデル名
            
        Returns:
            bool: 選択成功時True
        """
        try:
            # モデルセレクターをクリック
            if not await self.wait_for_element(self.selectors['model_selector'], timeout=5):
                self.logger.warning("モデルセレクターが見つかりません（デフォルトモデルを使用）")
                return True
            
            await self.page.click(self.selectors['model_selector'])
            await asyncio.sleep(1)
            
            # モデル選択メニューの表示を待機
            if not await self.wait_for_element(self.selectors['model_dropdown']):
                self.logger.error("モデル選択メニューが表示されません")
                return False
            
            # 指定されたモデルを選択
            model_elements = await self.page.query_selector_all(self.selectors['model_option'])
            for element in model_elements:
                text = await element.text_content()
                if text and model_name in text:
                    await element.click()
                    self.current_model = model_name
                    self.logger.info(f"モデル選択完了: {model_name}")
                    await asyncio.sleep(1)
                    return True
            
            # 見つからない場合はメニューを閉じる
            await self.page.keyboard.press('Escape')
            self.logger.error(f"指定されたモデルが見つかりません: {model_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"モデル選択エラー: {e}")
            return False

    async def get_available_settings(self) -> Dict[str, Any]:
        """利用可能な設定を取得
        
        Returns:
            Dict[str, Any]: 利用可能な設定とその選択肢
        """
        return self.available_settings

    async def apply_settings(self, settings: Dict[str, Any]) -> bool:
        """設定を適用
        
        Args:
            settings (Dict[str, Any]): 適用する設定
            
        Returns:
            bool: 適用成功時True
        """
        try:
            # モデル選択
            if "model" in settings:
                await self.select_model(settings["model"])
            
            # 設定ボタンがある場合の処理（将来的な拡張用）
            if "response_length" in settings or "creativity" in settings:
                # Gemini設定画面への遷移（実装予定）
                pass
            
            self.logger.info("設定適用完了")
            return True
            
        except Exception as e:
            self.logger.error(f"設定適用エラー: {e}")
            return False

    async def send_prompt(self, text: str) -> str:
        """プロンプト送信と応答取得
        
        Args:
            text (str): 送信するプロンプトテキスト
            
        Returns:
            str: AIからの応答テキスト
        """
        try:
            # 入力欄が利用可能になるまで待機
            if not await self.wait_for_element(self.selectors['input']):
                self.logger.error("入力欄が見つかりません")
                return ""
            
            # 入力欄をクリックしてフォーカス
            await self.page.click(self.selectors['input'])
            await asyncio.sleep(0.5)
            
            # 既存のテキストをクリア
            await self.page.keyboard.press('Control+a')
            await self.page.keyboard.press('Delete')
            
            # テキストを入力
            await self.page.type(self.selectors['input'], text)
            await asyncio.sleep(0.5)
            
            # 送信ボタンをクリック
            send_button = await self.page.query_selector(self.selectors['send_button'])
            if send_button:
                await send_button.click()
            else:
                # Enterキーで送信
                await self.page.keyboard.press('Enter')
            
            self.logger.info("プロンプト送信完了")
            
            # 応答完了を待機
            if await self.wait_for_response_complete():
                # 応答テキストを取得
                return await self.get_response_text()
            else:
                self.logger.error("応答完了の待機がタイムアウト")
                return ""
                
        except Exception as e:
            self.logger.error(f"プロンプト送信エラー: {e}")
            return ""

    async def wait_for_response_complete(self, timeout: int = 120) -> bool:
        """応答完了の待機
        
        Args:
            timeout (int): タイムアウト時間（秒）
            
        Returns:
            bool: 応答完了時True
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # 停止ボタンの存在を確認（生成中）
                stop_button = await self.page.query_selector(self.selectors['stop_button'])
                if stop_button:
                    # まだ生成中
                    await asyncio.sleep(1)
                    continue
                
                # 思考中のアニメーションを確認
                thinking_dots = await self.page.query_selector(self.selectors['thinking_dots'])
                if thinking_dots:
                    # まだ思考中
                    await asyncio.sleep(1)
                    continue
                
                # ローディングインジケーターの確認
                loading = await self.page.query_selector(self.selectors['loading_indicator'])
                if loading:
                    # まだ読み込み中
                    await asyncio.sleep(1)
                    continue
                
                # 入力欄が再び使用可能かどうかを確認
                input_element = await self.page.query_selector(self.selectors['input'])
                if input_element:
                    is_disabled = await input_element.get_attribute('aria-disabled')
                    if is_disabled != 'true':
                        # 入力欄が使用可能なら応答完了
                        self.logger.info("Gemini応答完了")
                        return True
                
                await asyncio.sleep(1)
            
            self.logger.error("応答完了の待機がタイムアウト")
            return False
            
        except Exception as e:
            self.logger.error(f"応答完了待機エラー: {e}")
            return False

    async def get_response_text(self) -> str:
        """最新の応答テキストを取得
        
        Returns:
            str: 応答テキスト
        """
        try:
            # 少し待機してから応答を取得
            await asyncio.sleep(1)
            
            # 複数のセレクターを試行
            response_selectors = [
                self.selectors['response_container'],
                'message-content',
                '.conversation-turn',
                '[data-test-id="response"]'
            ]
            
            response_elements = []
            for selector in response_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    response_elements = elements
                    break
            
            if not response_elements:
                self.logger.error("応答コンテナが見つかりません")
                return ""
            
            # 最後の応答を取得（Gemini側の応答）
            for element in reversed(response_elements):
                # Gemini側の応答かどうかを確認
                role_indicator = await element.query_selector('[data-test-id="role"]')
                if role_indicator:
                    role_text = await role_indicator.text_content()
                    if "Gemini" in role_text or "Assistant" in role_text:
                        # テキスト内容を取得
                        text_element = await element.query_selector(self.selectors['response_text'])
                        if text_element:
                            response_text = await text_element.inner_text()
                            self.logger.info("応答テキスト取得完了")
                            return response_text.strip()
                        else:
                            # フォールバック: 全体のテキストを取得
                            response_text = await element.inner_text()
                            return response_text.strip()
            
            # フォールバック: 最後の応答を取得
            last_response = response_elements[-1]
            response_text = await last_response.inner_text()
            return response_text.strip()
                
        except Exception as e:
            self.logger.error(f"応答テキスト取得エラー: {e}")
            return ""

    async def clear_conversation(self) -> bool:
        """会話をクリア（新しいチャットを開始）
        
        Returns:
            bool: 成功時True
        """
        try:
            # 新しいチャットボタンを探してクリック
            new_chat_selectors = [
                self.selectors['new_chat_button'],
                'button[aria-label="New conversation"]',
                'button:has-text("New chat")',
                'a[href="/app"]'
            ]
            
            for selector in new_chat_selectors:
                button = await self.page.query_selector(selector)
                if button:
                    await button.click()
                    await asyncio.sleep(2)
                    self.logger.info("会話クリア完了")
                    return True
            
            self.logger.warning("新しいチャットボタンが見つかりません")
            return False
            
        except Exception as e:
            self.logger.error(f"会話クリアエラー: {e}")
            return False