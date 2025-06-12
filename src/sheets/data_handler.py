"""
スプレッドシートのデータ読み書きを担当するハンドラー

このモジュールは以下の機能を提供します：
1. 個別セルの読み取り・書き込み
2. 複数セルの一括更新（API呼び出し削減）
3. シート全体のデータ取得
4. API制限対策（1分100リクエスト制限への対応）

初心者向け解説：
- GoogleSheetsClientをラップして、より使いやすいインターフェースを提供
- リトライ機能付きでエラーに強い設計
- バッチ処理でAPI効率を最大化
- セル位置の計算を自動化（A1形式への変換など）
"""

from typing import List, Dict, Optional, Tuple
import time
import logging
from src.sheets.client import GoogleSheetsClient
from src.interfaces.sheet_interface import ISheetHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataHandler(ISheetHandler):
    """
    スプレッドシートのデータ操作を担当するクラス
    
    使用例:
        handler = DataHandler()
        # 単一セル読み取り
        value = handler.read_cell(sheet_id, "Sheet1", 0, 0)  # A1セル
        # 単一セル書き込み
        handler.write_cell(sheet_id, "Sheet1", 0, 1, "新しい値")  # B1セル
        # 一括更新
        updates = [{"range": "A1", "values": [["値1"]]}, {"range": "B1", "values": [["値2"]]}]
        handler.batch_update(sheet_id, updates)
    
    注意事項:
        - 全ての行・列インデックスは0ベース
        - API制限（1分100リクエスト）を考慮した実装
        - エラー時は詳細なログでデバッグを支援
    """
    
    def __init__(self):
        """データハンドラーを初期化"""
        logger.info("📊 DataHandler を初期化しました")
        self.client = GoogleSheetsClient()
        self.api_call_count = 0
        self.last_api_call_time = 0
        self.api_limit_per_minute = 90  # 安全マージンを考慮して90リクエスト/分
        
    def read_cell(self, sheet_id: str, sheet_name: str, row: int, col: int) -> str:
        """
        指定されたセルの値を読み取り
        
        Args:
            sheet_id: スプレッドシートID
            sheet_name: シート名
            row: 行インデックス（0ベース）
            col: 列インデックス（0ベース）
            
        Returns:
            セルの値（文字列）。空の場合は空文字列
            
        例:
            >>> handler.read_cell("abc123", "Sheet1", 0, 0)
            "セルA1の値"
        """
        cell_address = self._index_to_a1_notation(row, col)
        range_name = f"{sheet_name}!{cell_address}"
        
        logger.debug(f"📖 セル読み取り開始: {range_name}")
        
        try:
            self._check_api_limit()
            values = self.client.read_range(sheet_id, range_name)
            
            if values and len(values) > 0 and len(values[0]) > 0:
                cell_value = str(values[0][0])
                logger.debug(f"✅ セル値取得成功: {range_name} = '{cell_value}'")
                return cell_value
            else:
                logger.debug(f"📝 セルは空です: {range_name}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ セル読み取り失敗: {range_name} - エラー: {e}")
            raise
    
    def write_cell(self, sheet_id: str, sheet_name: str, row: int, col: int, value: str) -> bool:
        """
        指定されたセルに値を書き込み
        
        Args:
            sheet_id: スプレッドシートID
            sheet_name: シート名
            row: 行インデックス（0ベース）
            col: 列インデックス（0ベース）
            value: 書き込む値
            
        Returns:
            成功時はTrue、失敗時はFalse
            
        例:
            >>> handler.write_cell("abc123", "Sheet1", 0, 1, "新しい値")
            True
        """
        cell_address = self._index_to_a1_notation(row, col)
        range_name = f"{sheet_name}!{cell_address}"
        
        logger.debug(f"✏️ セル書き込み開始: {range_name} = '{value}'")
        
        try:
            self._check_api_limit()
            result = self.client.write_value(sheet_id, range_name, value)
            
            if result:
                logger.debug(f"✅ セル書き込み成功: {range_name}")
                return True
            else:
                logger.warning(f"⚠️ セル書き込み結果が不明: {range_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ セル書き込み失敗: {range_name} - エラー: {e}")
            return False
    
    def batch_update(self, sheet_id: str, updates: List[Dict]) -> bool:
        """
        複数セルを一括更新（API効率化）
        
        Args:
            sheet_id: スプレッドシートID
            updates: 更新データのリスト
                    形式: [{"range": "Sheet1!A1", "values": [["値1"]]}, ...]
                    
        Returns:
            成功時はTrue、失敗時はFalse
            
        例:
            >>> updates = [
            ...     {"range": "Sheet1!A1", "values": [["値1"]]},
            ...     {"range": "Sheet1!B1", "values": [["値2"]]},
            ...     {"range": "Sheet1!C1", "values": [["値3"]]}
            ... ]
            >>> handler.batch_update("abc123", updates)
            True
        """
        if not updates:
            logger.warning("⚠️ 更新データが空です")
            return True
            
        logger.info(f"📦 バッチ更新開始: {len(updates)}件の更新")
        
        try:
            self._check_api_limit()
            result = self.client.batch_update(sheet_id, updates)
            
            if result:
                logger.info(f"✅ バッチ更新成功: {len(updates)}件")
                return True
            else:
                logger.warning(f"⚠️ バッチ更新結果が不明: {len(updates)}件")
                return False
                
        except Exception as e:
            logger.error(f"❌ バッチ更新失敗: {len(updates)}件 - エラー: {e}")
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
            
        例:
            >>> data = handler.get_sheet_data("abc123", "Sheet1")
            [["ヘッダー1", "ヘッダー2"], ["データ1", "データ2"]]
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
            raise
    
    def create_batch_update_data(self, sheet_name: str, row_col_value_list: List[Tuple[int, int, str]]) -> List[Dict]:
        """
        バッチ更新用のデータ構造を作成
        
        Args:
            sheet_name: シート名
            row_col_value_list: (行, 列, 値) のタプルリスト
                               例: [(0, 0, "値1"), (0, 1, "値2"), (1, 0, "値3")]
                               
        Returns:
            バッチ更新用のデータリスト
            
        例:
            >>> updates = handler.create_batch_update_data("Sheet1", [
            ...     (0, 0, "A1の値"),
            ...     (0, 1, "B1の値"),
            ...     (1, 0, "A2の値")
            ... ])
            >>> handler.batch_update(sheet_id, updates)
        """
        logger.debug(f"📦 バッチ更新データ作成: {len(row_col_value_list)}件")
        
        updates = []
        for row, col, value in row_col_value_list:
            cell_address = self._index_to_a1_notation(row, col)
            range_name = f"{sheet_name}!{cell_address}"
            
            update_data = {
                "range": range_name,
                "values": [[str(value)]]
            }
            updates.append(update_data)
            
        logger.debug(f"✅ バッチ更新データ作成完了: {len(updates)}件")
        return updates
    
    def _check_api_limit(self):
        """
        API制限をチェックし、必要に応じて待機
        
        Google Sheets APIは100リクエスト/分の制限があるため、
        安全マージンを考慮して90リクエスト/分で制御
        """
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
    
    def _index_to_a1_notation(self, row: int, col: int) -> str:
        """
        行・列インデックス（0ベース）をA1記法に変換
        
        Args:
            row: 行インデックス（0ベース）
            col: 列インデックス（0ベース）
            
        Returns:
            A1記法の文字列（例: "A1", "B5", "AA10"）
            
        例:
            >>> self._index_to_a1_notation(0, 0)
            "A1"
            >>> self._index_to_a1_notation(4, 25)
            "Z5"
        """
        col_letter = self._index_to_column_letter(col)
        return f"{col_letter}{row + 1}"
    
    def _index_to_column_letter(self, col_idx: int) -> str:
        """
        列インデックス（0ベース）をExcel形式の列文字（A, B, C...）に変換
        
        Args:
            col_idx: 列インデックス（0=A, 1=B, 2=C, ...）
            
        Returns:
            列文字（A, B, C, ..., Z, AA, AB, ...）
            
        例:
            >>> self._index_to_column_letter(0)
            'A'
            >>> self._index_to_column_letter(25)
            'Z'
            >>> self._index_to_column_letter(26)
            'AA'
        """
        if col_idx < 0:
            return f"無効列({col_idx})"
            
        result = ""
        while col_idx >= 0:
            result = chr(col_idx % 26 + ord('A')) + result
            col_idx = col_idx // 26 - 1
        return result