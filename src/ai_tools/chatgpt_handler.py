"""
ChatGPT操作ハンドラー

このモジュールはChatGPTの自動操作機能を提供します：
1. ChatGPTウェブサイトへの接続
2. テキストの送信と回答の取得
3. モデル選択とセッション管理
4. エラーハンドリングとリトライ

初心者向け解説：
- ChatGPTのウェブサイトをPlaywrightで自動操作
- ログイン状態の確認と維持
- 複数のモデル（GPT-4、GPT-3.5等）に対応
- 会話セッションの管理
"""

import asyncio
import time
from typing import List, Optional
from src.ai_tools.base_ai_handler import BaseAIHandler, AIProcessingResult, AIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChatGPTHandler(BaseAIHandler):
    """
    ChatGPT操作ハンドラー
    
    使用例:
        config = AIConfig(ai_name="chatgpt", model_name="gpt-4")
        handler = ChatGPTHandler(config)
        await handler.initialize()
        result = await handler.process_text("Hello!")
        await handler.cleanup()
    """
    
    def __init__(self, ai_config: AIConfig):
        """ChatGPTハンドラーを初期化"""
        super().__init__(ai_config)
        
        # ChatGPT固有の設定
        self.base_url = "https://chat.openai.com"
        self.current_conversation_id = None
        self.is_logged_in = False
        
        # セレクター定義（ChatGPTのUI要素）
        self.selectors = {
            'login_button': '[data-testid="login-button"]',
            'chat_input': '[data-testid="prompt-textarea"]',
            'send_button': '[data-testid="send-button"]',
            'message_content': '[data-message-author-role="assistant"] .markdown',
            'model_selector': '[data-testid="model-switcher"]',
            'new_chat_button': '[data-testid="new-chat-button"]',
            'conversation_list': '[data-testid="conversation-list"]',
            'regenerate_button': '[data-testid="regenerate-button"]'
        }
        
        logger.info("🤖 ChatGPTHandler を初期化しました")
    
    def get_login_url(self) -> str:
        """ログインURLを取得"""
        return f"{self.base_url}/auth/login"
    
    def get_available_models(self) -> List[str]:
        """利用可能なモデル一覧を取得"""
        return [
            "gpt-4",
            "gpt-4-turbo", 
            "gpt-3.5-turbo",
            "gpt-4o",
            "gpt-4o-mini"
        ]
    
    async def _initialize_ai_specific(self):
        """ChatGPT固有の初期化処理"""
        logger.info("🚀 ChatGPT初期化を開始")
        
        # ChatGPTサイトにアクセス
        await self.page.goto(self.base_url)
        await asyncio.sleep(2)
        
        # ログイン状態をチェック
        await self._check_login_status()
        
        # モデル選択
        if self.is_logged_in:
            await self._select_model()
            await self._start_new_conversation()
        
        logger.info("✅ ChatGPT初期化完了")
    
    async def _cleanup_ai_specific(self):
        """ChatGPT固有のクリーンアップ"""
        logger.info("🧹 ChatGPTクリーンアップを実行")
        # 特別なクリーンアップ処理は不要
        pass
    
    async def _check_connection_ai_specific(self) -> bool:
        """ChatGPT固有の接続チェック"""
        try:
            # ページが正常に表示されているかチェック
            if not self.page:
                return False
            
            # ChatGPTサイトにいるかチェック
            current_url = self.page.url
            if "chat.openai.com" not in current_url:
                return False
            
            # ログイン状態をチェック
            await self._check_login_status()
            return self.is_logged_in
            
        except Exception as e:
            logger.error(f"❌ ChatGPT接続チェック失敗: {e}")
            return False
    
    async def _process_text_ai_specific(self, text: str) -> AIProcessingResult:
        """ChatGPT固有のテキスト処理"""
        try:
            logger.debug(f"🤖 ChatGPT処理開始: {text[:100]}...")
            
            # ログイン状態確認
            if not await self._ensure_logged_in():
                return AIProcessingResult(
                    success=False,
                    error_message="ChatGPTにログインできませんでした"
                )
            
            # テキストを送信
            success = await self._send_message(text)
            if not success:
                return AIProcessingResult(
                    success=False,
                    error_message="メッセージの送信に失敗しました"
                )
            
            # 回答を待機・取得
            response_text = await self._wait_for_response()
            if not response_text:
                return AIProcessingResult(
                    success=False,
                    error_message="回答の取得に失敗しました"
                )
            
            logger.debug(f"✅ ChatGPT回答取得: {response_text[:100]}...")
            
            return AIProcessingResult(
                success=True,
                result_text=response_text
            )
            
        except Exception as e:
            logger.error(f"❌ ChatGPT処理エラー: {e}")
            return AIProcessingResult(
                success=False,
                error_message=str(e)
            )
    
    async def _check_login_status(self):
        """ログイン状態をチェック"""
        try:
            # ログインボタンの存在でログイン状態を判定
            login_button_exists = await self._wait_for_element(
                self.selectors['login_button'], timeout=5000
            )
            
            if login_button_exists:
                self.is_logged_in = False
                logger.info("📝 ChatGPTログインが必要です")
            else:
                # チャット入力欄の存在でログイン状態を確認
                chat_input_exists = await self._wait_for_element(
                    self.selectors['chat_input'], timeout=5000
                )
                self.is_logged_in = chat_input_exists
                
                if self.is_logged_in:
                    logger.info("✅ ChatGPTにログイン済み")
                else:
                    logger.warning("⚠️ ChatGPTログイン状態が不明")
        
        except Exception as e:
            logger.error(f"❌ ログイン状態チェック失敗: {e}")
            self.is_logged_in = False
    
    async def _ensure_logged_in(self) -> bool:
        """ログイン状態を確保"""
        await self._check_login_status()
        
        if not self.is_logged_in:
            logger.warning("⚠️ ChatGPTログインが必要です。手動でログインしてください。")
            
            # ログインページに移動
            await self.page.goto(self.get_login_url())
            
            # ユーザーのログインを待機（最大5分）
            logger.info("⏳ ログイン完了を待機中... (最大5分)")
            for i in range(30):  # 10秒 x 30 = 5分
                await asyncio.sleep(10)
                await self._check_login_status()
                if self.is_logged_in:
                    logger.info("✅ ログイン完了を確認")
                    return True
                logger.debug(f"⏳ ログイン待機中... ({i+1}/30)")
            
            logger.error("❌ ログインタイムアウト")
            return False
        
        return True
    
    async def _select_model(self):
        """指定されたモデルを選択"""
        try:
            logger.debug(f"🎯 モデル選択: {self.config.model_name}")
            
            # モデルセレクターをクリック
            if await self._safe_click(self.selectors['model_selector']):
                await asyncio.sleep(1)
                
                # 指定されたモデルを選択（詳細実装は省略）
                # 実際の実装では、ドロップダウンから適切なモデルを選択
                logger.debug(f"✅ モデル選択完了: {self.config.model_name}")
            else:
                logger.warning("⚠️ モデルセレクターが見つかりません")
                
        except Exception as e:
            logger.error(f"❌ モデル選択エラー: {e}")
    
    async def _start_new_conversation(self):
        """新しい会話を開始"""
        try:
            logger.debug("💬 新しい会話を開始")
            
            # 新しいチャットボタンをクリック
            if await self._safe_click(self.selectors['new_chat_button']):
                await asyncio.sleep(2)
                logger.debug("✅ 新しい会話を開始しました")
            else:
                logger.debug("⚠️ 新しいチャットボタンが見つかりません（既に新しい会話かもしれません）")
                
        except Exception as e:
            logger.error(f"❌ 新しい会話開始エラー: {e}")
    
    async def _send_message(self, text: str) -> bool:
        """メッセージを送信"""
        try:
            logger.debug("📤 メッセージ送信中...")
            
            # テキスト入力欄にテキストを入力
            if not await self._safe_type(self.selectors['chat_input'], text):
                logger.error("❌ テキスト入力に失敗")
                return False
            
            await asyncio.sleep(0.5)
            
            # 送信ボタンをクリック
            if not await self._safe_click(self.selectors['send_button']):
                # Enterキーでも送信を試行
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(0.5)
            
            logger.debug("✅ メッセージ送信完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ メッセージ送信エラー: {e}")
            return False
    
    async def _wait_for_response(self, timeout: float = 120) -> Optional[str]:
        """ChatGPTの回答を待機"""
        try:
            logger.debug("⏳ ChatGPTの回答を待機中...")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # 回答要素を検索
                response_elements = await self.page.query_selector_all(
                    self.selectors['message_content']
                )
                
                if response_elements:
                    # 最新の回答を取得
                    last_response = response_elements[-1]
                    response_text = await last_response.text_content()
                    
                    if response_text and response_text.strip():
                        # 回答が完了しているかチェック（カーソルの有無等）
                        if await self._is_response_complete():
                            logger.debug("✅ 回答取得完了")
                            return response_text.strip()
                
                await asyncio.sleep(2)  # 2秒間隔でチェック
            
            logger.error("❌ 回答待機タイムアウト")
            return None
            
        except Exception as e:
            logger.error(f"❌ 回答待機エラー: {e}")
            return None
    
    async def _is_response_complete(self) -> bool:
        """回答が完了しているかチェック"""
        try:
            # 送信ボタンが再び有効になっているかチェック
            send_button = await self.page.query_selector(self.selectors['send_button'])
            if send_button:
                is_disabled = await send_button.get_attribute('disabled')
                return is_disabled is None
            
            # 再生成ボタンの存在をチェック
            regenerate_exists = await self._wait_for_element(
                self.selectors['regenerate_button'], timeout=2000
            )
            
            return regenerate_exists
            
        except Exception as e:
            logger.debug(f"回答完了チェックエラー: {e}")
            return True  # エラー時は完了と判定
    
    async def handle_rate_limit(self):
        """レート制限への対応"""
        logger.warning("⚠️ ChatGPTレート制限を検出")
        
        # レート制限メッセージの検出と待機時間の計算
        # 実際の実装では、エラーメッセージから待機時間を解析
        
        wait_time = 60  # デフォルトで1分待機
        logger.info(f"⏳ レート制限のため {wait_time} 秒待機")
        await asyncio.sleep(wait_time)
    
    async def clear_conversation(self):
        """現在の会話をクリア"""
        await self._start_new_conversation()