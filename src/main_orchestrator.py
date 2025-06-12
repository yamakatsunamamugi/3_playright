"""
メインオーケストレーター
各コンポーネントを統合して実際の処理を実行
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
from src.utils.logger import get_logger
from src.orchestrator import Orchestrator
from src.sheets.processor import SheetProcessor
from src.sheets.client import GoogleSheetsClient
from src.sheets.data_handler import DataHandler
from src.ai_tools.browser_manager import BrowserManager
from config.settings import settings

# AIツールハンドラーのインポート
from src.ai_tools.chatgpt_handler import ChatGPTHandler
from src.ai_tools.claude import ClaudeHandler
from src.ai_tools.gemini import GeminiHandler
from src.ai_tools.genspark import GensparkHandler
from src.ai_tools.google_ai_studio import GoogleAIStudioHandler

logger = get_logger(__name__)


class AIManager:
    """AI管理クラス - 複数のAIツールを管理"""
    
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.ai_handlers = {}
        self.initialized = False
        
    async def initialize(self, chrome_profile: str = None) -> bool:
        """ブラウザとAIハンドラーを初期化"""
        try:
            # ブラウザマネージャーを起動
            logger.info("ブラウザを起動中...")
            success = await self.browser_manager.start_browser(
                headless=False,
                use_existing_profile=True,
                profile_dir=chrome_profile or "Default"
            )
            
            if not success:
                logger.error("ブラウザの起動に失敗しました")
                return False
                
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"AI管理の初期化エラー: {e}")
            return False
            
    def register_handler(self, tool_name: str, config: Dict[str, Any]) -> bool:
        """AIハンドラーを登録"""
        try:
            handler_class = {
                "ChatGPT": ChatGPTHandler,
                "Claude": ClaudeHandler,
                "Gemini": GeminiHandler,
                "Genspark": GensparkHandler,
                "Google AI Studio": GoogleAIStudioHandler
            }.get(tool_name)
            
            if not handler_class:
                logger.error(f"未知のAIツール: {tool_name}")
                return False
                
            # ハンドラーのインスタンスを作成
            handler = handler_class(self.browser_manager)
            handler.model = config.get('model', '')
            handler.settings = config.get('settings', {})
            
            self.ai_handlers[tool_name] = handler
            logger.info(f"{tool_name}ハンドラーを登録しました")
            return True
            
        except Exception as e:
            logger.error(f"{tool_name}ハンドラーの登録エラー: {e}")
            return False
            
    async def process_with_ai(self, tool_name: str, prompt: str, timeout: int = 120) -> str:
        """指定したAIツールでプロンプトを処理"""
        handler = self.ai_handlers.get(tool_name)
        if not handler:
            raise ValueError(f"AIハンドラーが登録されていません: {tool_name}")
            
        try:
            # ログイン状態を確認
            if not await handler.is_logged_in():
                logger.warning(f"{tool_name}にログインしていません。手動でログインしてください。")
                # ここでGUIに通知してユーザーにログインを促す
                await asyncio.sleep(10)  # ユーザーがログインする時間を確保
                
            # プロンプトを送信
            result = await handler.send_prompt_async(prompt, timeout)
            return result
            
        except Exception as e:
            logger.error(f"{tool_name}での処理エラー: {e}")
            raise
            
    async def cleanup(self):
        """リソースのクリーンアップ"""
        if self.browser_manager:
            await self.browser_manager.cleanup()
            

class MainOrchestrator:
    """メインオーケストレーター - 全体の処理を管理"""
    
    def __init__(self, gui_controller):
        self.gui_controller = gui_controller
        self.orchestrator = Orchestrator()
        self.ai_manager = AIManager()
        
        # Googleシートコンポーネント
        self.sheet_client = GoogleSheetsClient()
        self.sheet_processor = SheetProcessor()
        self.data_handler = DataHandler()
        
        # 処理状態
        self.is_processing = False
        self.should_stop = False
        
        # コピー列ごとのAI設定を保持
        self.column_ai_mapping = {}  # {column_index: ai_tool_name}
        
    async def initialize(self, chrome_profile: str = None) -> bool:
        """初期化処理"""
        try:
            # AI管理の初期化
            if not await self.ai_manager.initialize(chrome_profile):
                return False
                
            # オーケストレーターにコンポーネントを設定
            self.orchestrator.set_components(
                sheet_processor=self.sheet_processor,
                sheet_handler=self.sheet_client,
                ai_manager=self,  # AIManagerインターフェースとして自身を渡す
                gui_controller=self.gui_controller
            )
            
            return True
            
        except Exception as e:
            logger.error(f"初期化エラー: {e}")
            return False
            
    def set_column_ai_mapping(self, mapping: Dict[int, str]):
        """コピー列とAIツールのマッピングを設定"""
        self.column_ai_mapping = mapping
        logger.info(f"コピー列とAIのマッピングを設定: {mapping}")
        
    async def process_spreadsheet(self, config: Dict) -> bool:
        """スプレッドシート処理のメイン関数"""
        if self.is_processing:
            logger.warning("既に処理中です")
            return False
            
        try:
            self.is_processing = True
            self.should_stop = False
            
            # AIツールの登録
            ai_tools = config.get('ai_tools', {})
            for tool_name, tool_config in ai_tools.items():
                if tool_config.get('enabled', False):
                    self.ai_manager.register_handler(tool_name, tool_config)
                    
            # スプレッドシートの処理
            sheet_url = config['spreadsheet_url']
            sheet_name = config['sheet_name']
            
            # シートデータの読み込み
            self.gui_controller.add_log("スプレッドシートを読み込み中...")
            sheet_id = self._extract_sheet_id(sheet_url)
            
            # 認証
            if not self.sheet_client.authenticate():
                raise Exception("Google Sheets認証に失敗しました")
                
            # データ取得
            sheet_data = self.sheet_client.get_sheet_data(sheet_id, sheet_name)
            if not sheet_data:
                raise Exception("シートデータの取得に失敗しました")
                
            # 作業指示行の検出
            work_row_idx = self._find_work_instruction_row(sheet_data)
            if work_row_idx == -1:
                raise Exception("作業指示行が見つかりません")
                
            # コピー列の検出
            header_row = sheet_data[work_row_idx]
            copy_columns = self._find_copy_columns(header_row)
            
            if not copy_columns:
                raise Exception("コピー列が見つかりません")
                
            self.gui_controller.add_log(f"{len(copy_columns)}個のコピー列を検出しました")
            
            # 処理対象行の取得
            process_rows = self._get_process_rows(sheet_data, work_row_idx)
            
            if not process_rows:
                raise Exception("処理対象行が見つかりません")
                
            self.gui_controller.add_log(f"{len(process_rows)}個の処理対象行を検出しました")
            
            # 各コピー列・各行の処理
            total_tasks = len(copy_columns) * len(process_rows)
            current_task = 0
            
            for copy_col_idx in copy_columns:
                if self.should_stop:
                    break
                    
                # この列で使用するAIツールを決定
                ai_tool = self.column_ai_mapping.get(copy_col_idx, list(ai_tools.keys())[0])
                
                self.gui_controller.add_log(f"列{copy_col_idx + 1}を{ai_tool}で処理開始")
                
                # 関連列の計算
                process_col_idx = copy_col_idx - 2
                error_col_idx = copy_col_idx - 1
                paste_col_idx = copy_col_idx + 1
                
                for row_idx in process_rows:
                    if self.should_stop:
                        break
                        
                    current_task += 1
                    self.gui_controller.update_progress(
                        current_task, total_tasks,
                        f"行{row_idx + 1}を処理中 ({current_task}/{total_tasks})"
                    )
                    
                    # 処理状態をチェック
                    if process_col_idx >= 0:
                        status = self._get_cell_value(sheet_data, row_idx, process_col_idx)
                        if status == "処理済み":
                            self.gui_controller.add_log(f"行{row_idx + 1}は既に処理済みです")
                            continue
                            
                    # プロンプトテキストを取得
                    prompt_text = self._get_cell_value(sheet_data, row_idx, copy_col_idx)
                    if not prompt_text.strip():
                        self.gui_controller.add_log(f"行{row_idx + 1}のプロンプトが空です")
                        continue
                        
                    # AI処理を実行
                    await self._process_single_cell(
                        sheet_id, sheet_name, row_idx,
                        copy_col_idx, process_col_idx, error_col_idx, paste_col_idx,
                        prompt_text, ai_tool
                    )
                    
                    # 少し待機（API制限対策）
                    await asyncio.sleep(1)
                    
            if self.should_stop:
                self.gui_controller.add_log("処理が中断されました")
            else:
                self.gui_controller.add_log("全ての処理が完了しました")
                
            return True
            
        except Exception as e:
            logger.error(f"処理中にエラー: {e}")
            self.gui_controller.add_log(f"エラー: {e}", "ERROR")
            return False
            
        finally:
            self.is_processing = False
            
    async def _process_single_cell(self, sheet_id: str, sheet_name: str,
                                  row_idx: int, copy_col_idx: int,
                                  process_col_idx: int, error_col_idx: int,
                                  paste_col_idx: int, prompt_text: str,
                                  ai_tool: str):
        """単一セルの処理"""
        # 処理開始をマーク
        if process_col_idx >= 0:
            self.sheet_client.write_cell(
                sheet_id, sheet_name, row_idx, process_col_idx, "処理中"
            )
            
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # AIで処理
                self.gui_controller.add_log(f"行{row_idx + 1}: {ai_tool}で処理中...")
                response = await self.ai_manager.process_with_ai(ai_tool, prompt_text)
                
                # 結果を書き込み
                self.sheet_client.write_cell(
                    sheet_id, sheet_name, row_idx, paste_col_idx, response
                )
                
                # 処理完了をマーク
                if process_col_idx >= 0:
                    self.sheet_client.write_cell(
                        sheet_id, sheet_name, row_idx, process_col_idx, "処理済み"
                    )
                    
                self.gui_controller.add_log(f"行{row_idx + 1}: 処理完了")
                break
                
            except Exception as e:
                retry_count += 1
                error_msg = f"エラー(試行{retry_count}/{max_retries}): {str(e)}"
                logger.error(error_msg)
                
                if retry_count >= max_retries:
                    # エラーを記録
                    if error_col_idx >= 0:
                        self.sheet_client.write_cell(
                            sheet_id, sheet_name, row_idx, error_col_idx, error_msg
                        )
                    self.gui_controller.add_log(f"行{row_idx + 1}: 処理失敗 - {error_msg}", "ERROR")
                    break
                else:
                    # リトライ前に待機
                    await asyncio.sleep(10)
                    
    def stop_processing(self):
        """処理を停止"""
        self.should_stop = True
        self.orchestrator.stop_processing()
        
    async def cleanup(self):
        """クリーンアップ"""
        await self.ai_manager.cleanup()
        
    # ヘルパーメソッド
    def _extract_sheet_id(self, url: str) -> str:
        """スプレッドシートURLからIDを抽出"""
        if '/spreadsheets/d/' in url:
            start = url.find('/spreadsheets/d/') + len('/spreadsheets/d/')
            end = url.find('/', start)
            if end == -1:
                end = url.find('#', start) if '#' in url[start:] else len(url)
            return url[start:end]
        raise ValueError("無効なスプレッドシートURLです")
        
    def _find_work_instruction_row(self, sheet_data: List[List[Any]]) -> int:
        """作業指示行を検出"""
        for i, row in enumerate(sheet_data):
            if row and str(row[0]).strip() == "作業指示行":
                return i
        return -1
        
    def _find_copy_columns(self, header_row: List[Any]) -> List[int]:
        """コピー列を検出"""
        copy_columns = []
        for i, cell in enumerate(header_row):
            if str(cell).strip() == "コピー":
                copy_columns.append(i)
        return copy_columns
        
    def _get_process_rows(self, sheet_data: List[List[Any]], start_row: int) -> List[int]:
        """処理対象行を取得"""
        process_rows = []
        
        # 作業指示行の次の行から開始
        for i in range(start_row + 1, len(sheet_data)):
            row = sheet_data[i]
            if not row or not row[0]:
                break
                
            # A列が数字の行を処理対象とする
            try:
                int(str(row[0]))
                process_rows.append(i)
            except ValueError:
                continue
                
        return process_rows
        
    def _get_cell_value(self, sheet_data: List[List[Any]], row: int, col: int) -> str:
        """セルの値を安全に取得"""
        if 0 <= row < len(sheet_data) and 0 <= col < len(sheet_data[row]):
            return str(sheet_data[row][col])
        return ""
        
    # AIManagerインターフェースの実装
    def initialize_all_tools(self, config: Dict[str, Dict]) -> Dict[str, bool]:
        """全AIツールを初期化（インターフェース互換性のため）"""
        results = {}
        for tool_name, tool_config in config.items():
            if tool_config.get('enabled', False):
                results[tool_name] = self.ai_manager.register_handler(tool_name, tool_config)
        return results
        
    def get_tool(self, tool_name: str):
        """AIツールを取得（インターフェース互換性のため）"""
        return self.ai_manager.ai_handlers.get(tool_name)