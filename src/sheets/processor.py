"""
スプレッドシート処理の核となるプロセッサー（Day 2-3拡張版）

このモジュールは以下の機能を提供します：
1. 作業指示行の検出（A列に「作業指示行」がある行を特定）
2. コピー列の検索（ヘッダー行から「コピー」列を全て検出）
3. 関連列の位置計算（処理列、エラー列、貼り付け列の位置）
4. 処理対象行の取得（A列が連番の行を検出）
5. 処理状態管理（未処理/処理中/処理済み/エラー）
6. 進捗追跡機能

初心者向け解説：
- このクラスはGoogleスプレッドシートの構造を解析します
- 「作業指示行」を基準として、どの列でどんな処理をするかを決定します
- 処理の進捗状況を追跡し、途中で止まっても再開できます
- エラーが発生した場合は詳細なログを出力して、問題箇所を特定しやすくします
"""

from typing import List, Dict, Optional, Set, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

from src.interfaces.sheet_interface import ISheetProcessor
from src.utils.logger import get_logger
from src.utils.sheet_utils import SheetUtils

logger = get_logger(__name__)


class ProcessingStatus(Enum):
    """処理状態の定義"""
    UNPROCESSED = "未処理"
    PROCESSING = "処理中"
    PROCESSED = "処理済み"
    ERROR = "エラー"
    SKIPPED = "スキップ"


@dataclass
class ProcessingTask:
    """処理タスクの定義"""
    row_index: int
    copy_column: int
    copy_text: str
    status: ProcessingStatus = ProcessingStatus.UNPROCESSED
    error_message: str = ""
    
    @property
    def row_number(self) -> int:
        """行番号（1ベース）"""
        return self.row_index + 1
    
    @property
    def copy_column_letter(self) -> str:
        """コピー列の文字（A, B, C...）"""
        return SpreadsheetProcessor._static_index_to_column_letter(self.copy_column)


