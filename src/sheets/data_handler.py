"""
スプレッドシートのデータ読み書きを担当するハンドラー（Day 2-3拡張版）

このモジュールは以下の機能を提供します：
1. 個別セルの読み取り・書き込み
2. 複数セルの一括更新（API呼び出し削減）
3. トランザクション処理（途中エラー時の整合性保持）
4. 処理状態管理（未処理/処理中/処理済み/エラー）
5. API制限対策（1分100リクエスト制限への対応）

初心者向け解説：
- GoogleSheetsClientをラップして、より使いやすいインターフェースを提供
- リトライ機能付きでエラーに強い設計
- バッチ処理でAPI効率を最大化
- トランザクション機能で途中でエラーが発生しても整合性を保つ
- セル位置の計算を自動化（A1形式への変換など）
"""

from typing import List, Dict, Optional, Tuple, Set
import time
import json
import logging
from dataclasses import dataclass
from enum import Enum

from src.sheets.client import GoogleSheetsClient
from src.interfaces.sheet_interface import ISheetHandler
from src.utils.logger import get_logger
from src.utils.retry_handler import retry_on_api_error, ErrorCollector

logger = get_logger(__name__)


class ProcessingStatus(Enum):
    """処理状態の定義"""
    UNPROCESSED = "未処理"
    PROCESSING = "処理中"
    PROCESSED = "処理済み"
    ERROR = "エラー"
    SKIPPED = "スキップ"


@dataclass
class CellUpdate:
    """セル更新情報のデータクラス"""
    row: int
    col: int
    value: str
    original_value: str = ""
    
    @property
    def cell_address(self) -> str:
        """A1記法でのセルアドレス"""
        return DataHandler._static_index_to_a1_notation(self.row, self.col)


@dataclass
class TransactionLog:
    """トランザクションログのデータクラス"""
    transaction_id: str
    updates: List[CellUpdate]
    timestamp: float
    status: str = "pending"
    error_message: str = ""
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'transaction_id': self.transaction_id,
            'updates': [
                {
                    'row': update.row,
                    'col': update.col,
                    'value': update.value,
                    'original_value': update.original_value
                }
                for update in self.updates
            ],
            'timestamp': self.timestamp,
            'status': self.status,
            'error_message': self.error_message
        }


