from typing import List, Dict
from src.interfaces.sheet_interface import ISheetProcessor, ISheetHandler


class MockSheetProcessor(ISheetProcessor):
    """チームAとCが使用するシート処理のモック"""
    
    def find_work_instruction_row(self, sheet_data: List[List[str]]) -> int:
        # テスト用のサンプルデータを想定
        for i, row in enumerate(sheet_data):
            if len(row) > 0 and row[0] == "作業指示行":
                return i
        return 4  # デフォルトで5行目（0ベースで4）
    
    def find_copy_columns(self, header_row: List[str]) -> List[int]:
        # サンプル: B列とE列に「コピー」があると仮定
        copy_columns = []
        for i, cell in enumerate(header_row):
            if cell == "コピー":
                copy_columns.append(i)
        
        if not copy_columns:
            # テスト用にB列（1）とE列（4）をデフォルト値として返す
            return [1, 4]
        return copy_columns
    
    def calculate_related_columns(self, copy_col: int) -> Dict[str, int]:
        return {
            'process_col': max(0, copy_col - 2),  # 境界チェック
            'error_col': max(0, copy_col - 1),
            'paste_col': copy_col + 1
        }
    
    def get_process_rows(self, sheet_data: List[List[str]]) -> List[int]:
        # A列が「1」「2」「3」...の行を返す
        process_rows = []
        for i, row in enumerate(sheet_data):
            if len(row) > 0:
                try:
                    if row[0].isdigit() and int(row[0]) >= 1:
                        process_rows.append(i)
                except (ValueError, AttributeError):
                    continue
        
        if not process_rows:
            # テスト用にいくつかの行を返す
            return [5, 6, 7, 8]  # 6行目から9行目
        return process_rows


class MockSheetHandler(ISheetHandler):
    """チームAとCが使用するシートハンドラーのモック"""
    
    def __init__(self):
        # メモリ上にテストデータを保持
        self.mock_data = {
            "test_sheet": [
                ["", "", "", "", ""],
                ["", "", "", "", ""],
                ["", "", "", "", ""],
                ["", "", "", "", ""],
                ["作業指示行", "コピー", "処理", "エラー", "コピー", "貼り付け"],
                ["1", "プロンプト1", "", "", "プロンプト2", ""],
                ["2", "プロンプト3", "", "", "プロンプト4", ""],
                ["3", "プロンプト5", "", "", "プロンプト6", ""],
            ]
        }
    
    def read_cell(self, sheet_id: str, sheet_name: str, row: int, col: int) -> str:
        try:
            return self.mock_data[sheet_name][row][col]
        except (KeyError, IndexError):
            return ""
    
    def write_cell(self, sheet_id: str, sheet_name: str, row: int, col: int, value: str) -> bool:
        try:
            if sheet_name not in self.mock_data:
                self.mock_data[sheet_name] = []
            
            # 行を拡張
            while len(self.mock_data[sheet_name]) <= row:
                self.mock_data[sheet_name].append([])
            
            # 列を拡張
            while len(self.mock_data[sheet_name][row]) <= col:
                self.mock_data[sheet_name][row].append("")
            
            self.mock_data[sheet_name][row][col] = value
            return True
        except Exception:
            return False
    
    def batch_update(self, sheet_id: str, updates: List[Dict]) -> bool:
        try:
            for update in updates:
                sheet_name = update['sheet_name']
                row = update['row']
                col = update['col']
                value = update['value']
                self.write_cell(sheet_id, sheet_name, row, col, value)
            return True
        except Exception:
            return False
    
    def get_sheet_data(self, sheet_id: str, sheet_name: str) -> List[List[str]]:
        return self.mock_data.get(sheet_name, [])