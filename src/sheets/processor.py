"""
スプレッドシート処理の核となるプロセッサー

このモジュールは以下の機能を提供します：
1. 作業指示行の検出（A列に「作業指示行」がある行を特定）
2. コピー列の検索（ヘッダー行から「コピー」列を全て検出）
3. 関連列の位置計算（処理列、エラー列、貼り付け列の位置）
4. 処理対象行の取得（A列が連番の行を検出）

初心者向け解説：
- このクラスはGoogleスプレッドシートの構造を解析します
- 「作業指示行」を基準として、どの列でどんな処理をするかを決定します
- エラーが発生した場合は詳細なログを出力して、問題箇所を特定しやすくします
"""

from typing import List, Dict, Optional
import logging
from src.interfaces.sheet_interface import ISheetProcessor
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SpreadsheetProcessor(ISheetProcessor):
    """
    スプレッドシート処理のメインクラス
    
    使用例:
        processor = SpreadsheetProcessor()
        work_row = processor.find_work_instruction_row(sheet_data)
        copy_columns = processor.find_copy_columns(sheet_data[work_row])
        
    注意事項:
        - 全ての列インデックスは0ベースです（A列=0, B列=1, ...）
        - 行インデックスも0ベースです（1行目=0, 2行目=1, ...）
    """
    
    def __init__(self):
        """プロセッサーを初期化"""
        logger.info("📊 SpreadsheetProcessor を初期化しました")
        self.work_instruction_marker = "作業指示行"
        self.copy_column_marker = "コピー"
        
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
            
        例:
            >>> sheet_data = [
            ...     ['', '', ''],
            ...     ['データ1', 'データ2', 'データ3'],
            ...     ['作業指示行', 'コピー', '貼り付け']
            ... ]
            >>> processor.find_work_instruction_row(sheet_data)
            2  # 3行目（0ベースで2）
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
            
        例:
            >>> header_row = ['', '処理', 'エラー', 'コピー', '貼り付け', '', 'コピー', '貼り付け']
            >>> processor.find_copy_columns(header_row)
            [3, 6]  # D列とG列
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
            
        例:
            >>> processor.calculate_related_columns(5)  # F列がコピー列の場合
            {'process_col': 3, 'error_col': 4, 'paste_col': 6}  # D列、E列、G列
            
            >>> processor.calculate_related_columns(1)  # B列がコピー列の場合
            {'process_col': -1, 'error_col': 0, 'paste_col': 2}  # 処理列は無効、エラー列はA列、貼り付け列はC列
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
            
        例:
            >>> sheet_data = [
            ...     ['ヘッダー1', 'ヘッダー2'],
            ...     ['1', 'データ1'],      # 処理対象
            ...     ['2', 'データ2'],      # 処理対象  
            ...     ['3', 'データ3'],      # 処理対象
            ...     ['', 'データ4'],       # 空白で終了
            ...     ['5', 'データ5']       # 処理されない
            ... ]
            >>> processor.get_process_rows(sheet_data)
            [1, 2, 3]  # 2行目〜4行目
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
        else:
            logger.warning("❌ 処理対象行が見つかりませんでした。A列に1から始まる連番があることを確認してください")
            
        return process_rows
    
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