class DataHandler(ISheetHandler):
    """
    スプレッドシートのデータ操作を担当するクラス（拡張版）
    
    使用例:
        handler = DataHandler()
        
        # トランザクション処理
        with handler.transaction() as tx:
            tx.write_cell(sheet_id, "Sheet1", 0, 0, "値1")
            tx.write_cell(sheet_id, "Sheet1", 0, 1, "値2")
        
        # バッチ処理
        updates = [(0, 0, "A1"), (0, 1, "B1"), (1, 0, "A2")]
        handler.batch_write_cells(sheet_id, "Sheet1", updates)
        
        # 処理状態管理
        handler.update_processing_status(sheet_id, "Sheet1", 5, 2, ProcessingStatus.PROCESSED)
    
    注意事項:
        - 全ての行・列インデックスは0ベース
        - API制限（1分100リクエスト）を考慮した実装
        - エラー時は詳細なログでデバッグを支援
        - トランザクション機能で途中エラー時の整合性を保持
    """
    
    def __init__(self):
        """データハンドラーを初期化"""
        logger.info("📊 DataHandler（拡張版）を初期化しました")
        self.client = GoogleSheetsClient()
        self.error_collector = ErrorCollector()
        
        # API制限管理
        self.api_call_count = 0
        self.last_api_call_time = 0
        self.api_limit_per_minute = 90  # 安全マージンを考慮して90リクエスト/分
        
        # トランザクション管理
        self.transaction_logs: List[TransactionLog] = []
        self.current_transaction: Optional['TransactionContext'] = None
        
        # キャッシュ機能
        self.cell_cache: Dict[str, str] = {}
        self.cache_enabled = True
        
    # === ISheetHandler インターフェース実装 ===
    
    def read_cell(self, sheet_id: str, sheet_name: str, row: int, col: int) -> str:
        """
        指定されたセルの値を読み取り（キャッシュ対応）
        
        Args:
            sheet_id: スプレッドシートID
            sheet_name: シート名
            row: 行インデックス（0ベース）
            col: 列インデックス（0ベース）
            
        Returns:
            セルの値（文字列）。空の場合は空文字列
        """
        cache_key = f"{sheet_id}:{sheet_name}:{row}:{col}"
        
        # キャッシュから取得を試行
        if self.cache_enabled and cache_key in self.cell_cache:
            logger.debug(f"📖 キャッシュからセル取得: {self._index_to_a1_notation(row, col)}")
            return self.cell_cache[cache_key]
        
        cell_address = self._index_to_a1_notation(row, col)
        range_name = f"{sheet_name}!{cell_address}"
        
        logger.debug(f"📖 セル読み取り開始: {range_name}")
        
        try:
            self._check_api_limit()
            values = self.client.read_range(sheet_id, range_name)
            
            if values and len(values) > 0 and len(values[0]) > 0:
                cell_value = str(values[0][0])
                
                # キャッシュに保存
                if self.cache_enabled:
                    self.cell_cache[cache_key] = cell_value
                
                logger.debug(f"✅ セル値取得成功: {range_name} = '{cell_value}'")
                return cell_value
            else:
                empty_value = ""
                if self.cache_enabled:
                    self.cell_cache[cache_key] = empty_value
                
                logger.debug(f"📝 セルは空です: {range_name}")
                return empty_value
                
        except Exception as e:
            logger.error(f"❌ セル読み取り失敗: {range_name} - エラー: {e}")
            self.error_collector.add_error(f"セル読み取り {range_name}", e)
            raise
    
    def write_cell(self, sheet_id: str, sheet_name: str, row: int, col: int, value: str) -> bool:
        """
        指定されたセルに値を書き込み（トランザクション対応）
        
        Args:
            sheet_id: スプレッドシートID
            sheet_name: シート名
            row: 行インデックス（0ベース）
            col: 列インデックス（0ベース）
            value: 書き込む値
            
        Returns:
            成功時はTrue、失敗時はFalse
        """
        # トランザクション中の場合は記録のみ
        if self.current_transaction:
            self.current_transaction.add_update(row, col, value)
            return True
        
        return self._execute_cell_write(sheet_id, sheet_name, row, col, value)
    
    def batch_update(self, sheet_id: str, updates: List[Dict]) -> bool:
        """
        複数セルを一括更新（API効率化）
        
        Args:
            sheet_id: スプレッドシートID
            updates: 更新データのリスト
                    形式: [{"range": "Sheet1!A1", "values": [["値1"]]}, ...]
                    
        Returns:
            成功時はTrue、失敗時はFalse
        """
        if not updates:
            logger.warning("⚠️ 更新データが空です")
            return True
            
        logger.info(f"📦 バッチ更新開始: {len(updates)}件の更新")
        
        try:
            self._check_api_limit()
            result = self.client.batch_update(sheet_id, updates)
            
            if result:
                # キャッシュを無効化
                self._invalidate_cache()
                logger.info(f"✅ バッチ更新成功: {len(updates)}件")
                return True
            else:
                logger.warning(f"⚠️ バッチ更新結果が不明: {len(updates)}件")
                return False
                
        except Exception as e:
            logger.error(f"❌ バッチ更新失敗: {len(updates)}件 - エラー: {e}")
            self.error_collector.add_error(f"バッチ更新 {len(updates)}件", e)
            return False
    
    def get_sheet_data(self, sheet_id: str, sheet_name: str, max_rows: int = 1000, max_cols: int = 26) -> List[List[str]]:
        """
        シート全体のデータを取得
        
        Args:
            sheet_id: スプレッドシートID
            sheet_name: シート名
            max_rows: 最大読み取り行数（デフォルト: 1000）
            max_cols: 最大読み取り列数（デフォルト: 26、Z列まで）
            
        Returns:
            シートデータの2次元リスト
        """
        end_col_letter = self._index_to_column_letter(max_cols - 1)
        range_name = f"{sheet_name}!A1:{end_col_letter}{max_rows}"
        
        logger.info(f"📊 シートデータ取得開始: {range_name}")
        
        try:
            self._check_api_limit()
            values = self.client.read_range(sheet_id, range_name)
            
            # データを正規化（すべての行を同じ列数にする）
            if values:
                max_len = max(len(row) for row in values) if values else 0
                normalized_data = []
                
                for row in values:
                    # 不足している列を空文字で埋める
                    normalized_row = row + [''] * (max_len - len(row))
                    normalized_data.append([str(cell) for cell in normalized_row])
                
                logger.info(f"✅ シートデータ取得成功: {len(normalized_data)}行 x {max_len}列")
                return normalized_data
            else:
                logger.info("📝 シートは空です")
                return []
                
        except Exception as e:
            logger.error(f"❌ シートデータ取得失敗: {range_name} - エラー: {e}")
            self.error_collector.add_error(f"シートデータ取得 {range_name}", e)
            raise
    
    # === 拡張機能 ===
    
    def batch_write_cells(self, sheet_id: str, sheet_name: str, 
                         cell_updates: List[Tuple[int, int, str]]) -> bool:
        """
        複数セルを効率的に一括書き込み
        
        Args:
            sheet_id: スプレッドシートID
            sheet_name: シート名
            cell_updates: (行, 列, 値) のタプルリスト
                         例: [(0, 0, "A1の値"), (0, 1, "B1の値"), (1, 0, "A2の値")]
                         
        Returns:
            成功時はTrue、失敗時はFalse
        """
        if not cell_updates:
            return True
        
        logger.info(f"📝 一括セル書き込み開始: {len(cell_updates)}セル")
        
        # バッチ更新用データを作成
        updates = []
        for row, col, value in cell_updates:
            cell_address = self._index_to_a1_notation(row, col)
            range_name = f"{sheet_name}!{cell_address}"
            
            update_data = {
                "range": range_name,
                "values": [[str(value)]]
            }
            updates.append(update_data)
        
        # バッチ更新を実行
        success = self.batch_update(sheet_id, updates)
        
        if success:
            # キャッシュを更新
            for row, col, value in cell_updates:
                cache_key = f"{sheet_id}:{sheet_name}:{row}:{col}"
                if self.cache_enabled:
                    self.cell_cache[cache_key] = str(value)
        
        return success
    
    def update_processing_status(self, sheet_id: str, sheet_name: str, 
                               row: int, process_col: int, status: ProcessingStatus) -> bool:
        """
        処理状態を更新
        
        Args:
            sheet_id: スプレッドシートID
            sheet_name: シート名
            row: 対象行インデックス
            process_col: 処理状態列のインデックス
            status: 処理状態
            
        Returns:
            成功時はTrue、失敗時はFalse
        """
        if process_col < 0:
            logger.debug(f"⚠️ 処理状態列が無効: {process_col}")
            return False
        
        logger.debug(f"📊 処理状態更新: 行{row + 1} → {status.value}")
        
        return self.write_cell(sheet_id, sheet_name, row, process_col, status.value)
    
    def write_error_info(self, sheet_id: str, sheet_name: str, 
                        row: int, error_col: int, error_message: str) -> bool:
        """
        エラー情報を記録
        
        Args:
            sheet_id: スプレッドシートID
            sheet_name: シート名
            row: 対象行インデックス
            error_col: エラー列のインデックス
            error_message: エラーメッセージ
            
        Returns:
            成功時はTrue、失敗時はFalse
        """
        if error_col < 0:
            logger.debug(f"⚠️ エラー列が無効: {error_col}")
            return False
        
        # エラーメッセージを100文字に制限
        truncated_message = error_message[:100] + "..." if len(error_message) > 100 else error_message
        
        logger.debug(f"📝 エラー情報記録: 行{row + 1} = {truncated_message}")
        
        return self.write_cell(sheet_id, sheet_name, row, error_col, truncated_message)
    
    def transaction(self):
        """
        トランザクションコンテキストマネージャー
        
        使用例:
            with handler.transaction() as tx:
                tx.write_cell(sheet_id, "Sheet1", 0, 0, "値1")
                tx.write_cell(sheet_id, "Sheet1", 0, 1, "値2")
                # ここでエラーが発生すると全ての変更がロールバック
        """
        return TransactionContext(self)
    
    def clear_cache(self):
        """セルキャッシュをクリア"""
        self.cell_cache.clear()
        logger.debug("🗑️ セルキャッシュをクリアしました")
    
    def get_cache_statistics(self) -> Dict[str, int]:
        """キャッシュ統計を取得"""
        return {
            'cache_size': len(self.cell_cache),
            'cache_enabled': self.cache_enabled
        }
    
    # === プライベートメソッド ===
    
    def _execute_cell_write(self, sheet_id: str, sheet_name: str, 
                          row: int, col: int, value: str) -> bool:
        """実際のセル書き込みを実行"""
        cell_address = self._index_to_a1_notation(row, col)
        range_name = f"{sheet_name}!{cell_address}"
        
        logger.debug(f"✏️ セル書き込み開始: {range_name} = '{value}'")
        
        try:
            self._check_api_limit()
            result = self.client.write_value(sheet_id, range_name, value)
            
            if result:
                # キャッシュを更新
                cache_key = f"{sheet_id}:{sheet_name}:{row}:{col}"
                if self.cache_enabled:
                    self.cell_cache[cache_key] = str(value)
                
                logger.debug(f"✅ セル書き込み成功: {range_name}")
                return True
            else:
                logger.warning(f"⚠️ セル書き込み結果が不明: {range_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ セル書き込み失敗: {range_name} - エラー: {e}")
            self.error_collector.add_error(f"セル書き込み {range_name}", e)
            return False
    
    def _check_api_limit(self):
        """API制限をチェックし、必要に応じて待機"""
        current_time = time.time()
        
        # 1分経過したらカウンターをリセット
        if current_time - self.last_api_call_time > 60:
            self.api_call_count = 0
            self.last_api_call_time = current_time
        
        # API制限に近づいている場合は待機
        if self.api_call_count >= self.api_limit_per_minute:
            wait_time = 60 - (current_time - self.last_api_call_time)
            if wait_time > 0:
                logger.warning(f"⏳ API制限に達しました。{wait_time:.1f}秒待機します...")
                time.sleep(wait_time)
                self.api_call_count = 0
                self.last_api_call_time = time.time()
        
        self.api_call_count += 1
        
        if self.api_call_count % 10 == 0:
            logger.debug(f"📊 API呼び出し状況: {self.api_call_count}/{self.api_limit_per_minute}")
    
    def _invalidate_cache(self):
        """キャッシュを無効化"""
        if self.cache_enabled:
            self.cell_cache.clear()
            logger.debug("♻️ キャッシュを無効化しました")
    
    def _index_to_a1_notation(self, row: int, col: int) -> str:
        """行・列インデックス（0ベース）をA1記法に変換"""
        col_letter = self._index_to_column_letter(col)
        return f"{col_letter}{row + 1}"
    
    @staticmethod
    def _static_index_to_a1_notation(row: int, col: int) -> str:
        """静的メソッド版のA1記法変換"""
        col_letter = DataHandler._static_index_to_column_letter(col)
        return f"{col_letter}{row + 1}"
    
    def _index_to_column_letter(self, col_idx: int) -> str:
        """列インデックス（0ベース）をExcel形式の列文字に変換"""
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


