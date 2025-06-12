from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.sheets.auth import GoogleSheetsAuth
from src.utils.logger import get_logger
from config.settings import settings
import time


logger = get_logger(__name__)


class GoogleSheetsClient:
    def __init__(self):
        self.auth = GoogleSheetsAuth()
        self.service = None
        self._initialize_service()
        
    def _initialize_service(self):
        try:
            creds = self.auth.get_credentials()
            self.service = build('sheets', 'v4', credentials=creds)
            logger.info("Google Sheets APIサービスを初期化しました")
        except Exception as e:
            logger.error(f"サービスの初期化に失敗しました: {e}")
            raise
            
    def get_spreadsheet_metadata(self, spreadsheet_id: str):
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            logger.info(f"スプレッドシート情報を取得しました: {spreadsheet.get('properties', {}).get('title', 'Unknown')}")
            return spreadsheet
        except HttpError as e:
            logger.error(f"スプレッドシート情報の取得に失敗しました: {e}")
            raise
            
    def get_sheet_names(self, spreadsheet_id: str):
        metadata = self.get_spreadsheet_metadata(spreadsheet_id)
        sheets = metadata.get('sheets', [])
        sheet_names = [sheet['properties']['title'] for sheet in sheets]
        logger.info(f"シート名一覧: {sheet_names}")
        return sheet_names
        
    def read_range(self, spreadsheet_id: str, range_name: str):
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            logger.info(f"範囲 {range_name} から {len(values)} 行のデータを読み取りました")
            return values
        except HttpError as e:
            logger.error(f"データの読み取りに失敗しました: {e}")
            raise
            
    def write_value(self, spreadsheet_id: str, range_name: str, value: str):
        try:
            body = {'values': [[value]]}
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"範囲 {range_name} にデータを書き込みました")
            return result
        except HttpError as e:
            logger.error(f"データの書き込みに失敗しました: {e}")
            raise
            
    def batch_update(self, spreadsheet_id: str, updates: list):
        try:
            body = {
                'valueInputOption': 'RAW',
                'data': updates
            }
            
            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
            logger.info(f"{len(updates)} 件の更新を実行しました")
            return result
        except HttpError as e:
            logger.error(f"バッチ更新に失敗しました: {e}")
            raise
            
    def find_cell(self, spreadsheet_id: str, sheet_name: str, search_value: str):
        try:
            range_name = f"{sheet_name}!A1:Z1000"
            values = self.read_range(spreadsheet_id, range_name)
            
            for row_idx, row in enumerate(values):
                for col_idx, cell_value in enumerate(row):
                    if cell_value == search_value:
                        logger.info(f"'{search_value}' を {sheet_name}!{chr(65 + col_idx)}{row_idx + 1} で発見しました")
                        return (row_idx, col_idx)
                        
            logger.warning(f"'{search_value}' が見つかりませんでした")
            return None
        except Exception as e:
            logger.error(f"セルの検索中にエラーが発生しました: {e}")
            raise