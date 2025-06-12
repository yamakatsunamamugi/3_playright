import asyncio
import time
from typing import Dict, List, Optional
from src.utils.logger import get_logger
from src.interfaces.sheet_interface import ISheetProcessor, ISheetHandler
from src.interfaces.ai_interface import IAIManager
from src.interfaces.gui_interface import IGUIController, ProcessStatus
from config.settings import settings


logger = get_logger(__name__)


class Orchestrator:
    """
    全体の処理フローを管理するオーケストレーター
    統括者Dが結合時に実装する
    """
    
    def __init__(self):
        # 各コンポーネントは結合時に実際の実装に置き換える
        self.sheet_processor: Optional[ISheetProcessor] = None
        self.sheet_handler: Optional[ISheetHandler] = None
        self.ai_manager: Optional[IAIManager] = None
        self.gui_controller: Optional[IGUIController] = None
        
        self.is_processing = False
        self.should_stop = False
        
    def set_components(self, 
                      sheet_processor: ISheetProcessor,
                      sheet_handler: ISheetHandler,
                      ai_manager: IAIManager,
                      gui_controller: IGUIController):
        """コンポーネントを設定"""
        self.sheet_processor = sheet_processor
        self.sheet_handler = sheet_handler
        self.ai_manager = ai_manager
        self.gui_controller = gui_controller
        
    async def process_spreadsheet(self, config: Dict) -> bool:
        """
        メイン処理フロー
        
        Args:
            config: {
                'spreadsheet_url': str,
                'sheet_name': str,
                'ai_tools': {tool_name: {'enabled': bool, 'model': str}}
            }
        """
        if self.is_processing:
            logger.warning("既に処理中です")
            return False
            
        try:
            self.is_processing = True
            self.should_stop = False
            
            logger.info("スプレッドシート処理を開始します")
            self.gui_controller.update_status(ProcessStatus.PROCESSING)
            self.gui_controller.add_log("処理を開始しました")
            
            # 1. スプレッドシートIDの抽出
            sheet_id = self._extract_sheet_id(config['spreadsheet_url'])
            sheet_name = config['sheet_name']
            
            # 2. シートデータの読み込み
            self.gui_controller.add_log("スプレッドシートからデータを読み込み中...")
            sheet_data = self.sheet_handler.get_sheet_data(sheet_id, sheet_name)
            
            # 3. 作業指示行とコピー列の検出
            work_row_idx = self.sheet_processor.find_work_instruction_row(sheet_data)
            if work_row_idx == -1:
                raise ValueError("作業指示行が見つかりません")
                
            header_row = sheet_data[work_row_idx]
            copy_columns = self.sheet_processor.find_copy_columns(header_row)
            
            if not copy_columns:
                raise ValueError("コピー列が見つかりません")
                
            self.gui_controller.add_log(f"コピー列を{len(copy_columns)}個検出しました")
            
            # 4. 処理対象行の取得
            process_rows = self.sheet_processor.get_process_rows(sheet_data)
            total_tasks = len(process_rows) * len(copy_columns)
            
            self.gui_controller.update_progress(0, total_tasks, "処理を開始します")
            
            # 5. AIツールの初期化
            ai_config = config['ai_tools']
            init_results = self.ai_manager.initialize_all_tools(ai_config)
            failed_tools = [tool for tool, success in init_results.items() if not success]
            
            if failed_tools:
                self.gui_controller.add_log(f"以下のAIツールの初期化に失敗: {failed_tools}", "WARNING")
            
            # 6. 各行・各列の処理
            current_task = 0
            for copy_col in copy_columns:
                if self.should_stop:
                    break
                    
                related_cols = self.sheet_processor.calculate_related_columns(copy_col)
                
                for row_idx in process_rows:
                    if self.should_stop:
                        break
                        
                    current_task += 1
                    
                    # 処理状態をチェック
                    process_col = related_cols['process_col']
                    current_status = self.sheet_handler.read_cell(sheet_id, sheet_name, row_idx, process_col)
                    
                    if current_status in [settings.PROCESS_STATUS_PROCESSED]:
                        self.gui_controller.add_log(f"行{row_idx + 1}は既に処理済みです", "INFO")
                        continue
                        
                    # コピー列からテキストを取得
                    prompt_text = self.sheet_handler.read_cell(sheet_id, sheet_name, row_idx, copy_col)
                    
                    if not prompt_text.strip():
                        self.gui_controller.add_log(f"行{row_idx + 1}のプロンプトが空です", "WARNING")
                        continue
                    
                    # AI処理の実行
                    await self._process_single_task(
                        sheet_id, sheet_name, row_idx, copy_col, 
                        related_cols, prompt_text, ai_config
                    )
                    
                    # 進捗更新
                    self.gui_controller.update_progress(
                        current_task, total_tasks, 
                        f"行{row_idx + 1}を処理中... ({current_task}/{total_tasks})"
                    )
                    
            if self.should_stop:
                self.gui_controller.update_status(ProcessStatus.PAUSED)
                self.gui_controller.add_log("処理が停止されました")
            else:
                self.gui_controller.update_status(ProcessStatus.COMPLETED)
                self.gui_controller.add_log("全ての処理が完了しました")
                
            return True
            
        except Exception as e:
            logger.error(f"処理中にエラーが発生しました: {e}")
            self.gui_controller.update_status(ProcessStatus.ERROR)
            self.gui_controller.add_log(f"エラー: {e}", "ERROR")
            return False
            
        finally:
            self.is_processing = False
    
    async def _process_single_task(self, sheet_id: str, sheet_name: str, 
                                  row_idx: int, copy_col: int, related_cols: Dict,
                                  prompt_text: str, ai_config: Dict):
        """単一タスクの処理"""
        process_col = related_cols['process_col']
        error_col = related_cols['error_col']
        paste_col = related_cols['paste_col']
        
        # 処理開始をマーク
        self.sheet_handler.write_cell(sheet_id, sheet_name, row_idx, process_col, "処理中")
        
        # 有効なAIツールを取得
        enabled_tools = [tool for tool, config in ai_config.items() if config.get('enabled', False)]
        
        if not enabled_tools:
            self.sheet_handler.write_cell(sheet_id, sheet_name, row_idx, error_col, "有効なAIツールがありません")
            return
            
        # 最初の有効なAIツールを使用
        tool_name = enabled_tools[0]
        
        for attempt in range(settings.MAX_RETRIES):
            try:
                tool = self.ai_manager.get_tool(tool_name)
                response = tool.send_prompt(prompt_text, settings.AI_TIMEOUT)
                
                # 成功時の処理
                self.sheet_handler.write_cell(sheet_id, sheet_name, row_idx, paste_col, response)
                self.sheet_handler.write_cell(sheet_id, sheet_name, row_idx, process_col, settings.PROCESS_STATUS_PROCESSED)
                
                self.gui_controller.add_log(f"行{row_idx + 1}: {tool_name}で処理完了")
                break
                
            except Exception as e:
                logger.warning(f"行{row_idx + 1}の処理でエラー（試行{attempt + 1}回目）: {e}")
                
                if attempt == settings.MAX_RETRIES - 1:
                    # 最終試行でも失敗
                    error_msg = f"エラー({tool_name}): {str(e)}"
                    self.sheet_handler.write_cell(sheet_id, sheet_name, row_idx, error_col, error_msg)
                    self.gui_controller.add_log(f"行{row_idx + 1}: 処理失敗 - {error_msg}", "ERROR")
                else:
                    # リトライ待機
                    await asyncio.sleep(settings.RETRY_DELAY)
    
    def stop_processing(self):
        """処理を停止"""
        self.should_stop = True
        logger.info("処理停止が要求されました")
        
    def _extract_sheet_id(self, url: str) -> str:
        """GoogleスプレッドシートのURLからIDを抽出"""
        # https://docs.google.com/spreadsheets/d/{ID}/edit#gid=0
        if '/spreadsheets/d/' in url:
            start = url.find('/spreadsheets/d/') + len('/spreadsheets/d/')
            end = url.find('/', start)
            if end == -1:
                end = url.find('#', start)
            if end == -1:
                end = len(url)
            return url[start:end]
        raise ValueError("無効なスプレッドシートURLです")