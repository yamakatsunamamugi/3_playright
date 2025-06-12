"""
スプレッドシートデータのバリデーション機能

このモジュールは以下の機能を提供します：
1. スプレッドシート構造の検証
2. データ型と値の妥当性チェック
3. 処理対象データの整合性確認
4. エラー詳細の報告

初心者向け解説：
- データ処理前に問題を早期発見
- わかりやすいエラーメッセージで問題箇所を特定
- 処理の安全性を確保
- データの整合性を保証
"""

from typing import List, Dict, Optional, Tuple, Set
import re
from src.utils.logger import get_logger
from src.utils.sheet_utils import SheetUtils

logger = get_logger(__name__)


class SpreadsheetValidator:
    """
    スプレッドシートデータの検証を行うクラス
    
    使用例:
        validator = SpreadsheetValidator()
        
        # 基本構造の検証
        is_valid, errors = validator.validate_basic_structure(sheet_data)
        
        # 処理設定の検証
        config = {
            'work_instruction_row': 5,
            'copy_columns': [3, 7],
            'process_rows': [1, 2, 3, 4]
        }
        is_valid, errors = validator.validate_processing_config(sheet_data, config)
    """
    
    def __init__(self):
        """バリデーターを初期化"""
        logger.info("🔍 SpreadsheetValidator を初期化しました")
        self.validation_errors: List[str] = []
        
    def validate_basic_structure(self, sheet_data: List[List[str]]) -> Tuple[bool, List[str]]:
        """
        スプレッドシートの基本構造を検証
        
        検証項目:
        1. データが空でない
        2. 最低限の行数がある（5行以上）
        3. 最低限の列数がある（3列以上）
        4. データの一貫性（行ごとの列数のばらつきが少ない）
        
        Args:
            sheet_data: 検証対象のシートデータ
            
        Returns:
            (検証結果: bool, エラーメッセージリスト: List[str])
        """
        logger.info("🔍 基本構造の検証を開始")
        errors = []
        
        # 1. データが空でないかチェック
        if not sheet_data:
            errors.append("シートデータが空です")
            return False, errors
            
        # 2. 最低限の行数チェック
        if len(sheet_data) < 5:
            errors.append(f"行数が不足しています: {len(sheet_data)}行（最低5行必要）")
            
        # 3. 最低限の列数チェック
        if sheet_data:
            max_cols = max(len(row) for row in sheet_data)
            if max_cols < 3:
                errors.append(f"列数が不足しています: {max_cols}列（最低3列必要）")
        
        # 4. データの一貫性チェック
        if sheet_data:
            col_counts = [len(row) for row in sheet_data]
            max_cols = max(col_counts)
            min_cols = min(col_counts)
            
            # 列数のばらつきが50%以上の場合は警告
            if max_cols > 0 and (max_cols - min_cols) / max_cols > 0.5:
                errors.append(
                    f"行ごとの列数にばらつきがあります: "
                    f"最小{min_cols}列、最大{max_cols}列"
                )
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"✅ 基本構造検証成功: {len(sheet_data)}行 x {max_cols}列")
        else:
            logger.warning(f"⚠️ 基本構造検証で{len(errors)}件の問題を検出")
            for error in errors:
                logger.warning(f"  - {error}")
                
        return is_valid, errors
    
    def validate_work_instruction_row(self, sheet_data: List[List[str]], 
                                    expected_row: int, marker: str = "作業指示行") -> Tuple[bool, List[str]]:
        """
        作業指示行の検証
        
        Args:
            sheet_data: シートデータ
            expected_row: 予想される作業指示行のインデックス
            marker: 作業指示行のマーカー文字列
            
        Returns:
            (検証結果: bool, エラーメッセージリスト: List[str])
        """
        logger.debug(f"🔍 作業指示行検証: 行{expected_row + 1}, マーカー='{marker}'")
        errors = []
        
        # 行インデックスの境界チェック
        if expected_row < 0 or expected_row >= len(sheet_data):
            errors.append(f"作業指示行インデックスが範囲外: {expected_row + 1}行目")
            return False, errors
            
        # 対象行のA列にマーカーがあるかチェック
        target_row = sheet_data[expected_row]
        if len(target_row) == 0:
            errors.append(f"{expected_row + 1}行目のA列が存在しません")
            return False, errors
            
        a_cell_value = str(target_row[0]).strip()
        if a_cell_value != marker:
            errors.append(
                f"{expected_row + 1}行目のA列の値が期待値と異なります: "
                f"期待='{marker}', 実際='{a_cell_value}'"
            )
            
        is_valid = len(errors) == 0
        if is_valid:
            logger.debug(f"✅ 作業指示行検証成功: {expected_row + 1}行目")
        
        return is_valid, errors
    
    def validate_copy_columns(self, header_row: List[str], 
                            copy_columns: List[int], marker: str = "コピー") -> Tuple[bool, List[str]]:
        """
        コピー列の検証
        
        Args:
            header_row: ヘッダー行のデータ
            copy_columns: 検証対象のコピー列インデックスリスト
            marker: コピー列のマーカー文字列
            
        Returns:
            (検証結果: bool, エラーメッセージリスト: List[str])
        """
        logger.debug(f"🔍 コピー列検証: {len(copy_columns)}列")
        errors = []
        
        if not copy_columns:
            errors.append("コピー列が指定されていません")
            return False, errors
            
        for col_idx in copy_columns:
            # 列インデックスの境界チェック
            if col_idx < 0 or col_idx >= len(header_row):
                col_letter = SheetUtils.index_to_column_letter(col_idx)
                errors.append(f"コピー列インデックスが範囲外: {col_letter}列（{col_idx}）")
                continue
                
            # セル値の確認
            cell_value = str(header_row[col_idx]).strip()
            if cell_value != marker:
                col_letter = SheetUtils.index_to_column_letter(col_idx)
                errors.append(
                    f"{col_letter}列の値が期待値と異なります: "
                    f"期待='{marker}', 実際='{cell_value}'"
                )
        
        is_valid = len(errors) == 0
        if is_valid:
            column_letters = [SheetUtils.index_to_column_letter(idx) for idx in copy_columns]
            logger.debug(f"✅ コピー列検証成功: {column_letters}")
        
        return is_valid, errors
    
    def validate_related_columns(self, sheet_data: List[List[str]], 
                               copy_columns: List[int]) -> Tuple[bool, List[str]]:
        """
        関連列（処理列、エラー列、貼り付け列）の検証
        
        Args:
            sheet_data: シートデータ
            copy_columns: コピー列のインデックスリスト
            
        Returns:
            (検証結果: bool, エラーメッセージリスト: List[str])
        """
        logger.debug(f"🔍 関連列検証: {len(copy_columns)}つのコピー列")
        errors = []
        
        max_col = max(len(row) for row in sheet_data) - 1 if sheet_data else -1
        
        for copy_col in copy_columns:
            copy_letter = SheetUtils.index_to_column_letter(copy_col)
            
            # 処理列（コピー列 - 2）
            process_col = copy_col - 2
            if process_col < 0:
                errors.append(f"{copy_letter}列の処理列が範囲外: {process_col}")
            
            # エラー列（コピー列 - 1）
            error_col = copy_col - 1
            if error_col < 0:
                errors.append(f"{copy_letter}列のエラー列が範囲外: {error_col}")
            
            # 貼り付け列（コピー列 + 1）
            paste_col = copy_col + 1
            if paste_col > max_col:
                paste_letter = SheetUtils.index_to_column_letter(paste_col)
                errors.append(
                    f"{copy_letter}列の貼り付け列が範囲外: {paste_letter}列"
                    f"（最大列: {SheetUtils.index_to_column_letter(max_col)}）"
                )
        
        is_valid = len(errors) == 0
        if is_valid:
            logger.debug(f"✅ 関連列検証成功: {len(copy_columns)}つのコピー列すべて")
        
        return is_valid, errors
    
    def validate_process_rows(self, sheet_data: List[List[str]], 
                            process_rows: List[int]) -> Tuple[bool, List[str]]:
        """
        処理対象行の検証
        
        Args:
            sheet_data: シートデータ
            process_rows: 検証対象の処理行インデックスリスト
            
        Returns:
            (検証結果: bool, エラーメッセージリスト: List[str])
        """
        logger.debug(f"🔍 処理対象行検証: {len(process_rows)}行")
        errors = []
        
        if not process_rows:
            errors.append("処理対象行が指定されていません")
            return False, errors
            
        for row_idx in process_rows:
            # 行インデックスの境界チェック
            if row_idx < 0 or row_idx >= len(sheet_data):
                errors.append(f"処理対象行インデックスが範囲外: {row_idx + 1}行目")
                continue
                
            # A列に連番があるかチェック
            row_data = sheet_data[row_idx]
            if len(row_data) == 0:
                errors.append(f"{row_idx + 1}行目: A列が存在しません")
                continue
                
            a_cell_value = str(row_data[0]).strip()
            if not a_cell_value.isdigit():
                errors.append(f"{row_idx + 1}行目: A列の値が数値ではありません（'{a_cell_value}'）")
        
        # 連番の連続性チェック
        if process_rows and len([e for e in errors if "A列の値が数値" in e]) == 0:
            row_numbers = []
            for row_idx in process_rows:
                if row_idx < len(sheet_data) and len(sheet_data[row_idx]) > 0:
                    a_value = str(sheet_data[row_idx][0]).strip()
                    if a_value.isdigit():
                        row_numbers.append(int(a_value))
            
            if row_numbers:
                expected_sequence = list(range(1, len(row_numbers) + 1))
                if sorted(row_numbers) != expected_sequence:
                    errors.append(
                        f"A列の連番が正しくありません: "
                        f"期待=[1-{len(row_numbers)}], 実際={sorted(row_numbers)}"
                    )
        
        is_valid = len(errors) == 0
        if is_valid:
            logger.debug(f"✅ 処理対象行検証成功: {len(process_rows)}行")
        
        return is_valid, errors
    
    def validate_processing_config(self, sheet_data: List[List[str]], 
                                 config: Dict) -> Tuple[bool, List[str]]:
        """
        処理設定全体の包括的検証
        
        Args:
            sheet_data: シートデータ
            config: 処理設定
                   {
                       'work_instruction_row': int,
                       'copy_columns': List[int],
                       'process_rows': List[int]
                   }
                   
        Returns:
            (検証結果: bool, エラーメッセージリスト: List[str])
        """
        logger.info("🔍 処理設定の包括的検証を開始")
        all_errors = []
        
        # 基本構造の検証
        is_valid, errors = self.validate_basic_structure(sheet_data)
        all_errors.extend(errors)
        
        if not is_valid:
            logger.error("❌ 基本構造検証に失敗したため、詳細検証をスキップします")
            return False, all_errors
        
        # 作業指示行の検証
        work_row = config.get('work_instruction_row')
        if work_row is not None:
            is_valid, errors = self.validate_work_instruction_row(sheet_data, work_row)
            all_errors.extend(errors)
            
            # ヘッダー行データを取得（後続の検証用）
            if is_valid and work_row < len(sheet_data):
                header_row = sheet_data[work_row]
            else:
                header_row = []
        else:
            all_errors.append("作業指示行が設定されていません")
            header_row = []
        
        # コピー列の検証
        copy_columns = config.get('copy_columns', [])
        if copy_columns and header_row:
            is_valid, errors = self.validate_copy_columns(header_row, copy_columns)
            all_errors.extend(errors)
            
            # 関連列の検証
            if is_valid:
                is_valid, errors = self.validate_related_columns(sheet_data, copy_columns)
                all_errors.extend(errors)
        elif not copy_columns:
            all_errors.append("コピー列が設定されていません")
        
        # 処理対象行の検証
        process_rows = config.get('process_rows', [])
        if process_rows:
            is_valid, errors = self.validate_process_rows(sheet_data, process_rows)
            all_errors.extend(errors)
        else:
            all_errors.append("処理対象行が設定されていません")
        
        is_valid = len(all_errors) == 0
        
        if is_valid:
            logger.info("✅ 処理設定の包括的検証が成功しました")
        else:
            logger.error(f"❌ 処理設定の包括的検証で{len(all_errors)}件の問題を検出:")
            for i, error in enumerate(all_errors, 1):
                logger.error(f"  {i}. {error}")
        
        return is_valid, all_errors
    
    def validate_cell_content(self, content: str, 
                            allow_empty: bool = True, 
                            max_length: Optional[int] = None) -> Tuple[bool, List[str]]:
        """
        セル内容の検証
        
        Args:
            content: セルの内容
            allow_empty: 空文字を許可するか
            max_length: 最大文字数制限
            
        Returns:
            (検証結果: bool, エラーメッセージリスト: List[str])
        """
        errors = []
        
        # 空文字チェック
        if not content.strip() and not allow_empty:
            errors.append("セルが空です")
        
        # 文字数制限チェック
        if max_length and len(content) > max_length:
            errors.append(f"文字数制限を超過: {len(content)}文字（最大{max_length}文字）")
        
        # 制御文字のチェック
        control_chars = [char for char in content if ord(char) < 32 and char not in '\t\n\r']
        if control_chars:
            errors.append(f"制御文字が含まれています: {[ord(char) for char in control_chars]}")
        
        return len(errors) == 0, errors
    
    def get_validation_summary(self, sheet_data: List[List[str]], 
                             config: Dict) -> Dict[str, any]:
        """
        検証結果のサマリーを生成
        
        Returns:
            検証結果のサマリー辞書
        """
        logger.info("📊 検証サマリーを生成")
        
        is_valid, errors = self.validate_processing_config(sheet_data, config)
        
        summary = {
            'is_valid': is_valid,
            'error_count': len(errors),
            'errors': errors,
            'sheet_info': {
                'row_count': len(sheet_data),
                'max_col_count': max(len(row) for row in sheet_data) if sheet_data else 0,
                'data_size_kb': len(str(sheet_data)) / 1024
            },
            'config_info': {
                'work_instruction_row': config.get('work_instruction_row'),
                'copy_column_count': len(config.get('copy_columns', [])),
                'process_row_count': len(config.get('process_rows', []))
            }
        }
        
        logger.info(f"📊 検証サマリー生成完了: {'✅ 有効' if is_valid else '❌ 無効'}")
        return summary