class TransactionContext:
    """
    トランザクションコンテキスト
    
    with文で使用してトランザクション処理を実現
    """
    
    def __init__(self, data_handler: DataHandler):
        self.data_handler = data_handler
        self.updates: List[CellUpdate] = []
        self.sheet_id: Optional[str] = None
        self.sheet_name: Optional[str] = None
        self.transaction_id = f"tx_{int(time.time() * 1000)}"
        
    def __enter__(self):
        """トランザクション開始"""
        logger.debug(f"🏁 トランザクション開始: {self.transaction_id}")
        self.data_handler.current_transaction = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """トランザクション終了"""
        try:
            if exc_type is None:
                # 正常終了の場合はコミット
                self._commit()
            else:
                # 例外発生の場合はロールバック
                self._rollback()
                logger.error(f"❌ トランザクションエラー: {exc_val}")
        finally:
            self.data_handler.current_transaction = None
            logger.debug(f"🏁 トランザクション終了: {self.transaction_id}")
    
    def write_cell(self, sheet_id: str, sheet_name: str, row: int, col: int, value: str):
        """トランザクション内でのセル書き込み予約"""
        # 初回の場合はシート情報を保存
        if self.sheet_id is None:
            self.sheet_id = sheet_id
            self.sheet_name = sheet_name
        
        # 元の値を読み取り（ロールバック用）
        original_value = ""
        try:
            original_value = self.data_handler.read_cell(sheet_id, sheet_name, row, col)
        except Exception as e:
            logger.debug(f"⚠️ 元の値の読み取り失敗: {e}")
        
        update = CellUpdate(
            row=row,
            col=col,
            value=value,
            original_value=original_value
        )
        self.updates.append(update)
        
        logger.debug(f"📝 書き込み予約: {update.cell_address} = '{value}'")
    
    def add_update(self, row: int, col: int, value: str):
        """更新を追加（内部使用）"""
        if self.sheet_id and self.sheet_name:
            self.write_cell(self.sheet_id, self.sheet_name, row, col, value)
    
    def _commit(self):
        """変更をコミット"""
        if not self.updates:
            logger.debug("💾 コミット対象なし")
            return
        
        logger.info(f"💾 トランザクションコミット開始: {len(self.updates)}件")
        
        try:
            # バッチ更新でまとめて実行
            cell_updates = [(update.row, update.col, update.value) for update in self.updates]
            success = self.data_handler.batch_write_cells(
                self.sheet_id, self.sheet_name, cell_updates
            )
            
            if success:
                # トランザクションログを記録
                transaction_log = TransactionLog(
                    transaction_id=self.transaction_id,
                    updates=self.updates,
                    timestamp=time.time(),
                    status="committed"
                )
                self.data_handler.transaction_logs.append(transaction_log)
                
                logger.info(f"✅ トランザクションコミット成功: {len(self.updates)}件")
            else:
                raise Exception("バッチ更新に失敗しました")
                
        except Exception as e:
            logger.error(f"❌ トランザクションコミット失敗: {e}")
            self._rollback()
            raise
    
    def _rollback(self):
        """変更をロールバック"""
        logger.warning(f"↩️ トランザクションロールバック: {len(self.updates)}件")
        
        try:
            # 元の値に戻す
            rollback_updates = [
                (update.row, update.col, update.original_value) 
                for update in self.updates
                if update.original_value is not None
            ]
            
            if rollback_updates:
                self.data_handler.batch_write_cells(
                    self.sheet_id, self.sheet_name, rollback_updates
                )
            
            # エラーログを記録
            transaction_log = TransactionLog(
                transaction_id=self.transaction_id,
                updates=self.updates,
                timestamp=time.time(),
                status="rolled_back",
                error_message="トランザクション中にエラーが発生"
            )
            self.data_handler.transaction_logs.append(transaction_log)
            
            logger.info(f"✅ ロールバック完了: {len(rollback_updates)}件")
            
        except Exception as e:
            logger.error(f"❌ ロールバック失敗: {e}")
            # ロールバックに失敗した場合はエラーログのみ記録