@dataclass
class ProcessingProgress:
    """処理進捗の追跡"""
    total_tasks: int = 0
    completed_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    
    @property
    def completion_percentage(self) -> float:
        """完了率（0-100）"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
    
    @property
    def success_rate(self) -> float:
        """成功率（0-100）"""
        if self.completed_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.completed_tasks) * 100


@dataclass
class ColumnMapping:
    """列マッピング情報"""
    copy_column: int
    process_column: int
    error_column: int
    paste_column: int
    
    @property
    def is_valid(self) -> bool:
        """すべての列が有効かチェック"""
        return all(col >= 0 for col in [self.copy_column, self.process_column, 
                                       self.error_column, self.paste_column])
    
    @property
    def column_letters(self) -> Dict[str, str]:
        """列文字の辞書"""
        converter = SpreadsheetProcessor._static_index_to_column_letter
        return {
            'copy': converter(self.copy_column),
            'process': converter(self.process_column) if self.process_column >= 0 else '無効',
            'error': converter(self.error_column) if self.error_column >= 0 else '無効',
            'paste': converter(self.paste_column)
        }


class SpreadsheetProcessor(ISheetProcessor):
    """
    スプレッドシート処理のメインクラス（拡張版）
    
    使用例:
        processor = SpreadsheetProcessor()
        
        # 基本的な解析
        work_row = processor.find_work_instruction_row(sheet_data)
        copy_columns = processor.find_copy_columns(sheet_data[work_row])
        
        # 拡張機能
        processor.analyze_sheet_structure(sheet_data)
        tasks = processor.create_processing_tasks(sheet_data)
        progress = processor.get_processing_progress()
        
    注意事項:
        - 全ての列インデックスは0ベースです（A列=0, B列=1, ...）
        - 行インデックスも0ベースです（1行目=0, 2行目=1, ...）
        - 処理状態は自動的に追跡されます
    """
    
    def __init__(self):
        """プロセッサーを初期化"""
        logger.info("📊 SpreadsheetProcessor（拡張版）を初期化しました")
        self.work_instruction_marker = "作業指示行"
        self.copy_column_marker = "コピー"
        
        # 拡張機能用の状態管理
        self.sheet_structure: Optional[Dict] = None
        self.column_mappings: List[ColumnMapping] = []
        self.processing_tasks: List[ProcessingTask] = []
        self.processing_progress = ProcessingProgress()
        
        # 設定可能なオプション
        self.options = {
            'skip_empty_cells': True,
            'validate_before_processing': True,
            'track_progress': True,
            'auto_resume': True
        }
    
    # === ISheetProcessor インターフェース実装 ===
    
    def find_work_instruction_row(self, sheet_data: List[List[str]]) -> int:
        """
        A列に'作業指示行'という文字列がある行を検索
        
        詳細説明:
        1. シートデータの各行のA列（0列目）をチェック
        2. セルの値が「作業指示行」と完全一致する行を検索
        3. 最初に見つかった行のインデックスを返す
        
        Args:
            sheet_data: シート全体のデータ（2次元リスト）
                      例: [['', '', ''], ['A', 'B', 'C'], ['作業指示行', 'コピー', '貼り付け']]
                      
        Returns:
            作業指示行のインデックス（0ベース）
            見つからない場合は-1
        """
        logger.info(f"🔍 作業指示行を検索開始 - データ行数: {len(sheet_data)}")
        
        if not sheet_data:
            logger.warning("⚠️ シートデータが空です")
            return -1
            
        for row_idx, row_data in enumerate(sheet_data):
            # A列（インデックス0）が存在するかチェック
            if len(row_data) == 0:
                logger.debug(f"行 {row_idx + 1}: A列が存在しません（空行）")
                continue
                
            a_cell_value = str(row_data[0]).strip()
            logger.debug(f"行 {row_idx + 1}: A列の値 = '{a_cell_value}'")
            
            if a_cell_value == self.work_instruction_marker:
                logger.info(f"✅ 作業指示行を発見: {row_idx + 1}行目（0ベース: {row_idx}）")
                
                # 構造情報を更新
                if self.sheet_structure is None:
                    self.sheet_structure = {}
                self.sheet_structure['work_instruction_row'] = row_idx
                
                return row_idx
                
        logger.warning(f"❌ 作業指示行が見つかりませんでした。A列に'{self.work_instruction_marker}'がある行を確認してください")
        return -1
    
    def find_copy_columns(self, header_row: List[str]) -> List[int]:
        """
        ヘッダー行から'コピー'と完全一致する列を全て検索
        
        詳細説明:
        1. ヘッダー行の各セルをチェック
        2. 「コピー」と完全一致するセルの列インデックスを収集
        3. 複数の「コピー」列が存在する可能性に対応
        
        Args:
            header_row: ヘッダー行のデータ（1次元リスト）
                       例: ['', '処理', 'エラー', 'コピー', '貼り付け', '', 'コピー2', '貼り付け2']
                       
        Returns:
            コピー列のインデックスリスト（0ベース）
            見つからない場合は空リスト
        """
        logger.info(f"🔍 コピー列を検索開始 - ヘッダー列数: {len(header_row)}")
        
        copy_columns = []
        
        for col_idx, cell_value in enumerate(header_row):
            cell_value_str = str(cell_value).strip()
            logger.debug(f"列 {self._index_to_column_letter(col_idx)}: 値 = '{cell_value_str}'")
            
            if cell_value_str == self.copy_column_marker:
                copy_columns.append(col_idx)
                logger.info(f"✅ コピー列を発見: {self._index_to_column_letter(col_idx)}列（0ベース: {col_idx}）")
                
        if copy_columns:
            column_letters = [self._index_to_column_letter(idx) for idx in copy_columns]
            logger.info(f"🎯 コピー列検索完了 - 見つかった列: {column_letters}")
            
            # 構造情報を更新
            if self.sheet_structure is None:
                self.sheet_structure = {}
            self.sheet_structure['copy_columns'] = copy_columns
            
        else:
            logger.warning(f"❌ コピー列が見つかりませんでした。ヘッダー行に'{self.copy_column_marker}'がある列を確認してください")
            
        return copy_columns
    
    def calculate_related_columns(self, copy_col: int) -> Dict[str, int]:
        """
        コピー列を基準として関連列の位置を計算
        
        詳細説明:
        - 処理列: コピー列の2つ左（copy_col - 2）
        - エラー列: コピー列の1つ左（copy_col - 1）  
        - 貼り付け列: コピー列の1つ右（copy_col + 1）
        
        境界チェック:
        - 処理列とエラー列が0未満（A列より左）にならないよう検証
        - 無効な場合は-1を設定してエラーとして扱う
        
        Args:
            copy_col: コピー列のインデックス（0ベース）
                     
        Returns:
            関連列の辞書 {'process_col': int, 'error_col': int, 'paste_col': int}
            無効な列は-1
        """
        logger.info(f"📐 関連列位置を計算開始 - コピー列: {self._index_to_column_letter(copy_col)}（0ベース: {copy_col}）")
        
        # 各列の位置を計算
        process_col = copy_col - 2
        error_col = copy_col - 1
        paste_col = copy_col + 1
        
        # 境界チェック
        if process_col < 0:
            logger.warning(f"⚠️ 処理列が範囲外: {process_col} < 0 - 処理列を無効化")
            process_col = -1
            
        if error_col < 0:
            logger.warning(f"⚠️ エラー列が範囲外: {error_col} < 0 - エラー列を無効化")
            error_col = -1
            
        result = {
            'process_col': process_col,
            'error_col': error_col,
            'paste_col': paste_col
        }
        
        # 結果をログ出力
        valid_columns = []
        for col_type, col_idx in result.items():
            if col_idx >= 0:
                col_letter = self._index_to_column_letter(col_idx)
                valid_columns.append(f"{col_type}: {col_letter}列")
                logger.info(f"✅ {col_type}: {col_letter}列（0ベース: {col_idx}）")
            else:
                logger.warning(f"❌ {col_type}: 無効（範囲外）")
                
        logger.info(f"📐 関連列計算完了 - {', '.join(valid_columns)}")
        return result
    
    def get_process_rows(self, sheet_data: List[List[str]]) -> List[int]:
        """
        A列が'1'から始まる連番の行を取得
        
        詳細説明:
        1. A列の各セルをチェック
        2. 数値として解釈可能で、1から始まる連番の行を検出
        3. 連番が途切れた時点で終了
        4. 空白セルが現れた時点で終了
        
        Args:
            sheet_data: シート全体のデータ
                       
        Returns:
            処理対象行のインデックスリスト（0ベース）
        """
        logger.info(f"🔍 処理対象行を検索開始 - データ行数: {len(sheet_data)}")
        
        process_rows = []
        expected_number = 1
        
        for row_idx, row_data in enumerate(sheet_data):
            # A列が存在するかチェック
            if len(row_data) == 0:
                logger.debug(f"行 {row_idx + 1}: A列が存在しません（空行） - 処理を終了")
                break
                
            a_cell_value = str(row_data[0]).strip()
            
            # 空白の場合は処理終了
            if not a_cell_value:
                logger.info(f"📍 行 {row_idx + 1}: A列が空白 - 処理対象行検索を終了")
                break
                
            # 数値として解釈可能かチェック
            try:
                cell_number = int(a_cell_value)
            except ValueError:
                logger.debug(f"行 {row_idx + 1}: A列の値'{a_cell_value}'は数値ではありません - スキップ")
                continue
                
            # 期待する連番かチェック
            if cell_number == expected_number:
                process_rows.append(row_idx)
                logger.debug(f"✅ 行 {row_idx + 1}: 処理対象行 - A列の値: {cell_number}")
                expected_number += 1
            else:
                logger.debug(f"行 {row_idx + 1}: A列の値{cell_number}は期待値{expected_number}と一致しません - スキップ")
                # 連番が途切れても処理を継続（要件に応じて変更可能）
                
        logger.info(f"🎯 処理対象行検索完了 - 見つかった行数: {len(process_rows)}")
        if process_rows:
            start_row = process_rows[0] + 1
            end_row = process_rows[-1] + 1
            logger.info(f"📋 処理対象範囲: {start_row}行目〜{end_row}行目")
            
            # 構造情報を更新
            if self.sheet_structure is None:
                self.sheet_structure = {}
            self.sheet_structure['process_rows'] = process_rows
            
        else:
            logger.warning("❌ 処理対象行が見つかりませんでした。A列に1から始まる連番があることを確認してください")
            
        return process_rows
    
    # === 拡張機能 ===
    
    def analyze_sheet_structure(self, sheet_data: List[List[str]]) -> Dict:
        """
        シート構造を包括的に解析
        
        Args:
            sheet_data: シートデータ
            
        Returns:
            解析結果の辞書
        """
        logger.info("🔬 シート構造の包括的解析を開始")
        
        analysis_result = {
            'sheet_dimensions': {
                'rows': len(sheet_data),
                'columns': max(len(row) for row in sheet_data) if sheet_data else 0
            },
            'work_instruction_row': -1,
            'copy_columns': [],
            'process_rows': [],
            'column_mappings': [],
            'validation_errors': []
        }
        
        # 作業指示行を検索
        work_row = self.find_work_instruction_row(sheet_data)
        analysis_result['work_instruction_row'] = work_row
        
        if work_row != -1:
            # コピー列を検索
            header_row = sheet_data[work_row]
            copy_columns = self.find_copy_columns(header_row)
            analysis_result['copy_columns'] = copy_columns
            
            # 列マッピングを作成
            self.column_mappings = []
            for copy_col in copy_columns:
                related_cols = self.calculate_related_columns(copy_col)
                mapping = ColumnMapping(
                    copy_column=copy_col,
                    process_column=related_cols['process_col'],
                    error_column=related_cols['error_col'],
                    paste_column=related_cols['paste_col']
                )
                self.column_mappings.append(mapping)
                analysis_result['column_mappings'].append({
                    'copy_column': copy_col,
                    'column_letters': mapping.column_letters,
                    'is_valid': mapping.is_valid
                })
            
            # 処理対象行を取得
            process_rows = self.get_process_rows(sheet_data)
            analysis_result['process_rows'] = process_rows
            
            # 構造情報を保存
            self.sheet_structure = analysis_result
            
        logger.info(f"✅ シート構造解析完了: {analysis_result['sheet_dimensions']} | "
                   f"コピー列: {len(analysis_result['copy_columns'])} | "
                   f"処理対象行: {len(analysis_result['process_rows'])}")
        
        return analysis_result
    
    def create_processing_tasks(self, sheet_data: List[List[str]]) -> List[ProcessingTask]:
        """
        処理タスクを作成
        
        Args:
            sheet_data: シートデータ
            
        Returns:
            処理タスクのリスト
        """
        logger.info("📋 処理タスクを作成開始")
        
        if not self.sheet_structure:
            logger.warning("⚠️ シート構造が解析されていません。先に analyze_sheet_structure を実行してください")
            return []
        
        tasks = []
        copy_columns = self.sheet_structure.get('copy_columns', [])
        process_rows = self.sheet_structure.get('process_rows', [])
        
        for row_idx in process_rows:
            for copy_col in copy_columns:
                # コピー対象テキストを取得
                copy_text = ""
                if (row_idx < len(sheet_data) and 
                    copy_col < len(sheet_data[row_idx])):
                    copy_text = str(sheet_data[row_idx][copy_col]).strip()
                
                # 空のセルをスキップするかチェック
                if (self.options['skip_empty_cells'] and not copy_text):
                    logger.debug(f"⏭️ 空セルをスキップ: 行{row_idx + 1} 列{self._index_to_column_letter(copy_col)}")
                    continue
                
                task = ProcessingTask(
                    row_index=row_idx,
                    copy_column=copy_col,
                    copy_text=copy_text
                )
                tasks.append(task)
        
        self.processing_tasks = tasks
        
        # 進捗情報を初期化
        self.processing_progress = ProcessingProgress(total_tasks=len(tasks))
        
        logger.info(f"✅ 処理タスク作成完了: {len(tasks)}タスク")
        return tasks
    
    def update_task_status(self, row_idx: int, copy_col: int, 
                          status: ProcessingStatus, error_message: str = "") -> bool:
        """
        タスクの状態を更新
        
        Args:
            row_idx: 行インデックス
            copy_col: コピー列インデックス
            status: 新しい状態
            error_message: エラーメッセージ（エラー時）
            
        Returns:
            更新成功時はTrue
        """
        task = self._find_task(row_idx, copy_col)
        if not task:
            logger.warning(f"⚠️ タスクが見つかりません: 行{row_idx + 1} 列{self._index_to_column_letter(copy_col)}")
            return False
        
        old_status = task.status
        task.status = status
        task.error_message = error_message
        
        # 進捗を更新
        self._update_progress(old_status, status)
        
        logger.debug(f"📊 タスク状態更新: 行{row_idx + 1} 列{self._index_to_column_letter(copy_col)} "
                    f"{old_status.value} → {status.value}")
        
        return True
    
    def get_processing_progress(self) -> ProcessingProgress:
        """現在の処理進捗を取得"""
        return self.processing_progress
    
    def get_unprocessed_tasks(self) -> List[ProcessingTask]:
        """未処理タスクを取得"""
        return [task for task in self.processing_tasks 
                if task.status == ProcessingStatus.UNPROCESSED]
    
    def get_failed_tasks(self) -> List[ProcessingTask]:
        """失敗タスクを取得"""
        return [task for task in self.processing_tasks 
                if task.status == ProcessingStatus.ERROR]
    
    def reset_tasks(self, reset_errors_only: bool = False):
        """
        タスクをリセット
        
        Args:
            reset_errors_only: Trueの場合はエラータスクのみリセット
        """
        reset_count = 0
        for task in self.processing_tasks:
            if not reset_errors_only or task.status == ProcessingStatus.ERROR:
                old_status = task.status
                task.status = ProcessingStatus.UNPROCESSED
                task.error_message = ""
                
                # 進捗を更新
                self._update_progress(old_status, ProcessingStatus.UNPROCESSED)
                reset_count += 1
        
        logger.info(f"🔄 タスクリセット完了: {reset_count}タスク")
    
    def get_column_mapping(self, copy_col: int) -> Optional[ColumnMapping]:
        """指定されたコピー列の列マッピングを取得"""
        for mapping in self.column_mappings:
            if mapping.copy_column == copy_col:
                return mapping
        return None
    
    def export_processing_summary(self) -> Dict:
        """処理サマリーをエクスポート"""
        summary = {
            'processing_progress': {
                'total_tasks': self.processing_progress.total_tasks,
                'completion_percentage': self.processing_progress.completion_percentage,
                'success_rate': self.processing_progress.success_rate,
                'successful_tasks': self.processing_progress.successful_tasks,
                'failed_tasks': self.processing_progress.failed_tasks,
                'skipped_tasks': self.processing_progress.skipped_tasks
            },
            'sheet_structure': self.sheet_structure,
            'column_mappings': [
                {
                    'copy_column': mapping.copy_column,
                    'column_letters': mapping.column_letters,
                    'is_valid': mapping.is_valid
                }
                for mapping in self.column_mappings
            ],
            'failed_tasks_detail': [
                {
                    'row_number': task.row_number,
                    'copy_column_letter': task.copy_column_letter,
                    'copy_text': task.copy_text[:100] + "..." if len(task.copy_text) > 100 else task.copy_text,
                    'error_message': task.error_message
                }
                for task in self.get_failed_tasks()
            ]
        }
        
        logger.info("📊 処理サマリーをエクスポートしました")
        return summary
    
    # === プライベートメソッド ===
    
    def _find_task(self, row_idx: int, copy_col: int) -> Optional[ProcessingTask]:
        """指定された行・列のタスクを検索"""
        for task in self.processing_tasks:
            if task.row_index == row_idx and task.copy_column == copy_col:
                return task
        return None
    
    def _update_progress(self, old_status: ProcessingStatus, new_status: ProcessingStatus):
        """進捗情報を更新"""
        # 古い状態のカウントを減算
        if old_status == ProcessingStatus.PROCESSED:
            self.processing_progress.successful_tasks -= 1
            self.processing_progress.completed_tasks -= 1
        elif old_status == ProcessingStatus.ERROR:
            self.processing_progress.failed_tasks -= 1
            self.processing_progress.completed_tasks -= 1
        elif old_status == ProcessingStatus.SKIPPED:
            self.processing_progress.skipped_tasks -= 1
            self.processing_progress.completed_tasks -= 1
        
        # 新しい状態のカウントを加算
        if new_status == ProcessingStatus.PROCESSED:
            self.processing_progress.successful_tasks += 1
            self.processing_progress.completed_tasks += 1
        elif new_status == ProcessingStatus.ERROR:
            self.processing_progress.failed_tasks += 1
            self.processing_progress.completed_tasks += 1
        elif new_status == ProcessingStatus.SKIPPED:
            self.processing_progress.skipped_tasks += 1
            self.processing_progress.completed_tasks += 1
    
    def _index_to_column_letter(self, col_idx: int) -> str:
        """列インデックス（0ベース）をExcel形式の列文字（A, B, C...）に変換"""
        return self._static_index_to_column_letter(col_idx)
    
    @staticmethod
    def _static_index_to_column_letter(col_idx: int) -> str:
        """静的メソッド版の列文字変換"""
        if col_idx < 0:
            return f"無効列({col_idx})"
            
        result = ""
        while col_idx >= 0:
            result = chr(col_idx % 26 + ord('A')) + result
            col_idx = col_idx // 26 - 1
        return result