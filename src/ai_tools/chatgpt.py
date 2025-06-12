"""ChatGPT自動操作ツール"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from .base import AIToolBase
from .browser_manager import BrowserManager


class ChatGPTTool(AIToolBase):
    """ChatGPT自動操作クラス
    
    ChatGPTウェブサイトでの自動操作を行う。
    - 既存のChromeプロファイルでログイン済みを前提
    - モデル選択
    - プロンプト送信と応答取得
    - ストリーミング応答の完了待機
    """
    
    URL = "https://chat.openai.com"
    
    def __init__(self, browser_manager: BrowserManager):
        """初期化
        
        Args:
            browser_manager (BrowserManager): ブラウザマネージャーインスタンス
        """
        super().__init__("ChatGPT")
        self.browser_manager = browser_manager
        
        # ChatGPT固有のセレクター
        self.selectors = {
            'input': 'textarea[data-testid="textbox"]',  # メイン入力欄
            'send_button': 'button[data-testid="send-button"]',  # 送信ボタン
            'response_container': 'div[data-message-author-role="assistant"]',  # 応答コンテナ
            'response_text': 'div[data-message-author-role="assistant"] .markdown',  # 応答テキスト
            'model_selector': 'button[data-testid="model-switcher-button"]',  # モデル選択ボタン
            'model_dropdown': 'div[role="menu"]',  # モデル選択メニュー
            'model_option': 'div[role="menuitem"]',  # モデル選択オプション
            'stop_button': 'button[data-testid="stop-button"]',  # 停止ボタン
            'regenerate_button': 'button[data-testid="regenerate-button"]',  # 再生成ボタン
            'loading_indicator': 'div[data-testid="loading"]',  # ローディング表示
            'error_message': 'div[data-testid="error-message"]',  # エラー表示
        }
        
        # 利用可能なモデル（定期的に更新される可能性がある）
        self.available_models = [
            "GPT-4o",
            "GPT-4o mini", 
            "GPT-4",
            "GPT-3.5 Turbo"
        ]
        
        # 利用可能な設定
        self.available_settings = {
            "temperature": {"type": "slider", "min": 0, "max": 2, "default": 1},
            "max_tokens": {"type": "number", "min": 1, "max": 4096, "default": 2048},
            "custom_instructions": {"type": "text", "default": ""}
        }

    async def login(self) -> bool:
        """ログイン処理
        
        既存のChromeプロファイルでログイン済みを前提とする
        
        Returns:
            bool: ログイン成功時True
        """
        try:
            # ページを作成してChatGPTにアクセス
            self.page = await self.browser_manager.create_page("chatgpt", self.URL)
            if not self.page:
                self.logger.error("ChatGPTページの作成に失敗")
                return False
            
            # ページ読み込み完了を待機
            await asyncio.sleep(3)
            
            # ログイン状態の確認
            # 入力欄が表示されていればログイン済みと判断
            if await self.wait_for_element(self.selectors['input'], timeout=10):
                self.is_logged_in = True
                self.logger.info("ChatGPTログイン確認完了")
                return True
            else:
                self.logger.error("ChatGPTログインが必要です。手動でログインしてください。")
                return False
                
        except Exception as e:
            self.logger.error(f"ChatGPTログインエラー: {e}")
            return False

    async def get_available_models(self) -> List[str]:
        """利用可能なモデルを取得
        
        Returns:
            List[str]: 利用可能なモデル名リスト
        """
        try:
            # モデルセレクターをクリック
            if not await self.wait_for_element(self.selectors['model_selector']):
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
            if not await self.wait_for_element(self.selectors['model_selector']):
                self.logger.error("モデルセレクターが見つかりません")
                return False
            
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
        # ChatGPTではWebUI上で設定できる項目が限られているため、
        # 基本的な設定のみを返す
        return self.available_settings

    async def apply_settings(self, settings: Dict[str, Any]) -> bool:
        """設定を適用
        
        Args:
            settings (Dict[str, Any]): 適用する設定
            
        Returns:
            bool: 適用成功時True
        """
        try:
            # ChatGPTのWebUIでは設定項目が限られているため、
            # 基本的にはモデル選択のみ対応
            if "model" in settings:
                return await self.select_model(settings["model"])
            
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
            
            # 既存のテキストをクリア
            await self.page.click(self.selectors['input'])
            await self.page.keyboard.press('Control+a')
            await self.page.keyboard.press('Delete')
            
            # テキストを入力
            await self.page.fill(self.selectors['input'], text)
            await asyncio.sleep(0.5)
            
            # 送信ボタンをクリック
            if await self.wait_for_element(self.selectors['send_button']):
                await self.page.click(self.selectors['send_button'])
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
                
                # 再生成ボタンの存在を確認（生成完了）
                regenerate_button = await self.page.query_selector(self.selectors['regenerate_button'])
                if regenerate_button:
                    # 生成完了
                    self.logger.info("ChatGPT応答完了")
                    return True
                
                # 入力欄が再び使用可能かどうかを確認
                input_element = await self.page.query_selector(self.selectors['input'])
                if input_element:
                    is_disabled = await input_element.get_attribute('disabled')
                    if not is_disabled:
                        # 入力欄が使用可能なら応答完了
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
            # 最新の応答コンテナを取得
            response_elements = await self.page.query_selector_all(self.selectors['response_container'])
            if not response_elements:
                self.logger.error("応答コンテナが見つかりません")
                return ""
            
            # 最後の応答を取得
            last_response = response_elements[-1]
            
            # テキスト内容を取得
            text_element = await last_response.query_selector('.markdown')
            if text_element:
                response_text = await text_element.inner_text()
                self.logger.info("応答テキスト取得完了")
                return response_text.strip()
            else:
                # フォールバック: 全体のテキストを取得
                response_text = await last_response.inner_text()
                return response_text.strip()
                
        except Exception as e:
            self.logger.error(f"応答テキスト取得エラー: {e}")
            return ""

    async def clear_conversation(self) -> bool:
        """会話をクリア（新しい会話を開始）
        
        Returns:
            bool: 成功時True
        """
        try:
            # 新しい会話ボタンを探してクリック
            new_chat_selectors = [
                'button[data-testid="new-chat"]',
                'a[href="/"]',
                'button:has-text("New chat")'
            ]
            
            for selector in new_chat_selectors:
                button = await self.page.query_selector(selector)
                if button:
                    await button.click()
                    await asyncio.sleep(2)
                    self.logger.info("会話クリア完了")
                    return True
            
            self.logger.warning("新しい会話ボタンが見つかりません")
            return False
            
        except Exception as e:
            self.logger.error(f"会話クリアエラー: {e}")
            return False