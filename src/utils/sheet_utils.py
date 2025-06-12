"""
スプレッドシート操作に関するユーティリティ関数

このモジュールは以下の機能を提供します：
1. スプレッドシートURLからIDを抽出
2. セル範囲の検証と正規化
3. データ型の変換とバリデーション
4. 一般的なスプレッドシート操作のヘルパー関数

初心者向け解説：
- URLからスプレッドシートIDを自動抽出
- エラーを防ぐためのデータ検証機能
- 繰り返し使用される処理を関数化
"""

import re
from typing import List, Dict, Optional, Tuple, Union
from urllib.parse import urlparse, parse_qs
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SheetUtils:
    """スプレッドシート操作のユーティリティクラス"""
    
    @staticmethod
    def extract_spreadsheet_id(url: str) -> Optional[str]:
        """
        スプレッドシートURLからIDを抽出
        
        対応URL形式:
        - https://docs.google.com/spreadsheets/d/{ID}/edit#gid=0
        - https://docs.google.com/spreadsheets/d/{ID}/edit
        - https://docs.google.com/spreadsheets/d/{ID}
        
        Args:
            url: GoogleスプレッドシートのURL
            
        Returns:
            スプレッドシートID（44文字）、抽出できない場合はNone
            
        例:
            >>> url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
            >>> SheetUtils.extract_spreadsheet_id(url)
            "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        """
        if not url or not isinstance(url, str):
            logger.warning("⚠️ URLが無効です（空またはNone）")
            return None
            
        logger.debug(f"🔍 スプレッドシートID抽出開始: {url}")
        
        # 正規表現パターン：/d/ の後から次の / または文字列終端まで
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        
        if match:
            spreadsheet_id = match.group(1)
            logger.info(f"✅ スプレッドシートID抽出成功: {spreadsheet_id}")
            return spreadsheet_id
        else:
            logger.error(f"❌ スプレッドシートIDの抽出に失敗: {url}")
            return None
    
    @staticmethod
    def validate_spreadsheet_id(spreadsheet_id: str) -> bool:
        """
        スプレッドシートIDの形式を検証
        
        Args:
            spreadsheet_id: 検証するID
            
        Returns:
            有効な場合はTrue、無効な場合はFalse
            
        検証条件:
        - 文字列である
        - 長さが30文字以上60文字以下
        - 英数字とハイフン、アンダースコアのみ
        """
        if not isinstance(spreadsheet_id, str):
            logger.warning("⚠️ スプレッドシートIDが文字列ではありません")
            return False
            
        if len(spreadsheet_id) < 30 or len(spreadsheet_id) > 60:
            logger.warning(f"⚠️ スプレッドシートIDの長さが不正: {len(spreadsheet_id)}文字")
            return False
            
        # 英数字、ハイフン、アンダースコアのみ許可
        if not re.match(r'^[a-zA-Z0-9-_]+$', spreadsheet_id):
            logger.warning("⚠️ スプレッドシートIDに無効な文字が含まれています")
            return False
            
        logger.debug(f"✅ スプレッドシートID検証成功: {spreadsheet_id}")
        return True
    
    @staticmethod
    def normalize_sheet_data(raw_data: List[List]) -> List[List[str]]:
        """
        生のシートデータを正規化
        
        処理内容:
        1. 全セルを文字列に変換
        2. None や空要素を空文字に変換
        3. 全行を同じ列数に統一（不足分は空文字で埋める）
        
        Args:
            raw_data: Google Sheets APIから取得した生データ
            
        Returns:
            正規化されたデータ（文字列の2次元リスト）
            
        例:
            >>> raw_data = [['A', 'B'], [1, 2, 3], ['X']]
            >>> SheetUtils.normalize_sheet_data(raw_data)
            [['A', 'B', ''], ['1', '2', '3'], ['X', '', '']]
        """
        if not raw_data:
            logger.debug("📝 データが空です")
            return []
            
        logger.debug(f"🔄 データ正規化開始: {len(raw_data)}行")
        
        # 最大列数を取得
        max_cols = max(len(row) for row in raw_data) if raw_data else 0
        
        normalized_data = []
        for row_idx, row in enumerate(raw_data):
            normalized_row = []
            
            # 既存のセルを文字列に変換
            for cell in row:
                if cell is None:
                    normalized_row.append('')
                else:
                    normalized_row.append(str(cell))
            
            # 不足している列を空文字で埋める
            while len(normalized_row) < max_cols:
                normalized_row.append('')
                
            normalized_data.append(normalized_row)
            
        logger.debug(f"✅ データ正規化完了: {len(normalized_data)}行 x {max_cols}列")
        return normalized_data
    
    @staticmethod
    def find_header_row_by_marker(sheet_data: List[List[str]], marker: str, search_column: int = 0) -> int:
        """
        特定のマーカーを含む行を検索
        
        Args:
            sheet_data: シートデータ
            marker: 検索するマーカー文字列
            search_column: 検索対象の列インデックス（デフォルト: 0 = A列）
            
        Returns:
            マーカーが見つかった行のインデックス（0ベース）、見つからない場合は-1
            
        例:
            >>> data = [['', ''], ['作業指示行', 'コピー'], ['1', 'データ']]
            >>> SheetUtils.find_header_row_by_marker(data, '作業指示行', 0)
            1
        """
        logger.debug(f"🔍 ヘッダー行検索: マーカー='{marker}', 列={search_column}")
        
        for row_idx, row in enumerate(sheet_data):
            if len(row) > search_column:
                cell_value = str(row[search_column]).strip()
                if cell_value == marker:
                    logger.debug(f"✅ ヘッダー行発見: {row_idx}行目")
                    return row_idx
                    
        logger.debug(f"❌ ヘッダー行が見つかりません: マーカー='{marker}'")
        return -1
    
    @staticmethod
    def validate_column_boundaries(sheet_data: List[List[str]], required_columns: List[int]) -> Dict[str, bool]:
        """
        必要な列が境界内に存在するかを検証
        
        Args:
            sheet_data: シートデータ
            required_columns: 必要な列インデックスのリスト
            
        Returns:
            検証結果の辞書 {'valid': bool, 'max_col': int, 'invalid_cols': List[int]}
            
        例:
            >>> data = [['A', 'B', 'C']]
            >>> SheetUtils.validate_column_boundaries(data, [0, 1, 5])
            {'valid': False, 'max_col': 2, 'invalid_cols': [5]}
        """
        if not sheet_data:
            return {'valid': False, 'max_col': -1, 'invalid_cols': required_columns}
            
        max_col = max(len(row) for row in sheet_data) - 1 if sheet_data else -1
        invalid_cols = [col for col in required_columns if col < 0 or col > max_col]
        
        result = {
            'valid': len(invalid_cols) == 0,
            'max_col': max_col,
            'invalid_cols': invalid_cols
        }
        
        if invalid_cols:
            logger.warning(f"⚠️ 境界外の列が検出されました: {invalid_cols} (最大列: {max_col})")
        else:
            logger.debug(f"✅ 全列が境界内です: {required_columns}")
            
        return result
    
    @staticmethod
    def create_range_notation(sheet_name: str, start_row: int, start_col: int, 
                            end_row: Optional[int] = None, end_col: Optional[int] = None) -> str:
        """
        A1記法の範囲文字列を作成
        
        Args:
            sheet_name: シート名
            start_row: 開始行（0ベース）
            start_col: 開始列（0ベース）
            end_row: 終了行（0ベース）、Noneの場合は単一セル
            end_col: 終了列（0ベース）、Noneの場合は単一セル
            
        Returns:
            A1記法の範囲文字列
            
        例:
            >>> SheetUtils.create_range_notation("Sheet1", 0, 0, 2, 2)
            "Sheet1!A1:C3"
            >>> SheetUtils.create_range_notation("Sheet1", 0, 0)
            "Sheet1!A1"
        """
        start_cell = SheetUtils.index_to_a1_notation(start_row, start_col)
        
        if end_row is not None and end_col is not None:
            end_cell = SheetUtils.index_to_a1_notation(end_row, end_col)
            range_notation = f"{sheet_name}!{start_cell}:{end_cell}"
        else:
            range_notation = f"{sheet_name}!{start_cell}"
            
        logger.debug(f"📍 範囲記法作成: {range_notation}")
        return range_notation
    
    @staticmethod
    def index_to_a1_notation(row: int, col: int) -> str:
        """
        行・列インデックスをA1記法に変換
        
        Args:
            row: 行インデックス（0ベース）
            col: 列インデックス（0ベース）
            
        Returns:
            A1記法の文字列
        """
        col_letter = SheetUtils.index_to_column_letter(col)
        return f"{col_letter}{row + 1}"
    
    @staticmethod
    def index_to_column_letter(col_idx: int) -> str:
        """
        列インデックスを列文字に変換
        
        Args:
            col_idx: 列インデックス（0ベース）
            
        Returns:
            列文字（A, B, C, ..., Z, AA, AB, ...）
        """
        if col_idx < 0:
            return f"無効列({col_idx})"
            
        result = ""
        while col_idx >= 0:
            result = chr(col_idx % 26 + ord('A')) + result
            col_idx = col_idx // 26 - 1
        return result
    
    @staticmethod
    def a1_notation_to_index(a1_notation: str) -> Tuple[int, int]:
        """
        A1記法を行・列インデックスに変換
        
        Args:
            a1_notation: A1記法の文字列（例: "A1", "Z5", "AA10"）
            
        Returns:
            (行インデックス, 列インデックス) のタプル（0ベース）
            
        例:
            >>> SheetUtils.a1_notation_to_index("A1")
            (0, 0)
            >>> SheetUtils.a1_notation_to_index("B5")
            (4, 1)
        """
        # 列文字と行番号を分離
        match = re.match(r'^([A-Z]+)(\d+)$', a1_notation.upper())
        if not match:
            raise ValueError(f"無効なA1記法: {a1_notation}")
            
        col_letters = match.group(1)
        row_number = int(match.group(2))
        
        # 列文字を列インデックスに変換
        col_idx = 0
        for i, letter in enumerate(reversed(col_letters)):
            col_idx += (ord(letter) - ord('A') + 1) * (26 ** i)
        col_idx -= 1  # 0ベースに調整
        
        row_idx = row_number - 1  # 0ベースに調整
        
        return (row_idx, col_idx)
    
    @staticmethod
    def is_valid_sheet_name(sheet_name: str) -> bool:
        """
        シート名の有効性を検証
        
        Args:
            sheet_name: 検証するシート名
            
        Returns:
            有効な場合はTrue
            
        無効な条件:
        - 空文字列
        - 100文字を超える
        - 無効な文字（: / ? * [ ] など）を含む
        """
        if not sheet_name or not isinstance(sheet_name, str):
            return False
            
        if len(sheet_name) > 100:
            return False
            
        # Googleスプレッドシートで無効な文字
        invalid_chars = [':', '/', '?', '*', '[', ']']
        if any(char in sheet_name for char in invalid_chars):
            return False
            
        return True