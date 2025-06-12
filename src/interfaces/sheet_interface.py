from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional


class ISheetProcessor(ABC):
    """チームBが実装するスプレッドシート処理のインターフェース"""
    
    @abstractmethod
    def find_work_instruction_row(self, sheet_data: List[List[str]]) -> int:
        """
        作業指示行を検索
        
        Args:
            sheet_data: シート全体のデータ
            
        Returns:
            作業指示行のインデックス（0ベース）
            見つからない場合は-1
        """
        pass
    
    @abstractmethod
    def find_copy_columns(self, header_row: List[str]) -> List[int]:
        """
        'コピー'列を全て検索
        
        Args:
            header_row: ヘッダー行のデータ
            
        Returns:
            コピー列のインデックスリスト（0ベース）
        """
        pass
    
    @abstractmethod
    def calculate_related_columns(self, copy_col: int) -> Dict[str, int]:
        """
        コピー列に関連する列の位置を計算
        
        Args:
            copy_col: コピー列のインデックス
            
        Returns:
            {'process_col': int, 'error_col': int, 'paste_col': int}
        """
        pass
    
    @abstractmethod
    def get_process_rows(self, sheet_data: List[List[str]]) -> List[int]:
        """
        処理対象行（A列が1から始まる連番）を取得
        
        Returns:
            処理対象行のインデックスリスト
        """
        pass


class ISheetHandler(ABC):
    """スプレッドシートのデータ読み書きインターフェース"""
    
    @abstractmethod
    def read_cell(self, sheet_id: str, sheet_name: str, row: int, col: int) -> str:
        """単一セルの読み取り"""
        pass
    
    @abstractmethod
    def write_cell(self, sheet_id: str, sheet_name: str, row: int, col: int, value: str) -> bool:
        """単一セルへの書き込み"""
        pass
    
    @abstractmethod
    def batch_update(self, sheet_id: str, updates: List[Dict]) -> bool:
        """複数セルの一括更新"""
        pass
    
    @abstractmethod
    def get_sheet_data(self, sheet_id: str, sheet_name: str) -> List[List[str]]:
        """シート全体のデータ取得"""
        pass