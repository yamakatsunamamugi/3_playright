"""Google AI Studio自動操作ツール"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from .base import AIToolBase
from .browser_manager import BrowserManager


class GoogleAIStudioTool(AIToolBase):
    """Google AI Studio自動操作クラス
    
    Google AI Studioウェブサイトでの自動操作を行う。
    - 既存のChromeプロファイルでログイン済みを前提
    - モデル選択
    - プロンプト送信と応答取得
    - ストリーミング応答の完了待機
    """
    
    URL = "https://aistudio.google.com"
    
    def __init__(self, browser_manager: BrowserManager):
        """初期化
        
        Args:
            browser_manager (BrowserManager): ブラウザマネージャーインスタンス
        """
        super().__init__("Google AI Studio")
        self.browser_manager = browser_manager
        
        # Google AI Studio固有のセレクター
        self.selectors = {
            'input': 'textarea[placeholder*="Enter a prompt"]',  # メイン入力欄
            'send_button': 'button[aria-label="Run"]',  # 実行ボタン
            'response_container': '.output-container',  # 応答コンテナ
            'response_text': '.response-content',  # 応答テキスト
            'model_selector': 'select[data-testid="model-selector"]',  # モデル選択ドロップダウン
            'model_dropdown': '.model-selector-dropdown',  # モデル選択メニュー
            'model_option': 'option',  # モデル選択オプション
            'stop_button': 'button[aria-label="Stop"]',  # 停止ボタン
            'new_prompt_button': 'button[aria-label="New prompt"]',  # 新しいプロンプトボタン
            'loading_indicator': '.loading-spinner',  # ローディング表示
            'error_message': '.error-alert',  # エラー表示
            'generation_progress': '.generation-progress',  # 生成進捗表示
        }
        
        # 利用可能なモデル（Google AI Studioの提供モデル）
        self.available_models = [
            "Gemini 1.5 Pro",
            "Gemini 1.5 Flash",
            "Gemini 1.0 Pro",
            "PaLM 2",
            "Codey"
        ]
        
        # 利用可能な設定
        self.available_settings = {
            "temperature": {"type": "slider", "min": 0, "max": 2, "default": 1},
            "top_k": {"type": "number", "min": 1, "max": 40, "default": 40},
            "top_p": {"type": "slider", "min": 0, "max": 1, "default": 0.95},
            "max_output_tokens": {"type": "number", "min": 1, "max": 8192, "default": 2048},
            "safety_settings": {"type": "object", "default": {}}
        }

    async def login(self) -> bool:
        """ログイン処理
        
        既存のChromeプロファイルでログイン済みを前提とする
        
        Returns:
            bool: ログイン成功時True
        """
        try:
            # ページを作成してGoogle AI Studioにアクセス
            self.page = await self.browser_manager.create_page("google_ai_studio", self.URL)
            if not self.page:
                self.logger.error("Google AI Studioページの作成に失敗")
                return False
            
            # ページ読み込み完了を待機
            await asyncio.sleep(3)
            
            # ログイン状態の確認
            # 入力欄が表示されていればログイン済みと判断
            if await self.wait_for_element(self.selectors['input'], timeout=10):
                self.is_logged_in = True
                self.logger.info("Google AI Studioログイン確認完了")
                return True
            else:
                # Googleアカウントでのログインボタンを探す
                login_selectors = [
                    'button:has-text("Sign in")',
                    'a:has-text("Get started")',
                    'button[data-testid="sign-in"]',
                    '.sign-in-button'
                ]
                
                for selector in login_selectors:
                    login_button = await self.page.query_selector(selector)
                    if login_button:
                        self.logger.error("Google AI Studioログインが必要です。手動でログインしてください。")
                        return False
                
                self.logger.error("Google AI Studio入力欄またはログインボタンが見つかりません")
                return False
                
        except Exception as e:
            self.logger.error(f"Google AI Studioログインエラー: {e}")
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
            
            # selectタグの場合はoptionを直接取得
            model_selector = await self.page.query_selector(self.selectors['model_selector'])
            if model_selector:
                option_elements = await model_selector.query_selector_all('option')
                models = []
                for option in option_elements:
                    text = await option.text_content()
                    value = await option.get_attribute('value')
                    if text and text.strip() and value:
                        models.append(text.strip())
                
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
            # モデルセレクターを取得
            if not await self.wait_for_element(self.selectors['model_selector'], timeout=5):
                self.logger.warning("モデルセレクターが見つかりません（デフォルトモデルを使用）")
                return True
            
            # selectタグの場合はselect_option()を使用
            model_selector = await self.page.query_selector(self.selectors['model_selector'])
            if model_selector:
                # option要素を検索して選択
                option_elements = await model_selector.query_selector_all('option')
                for option in option_elements:
                    text = await option.text_content()
                    if text and model_name in text:
                        value = await option.get_attribute('value')
                        if value:
                            await self.page.select_option(self.selectors['model_selector'], value)
                            self.current_model = model_name
                            self.logger.info(f"モデル選択完了: {model_name}")
                            await asyncio.sleep(1)
                            return True
                
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
            
            # パラメータ設定（Google AI Studioでは詳細設定パネルが必要）
            if any(key in settings for key in ["temperature", "top_k", "top_p", "max_output_tokens"]):
                # 設定パネルを開く
                settings_button = await self.page.query_selector('button[aria-label="Settings"]')
                if settings_button:
                    await settings_button.click()
                    await asyncio.sleep(1)
                    
                    # 各種パラメータを設定
                    for param, value in settings.items():
                        if param in ["temperature", "top_k", "top_p", "max_output_tokens"]:
                            param_input = await self.page.query_selector(f'input[name="{param}"]')
                            if param_input:
                                await param_input.fill(str(value))
                    
                    # 設定を保存
                    save_button = await self.page.query_selector('button:has-text("Save")')
                    if save_button:
                        await save_button.click()
            
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
            await self.page.fill(self.selectors['input'], text)
            await asyncio.sleep(0.5)
            
            # 実行ボタンをクリック
            send_button = await self.page.query_selector(self.selectors['send_button'])
            if send_button:
                await send_button.click()
            else:
                # キーボードショートカット（Ctrl+Enter）
                await self.page.keyboard.press('Control+Enter')
            
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
                if stop_button and await stop_button.is_visible():
                    # まだ生成中
                    await asyncio.sleep(1)
                    continue
                
                # 生成進捗表示の確認
                progress = await self.page.query_selector(self.selectors['generation_progress'])
                if progress and await progress.is_visible():
                    # まだ生成中
                    await asyncio.sleep(1)
                    continue
                
                # ローディングインジケーターの確認
                loading = await self.page.query_selector(self.selectors['loading_indicator'])
                if loading and await loading.is_visible():
                    # まだ読み込み中
                    await asyncio.sleep(1)
                    continue
                
                # 実行ボタンが再び使用可能かどうかを確認
                run_button = await self.page.query_selector(self.selectors['send_button'])
                if run_button:
                    is_disabled = await run_button.get_attribute('disabled')
                    if not is_disabled:
                        # 実行ボタンが使用可能なら応答完了
                        self.logger.info("Google AI Studio応答完了")
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
                '.output-content',
                '.model-response',
                '.generated-text',
                '[data-testid="output"]'
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
            
            # 最後の応答を取得
            last_response = response_elements[-1]
            
            # テキスト内容を取得
            text_elements = await last_response.query_selector_all(self.selectors['response_text'])
            if text_elements:
                response_text = await text_elements[-1].inner_text()
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
        """会話をクリア（新しいプロンプトを開始）
        
        Returns:
            bool: 成功時True
        """
        try:
            # 新しいプロンプトボタンを探してクリック
            new_prompt_selectors = [
                self.selectors['new_prompt_button'],
                'button[aria-label="New"]',
                'button:has-text("New prompt")',
                '.new-prompt-button'
            ]
            
            for selector in new_prompt_selectors:
                button = await self.page.query_selector(selector)
                if button:
                    await button.click()
                    await asyncio.sleep(2)
                    self.logger.info("会話クリア完了")
                    return True
            
            # 入力欄をクリアして新しいプロンプトを準備
            input_element = await self.page.query_selector(self.selectors['input'])
            if input_element:
                await input_element.click()
                await self.page.keyboard.press('Control+a')
                await self.page.keyboard.press('Delete')
                self.logger.info("入力欄クリアで会話リセット完了")
                return True
            
            self.logger.warning("新しいプロンプトボタンが見つかりません")
            return False
            
        except Exception as e:
            self.logger.error(f"会話クリアエラー: {e}")
            return False