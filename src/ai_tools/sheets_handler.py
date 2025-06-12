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
    
    def __init__(self, credentials_path: str = None):
        """
        初期化
        
        Args:
            credentials_path: 認証情報ファイルのパス
        """
        # 認証ファイルパスを自動検出
        if credentials_path is None:
            import os
            possible_paths = [
                "credentials/google_service_account.json",
                "google_service_account.json",
                "../credentials/google_service_account.json",
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "credentials", "google_service_account.json")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    credentials_path = path
                    break
        
        self.credentials_path = credentials_path
        self.service = None
        self.spreadsheet_id = None
        self.sheet_name = None
        self.work_instruction_row = None  # 動的に検索して設定
        
        logger.info(f"📊 SheetsHandler を初期化しました (認証ファイル: {self.credentials_path})")
    
    def authenticate(self) -> bool:
        """
        Google Sheets APIの認証
        
        Returns:
            bool: 認証成功時True
        """
        try:
            logger.info("🔐 Google Sheets API認証を開始...")
            
            # まずサービスアカウント認証を試行
            if self._try_service_account_auth():
                return True
            
            # サービスアカウントが失敗した場合、OAuth2認証を試行
            logger.info("🔄 OAuth2認証を試行...")
            return self._try_oauth2_auth()
            
        except Exception as e:
            logger.error(f"❌ Google Sheets API認証エラー: {e}")
            return False
    
    def _try_service_account_auth(self) -> bool:
        """サービスアカウント認証を試行"""
        try:
            from google.oauth2 import service_account
            import os
            
            if not os.path.exists(self.credentials_path):
                logger.warning(f"⚠️ サービスアカウントファイルが見つかりません: {self.credentials_path}")
                return False
            
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
            
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("✅ サービスアカウント認証完了")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ サービスアカウント認証失敗: {e}")
            return False
    
    def _try_oauth2_auth(self) -> bool:
        """OAuth2認証を試行"""
        try:
            import os
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            import pickle
            
            creds = None
            token_path = 'token.pickle'
            
            # 既存のトークンをチェック
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # 認証情報が無効または存在しない場合
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # credentials.jsonを探す
                    credentials_json_paths = [
                        'credentials.json',
                        'credentials/credentials.json',
                        'config/credentials.json'
                    ]
                    
                    credentials_json_path = None
                    for path in credentials_json_paths:
                        if os.path.exists(path):
                            credentials_json_path = path
                            break
                    
                    if not credentials_json_path:
                        logger.error("❌ credentials.jsonファイルが見つかりません")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_json_path, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # トークンを保存
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('sheets', 'v4', credentials=creds)
            logger.info("✅ OAuth2認証完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ OAuth2認証失敗: {e}")
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
    def get_sheet_names(self) -> List[str]:
        """
        スプレッドシート内の全シート名を取得
        
        Returns:
            List[str]: シート名のリスト
        """
        try:
            logger.info("📋 シート名一覧を取得中...")
            
            if not self.service or not self.spreadsheet_id:
                raise ValueError("スプレッドシートが設定されていません")
            
            # スプレッドシートのメタデータを取得
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            # シート名を抽出
            sheet_names = []
            sheets = spreadsheet.get('sheets', [])
            
            for sheet in sheets:
                sheet_properties = sheet.get('properties', {})
                sheet_name = sheet_properties.get('title', '')
                if sheet_name:
                    sheet_names.append(sheet_name)
            
            logger.info(f"✅ シート名取得完了: {len(sheet_names)}個のシート")
            for name in sheet_names:
                logger.info(f"   📄 {name}")
            
            return sheet_names
            
        except Exception as e:
            logger.error(f"❌ シート名取得エラー: {e}")
            raise
    
    @retry_on_api_error(max_retries=3)
    def verify_sheet_exists(self, sheet_name: str) -> bool:
        """
        指定されたシート名が存在するかチェック
        
        Args:
            sheet_name: チェックするシート名
            
        Returns:
            bool: シートが存在する場合True
        """
        try:
            sheet_names = self.get_sheet_names()
            exists = sheet_name in sheet_names
            
            if exists:
                logger.info(f"✅ シート確認完了: '{sheet_name}' が存在します")
            else:
                logger.warning(f"⚠️ シートが見つかりません: '{sheet_name}'")
                logger.info(f"利用可能なシート: {', '.join(sheet_names)}")
            
            return exists
            
        except Exception as e:
            logger.error(f"❌ シート存在確認エラー: {e}")
            return False

    def find_work_instruction_row(self) -> int:
        """
        A列の1～10行目を検索して「作業指示行」を見つける
        
        Returns:
            int: 作業指示行の行番号（1-based）
        """
        try:
            logger.info("🔍 作業指示行を検索中...")
            
            # A1:A10を検索
            range_name = f"{self.sheet_name}!A1:A10"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            for row_index, row_data in enumerate(values, start=1):
                if row_data and "作業指示行" in str(row_data[0]):
                    logger.info(f"✅ 作業指示行を検出: {row_index}行目")
                    return row_index
            
            # 見つからない場合はエラー
            logger.error("❌ A列1～10行目に「作業指示行」が見つかりません")
            raise ValueError("A列1～10行目に「作業指示行」が見つかりません")
            
        except Exception as e:
            logger.error(f"❌ 作業指示行検索エラー: {e}")
            raise
    
    def find_data_start_row(self) -> int:
        """
        A列で数字「1」を検索してデータ開始行を見つける
        
        Returns:
            int: データ開始行の行番号（1-based）
        """
        try:
            logger.info("🔍 データ開始行を検索中...")
            
            if not self.work_instruction_row:
                raise ValueError("作業指示行が設定されていません")
            
            # 作業指示行の次の行から最大50行まで検索
            start_row = self.work_instruction_row + 1
            end_row = min(start_row + 50, 100)
            
            for row_index in range(start_row, end_row):
                cell_value = self.read_cell_value(row_index, 1)  # A列
                if cell_value == "1":
                    logger.info(f"✅ データ開始行を検出: {row_index}行目")
                    return row_index
            
            # 見つからない場合はエラー
            logger.error("❌ A列に「1」が見つかりません")
            raise ValueError("A列に「1」が見つかりません（処理対象データなし）")
            
        except Exception as e:
            logger.error(f"❌ データ開始行検索エラー: {e}")
            raise

    @retry_on_api_error(max_retries=3)
    def analyze_sheet_structure(self) -> Dict[str, Any]:
        """
        シート構造を分析（CLAUDE.md要件に基づく）
        
        Returns:
            Dict: 分析結果
        """
        try:
            logger.info("🔍 シート構造を分析中...")
            
            # 作業指示行を動的に検索
            self.work_instruction_row = self.find_work_instruction_row()
            
            # 作業指示行を読み取り
            work_row_range = f"{self.sheet_name}!{self.work_instruction_row}:{self.work_instruction_row}"
            work_row_result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=work_row_range
            ).execute()
            
            work_row_values = work_row_result.get('values', [[]])[0] if work_row_result.get('values') else []
            
            # 「コピー」列を検索（より柔軟な検索）
            copy_columns = []
            for col_index, cell_value in enumerate(work_row_values):
                cell_str = str(cell_value).strip().lower()
                # 「コピー」「copy」「コピー列」など様々なパターンに対応
                if any(keyword in cell_str for keyword in ['コピー', 'copy', 'ｺﾋﾟｰ']):
                    col_letter = self._column_index_to_letter(col_index + 1)
                    copy_columns.append({
                        'column_letter': col_letter,
                        'column_index': col_index + 1,
                        'process_column': max(1, col_index - 1),  # コピー列-2 (最小1列目)
                        'error_column': max(1, col_index),        # コピー列-1 (最小1列目)
                        'paste_column': col_index + 2             # コピー列+1
                    })
                    logger.info(f"🎯 コピー列を検出: {col_letter}列 '{cell_value}'")
            
            if not copy_columns:
                # より詳細なエラー情報を提供
                logger.warning("⚠️ 「コピー」列が見つかりません")
                logger.info("📋 作業指示行の内容:")
                for i, value in enumerate(work_row_values):
                    col_letter = self._column_index_to_letter(i + 1)
                    logger.info(f"   {col_letter}列: '{value}'")
                logger.info("💡 「コピー」「copy」「コピー列」などの文字列を含む列を作成してください")
                raise ValueError("「コピー」列が見つかりません。作業指示行に「コピー」列を作成してください。")
            
            # データ開始行を検索
            data_start_row = self.find_data_start_row()
            
            # A列の処理対象行を検索（データ開始行から）
            a_column_range = f"{self.sheet_name}!A{data_start_row}:A"
            a_column_result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=a_column_range
            ).execute()
            
            a_column_values = a_column_result.get('values', [])
            
            # 連続した数値が入っている行を特定
            target_rows = []
            for row_index, row_data in enumerate(a_column_values):
                if row_data and str(row_data[0]).strip().isdigit():
                    target_rows.append(data_start_row + row_index)  # 実際の行番号
                else:
                    # 空白セルまたは数値以外で終了
                    break
            
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