"""
Google Sheets API連携ハンドラー

CLAUDE.mdの要件：
- A列の番号（1,2,3...）で処理対象行を特定
- 5行目の「作業指示行」から「コピー」列を検索
- 「コピー」列-2 = 処理列（未処理/処理中/処理済み）
- 「コピー」列-1 = エラー列
- 「コピー」列+1 = 貼り付け列
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from src.utils.retry_handler import retry_on_api_error
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SheetsHandler:
    """Google Sheets操作を管理するクラス"""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self, credentials_path: str = "google_service_account.json"):
        """
        初期化
        
        Args:
            credentials_path: 認証情報ファイルのパス
        """
        self.credentials_path = credentials_path
        self.service = None
        self.spreadsheet_id = None
        self.sheet_name = None
        self.work_instruction_row = 5  # CLAUDE.md要件：5行目が作業指示行
        
        logger.info("📊 SheetsHandler を初期化しました")
    
    def authenticate(self) -> bool:
        """
        Google Sheets APIの認証
        
        Returns:
            bool: 認証成功時True
        """
        try:
            logger.info("🔐 Google Sheets API認証を開始...")
            
            # サービスアカウント認証
            from google.oauth2 import service_account
            
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
            
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("✅ Google Sheets API認証完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ Google Sheets API認証エラー: {e}")
            return False
    
    def set_spreadsheet(self, spreadsheet_url: str, sheet_name: str) -> bool:
        """
        対象スプレッドシートを設定
        
        Args:
            spreadsheet_url: スプレッドシートのURL
            sheet_name: シート名
            
        Returns:
            bool: 設定成功時True
        """
        try:
            # URLからスプレッドシートIDを抽出
            match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', spreadsheet_url)
            if not match:
                raise ValueError("無効なスプレッドシートURLです")
            
            self.spreadsheet_id = match.group(1)
            self.sheet_name = sheet_name
            
            logger.info(f"📊 スプレッドシート設定: {self.spreadsheet_id}, シート: {sheet_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ スプレッドシート設定エラー: {e}")
            return False
    
    @retry_on_api_error(max_retries=3)
    def analyze_sheet_structure(self) -> Dict[str, Any]:
        """
        シート構造を分析（CLAUDE.md要件に基づく）
        
        Returns:
            Dict: 分析結果
        """
        try:
            logger.info("🔍 シート構造を分析中...")
            
            # 作業指示行（5行目）を読み取り
            work_row_range = f"{self.sheet_name}!{self.work_instruction_row}:{self.work_instruction_row}"
            work_row_result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=work_row_range
            ).execute()
            
            work_row_values = work_row_result.get('values', [[]])[0] if work_row_result.get('values') else []
            
            # 「コピー」列を検索
            copy_columns = []
            for col_index, cell_value in enumerate(work_row_values):
                if str(cell_value).strip() == "コピー":
                    col_letter = self._column_index_to_letter(col_index + 1)
                    copy_columns.append({
                        'column_letter': col_letter,
                        'column_index': col_index + 1,
                        'process_column': col_index - 1,  # コピー列-2
                        'error_column': col_index,        # コピー列-1
                        'paste_column': col_index + 2     # コピー列+1
                    })
            
            if not copy_columns:
                raise ValueError("「コピー」列が見つかりません")
            
            # A列の処理対象行を検索
            a_column_range = f"{self.sheet_name}!A:A"
            a_column_result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=a_column_range
            ).execute()
            
            a_column_values = a_column_result.get('values', [])
            
            # 数値が入っている行を特定
            target_rows = []
            for row_index, row_data in enumerate(a_column_values):
                if row_data and str(row_data[0]).strip().isdigit():
                    target_rows.append(row_index + 1)  # 1-based
            
            structure = {
                'copy_columns': copy_columns,
                'target_rows': target_rows,
                'work_instruction_row': self.work_instruction_row,
                'total_copy_columns': len(copy_columns),
                'total_target_rows': len(target_rows)
            }
            
            logger.info(f"✅ 構造分析完了: {len(copy_columns)}個のコピー列, {len(target_rows)}行の処理対象")
            return structure
            
        except Exception as e:
            logger.error(f"❌ シート構造分析エラー: {e}")
            raise
    
    @retry_on_api_error(max_retries=3)
    def read_cell_value(self, row: int, column: int) -> str:
        """
        指定セルの値を読み取り
        
        Args:
            row: 行番号（1-based）
            column: 列番号（1-based）
            
        Returns:
            str: セルの値
        """
        try:
            col_letter = self._column_index_to_letter(column)
            cell_range = f"{self.sheet_name}!{col_letter}{row}"
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=cell_range
            ).execute()
            
            values = result.get('values', [['']])
            return str(values[0][0]) if values and values[0] else ''
            
        except Exception as e:
            logger.error(f"❌ セル読み取りエラー ({row}, {column}): {e}")
            return ''
    
    @retry_on_api_error(max_retries=3)
    def write_cell_value(self, row: int, column: int, value: str) -> bool:
        """
        指定セルに値を書き込み
        
        Args:
            row: 行番号（1-based）
            column: 列番号（1-based）
            value: 書き込む値
            
        Returns:
            bool: 書き込み成功時True
        """
        try:
            col_letter = self._column_index_to_letter(column)
            cell_range = f"{self.sheet_name}!{col_letter}{row}"
            
            body = {
                'values': [[value]]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=cell_range,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.debug(f"📝 セル書き込み完了 ({row}, {column}): {value[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ セル書き込みエラー ({row}, {column}): {e}")
            return False
    
    @retry_on_api_error(max_retries=3)
    def get_copy_text(self, copy_column_info: Dict, row: int) -> str:
        """
        コピー列からテキストを取得
        
        Args:
            copy_column_info: コピー列情報
            row: 行番号
            
        Returns:
            str: コピーするテキスト
        """
        return self.read_cell_value(row, copy_column_info['column_index'])
    
    @retry_on_api_error(max_retries=3)
    def get_process_status(self, copy_column_info: Dict, row: int) -> str:
        """
        処理状況を取得
        
        Args:
            copy_column_info: コピー列情報
            row: 行番号
            
        Returns:
            str: 処理状況（未処理/処理中/処理済み）
        """
        return self.read_cell_value(row, copy_column_info['process_column'])
    
    @retry_on_api_error(max_retries=3)
    def set_process_status(self, copy_column_info: Dict, row: int, status: str) -> bool:
        """
        処理状況を設定
        
        Args:
            copy_column_info: コピー列情報
            row: 行番号
            status: 処理状況
            
        Returns:
            bool: 設定成功時True
        """
        return self.write_cell_value(row, copy_column_info['process_column'], status)
    
    @retry_on_api_error(max_retries=3)
    def set_error_message(self, copy_column_info: Dict, row: int, error_message: str) -> bool:
        """
        エラーメッセージを設定
        
        Args:
            copy_column_info: コピー列情報
            row: 行番号
            error_message: エラーメッセージ
            
        Returns:
            bool: 設定成功時True
        """
        return self.write_cell_value(row, copy_column_info['error_column'], error_message)
    
    @retry_on_api_error(max_retries=3)
    def set_paste_result(self, copy_column_info: Dict, row: int, result: str) -> bool:
        """
        AI処理結果を貼り付け
        
        Args:
            copy_column_info: コピー列情報
            row: 行番号
            result: AI処理結果
            
        Returns:
            bool: 貼り付け成功時True
        """
        return self.write_cell_value(row, copy_column_info['paste_column'], result)
    
    def _column_index_to_letter(self, column_index: int) -> str:
        """
        列番号を列文字に変換（1-based）
        
        Args:
            column_index: 列番号（1から開始）
            
        Returns:
            str: 列文字（A, B, C, ..., AA, AB, ...）
        """
        result = ""
        while column_index > 0:
            column_index -= 1
            result = chr(column_index % 26 + ord('A')) + result
            column_index //= 26
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """
        現在の状態を取得
        
        Returns:
            Dict: 状態情報
        """
        return {
            "authenticated": self.service is not None,
            "spreadsheet_id": self.spreadsheet_id,
            "sheet_name": self.sheet_name,
            "credentials_path": self.credentials_path
        }