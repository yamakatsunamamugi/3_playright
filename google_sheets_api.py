#!/usr/bin/env python3
"""
Google Sheets API操作クラス
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

try:
    from google.auth import load_credentials_from_file
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Google API ライブラリが不足しています")
    print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    raise

class GoogleSheetsAPI:
    """Google Sheets API操作クラス"""
    
    def __init__(self, credentials_file: str = "credentials/google_service_account.json"):
        """
        初期化
        
        Args:
            credentials_file: 認証情報ファイルパス
        """
        self.credentials_file = credentials_file
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Google Sheets APIサービスを初期化"""
        try:
            # 認証情報読み込み
            credentials, project = load_credentials_from_file(
                self.credentials_file,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets.readonly',
                    'https://www.googleapis.com/auth/spreadsheets'
                ]
            )
            
            # サービス作成
            self.service = build('sheets', 'v4', credentials=credentials)
            print("✅ Google Sheets API 初期化成功")
            
        except FileNotFoundError:
            print(f"❌ 認証ファイルが見つかりません: {self.credentials_file}")
            raise
        except Exception as e:
            print(f"❌ API初期化エラー: {e}")
            raise
    
    def extract_spreadsheet_id(self, url: str) -> Optional[str]:
        """
        スプレッドシートURLからIDを抽出
        
        Args:
            url: スプレッドシートURL
            
        Returns:
            スプレッドシートID または None
        """
        patterns = [
            r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_sheet_names(self, spreadsheet_url: str) -> List[str]:
        """
        スプレッドシートのシート名一覧を取得
        
        Args:
            spreadsheet_url: スプレッドシートURL
            
        Returns:
            シート名のリスト
        """
        try:
            # スプレッドシートID抽出
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
            if not spreadsheet_id:
                raise ValueError("無効なスプレッドシートURLです")
            
            # スプレッドシート情報取得
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            # シート名抽出
            sheets = sheet_metadata.get('sheets', [])
            sheet_names = []
            
            for sheet in sheets:
                sheet_name = sheet.get('properties', {}).get('title', '')
                if sheet_name:
                    sheet_names.append(sheet_name)
            
            print(f"✅ {len(sheet_names)}個のシートを取得")
            return sheet_names
            
        except HttpError as e:
            print(f"❌ HTTP エラー: {e}")
            if e.resp.status == 403:
                print("💡 スプレッドシートがサービスアカウントに共有されているか確認してください")
            return []
        except Exception as e:
            print(f"❌ シート名取得エラー: {e}")
            return []
    
    def get_sheet_data(self, spreadsheet_url: str, sheet_name: str, range_name: str = None) -> List[List[str]]:
        """
        シートデータを取得
        
        Args:
            spreadsheet_url: スプレッドシートURL
            sheet_name: シート名
            range_name: 範囲（例: "A1:Z100"）、Noneで全体
            
        Returns:
            セルデータの2次元リスト
        """
        try:
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
            if not spreadsheet_id:
                raise ValueError("無効なスプレッドシートURLです")
            
            # 範囲指定
            if range_name:
                full_range = f"'{sheet_name}'!{range_name}"
            else:
                full_range = f"'{sheet_name}'"
            
            # データ取得
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=full_range
            ).execute()
            
            values = result.get('values', [])
            print(f"✅ {len(values)}行のデータを取得")
            return values
            
        except Exception as e:
            print(f"❌ データ取得エラー: {e}")
            return []
    
    def find_copy_columns(self, spreadsheet_url: str, sheet_name: str) -> List[Dict[str, Any]]:
        """
        「コピー」列を検出
        
        Args:
            spreadsheet_url: スプレッドシートURL
            sheet_name: シート名
            
        Returns:
            コピー列情報のリスト
        """
        try:
            # 最初の10行を取得（ヘッダー検出用）
            data = self.get_sheet_data(spreadsheet_url, sheet_name, "A1:Z10")
            
            copy_columns = []
            
            # 5行目の「作業指示行」を探す
            if len(data) >= 5:
                header_row = data[4]  # 5行目（0ベース）
                
                for col_index, cell_value in enumerate(header_row):
                    if cell_value and "コピー" in str(cell_value):
                        # 列名（A, B, C...）を計算
                        col_letter = chr(ord('A') + col_index)
                        
                        copy_columns.append({
                            'name': str(cell_value),
                            'column': col_letter,
                            'index': col_index
                        })
            
            print(f"✅ {len(copy_columns)}個の「コピー」列を検出")
            for col in copy_columns:
                print(f"   • {col['column']}列: {col['name']}")
            
            return copy_columns
            
        except Exception as e:
            print(f"❌ コピー列検出エラー: {e}")
            return []

# テスト用関数
def test_api():
    """APIテスト"""
    api = GoogleSheetsAPI()
    
    # テスト用URL
    test_url = "https://docs.google.com/spreadsheets/d/1mhvJKjNNdFqn_xo1D7iZzEyoLm9_2Qh3TbcV8NrW5Sx"
    
    print("🧪 Google Sheets API テスト開始")
    print("=" * 50)
    
    # シート名取得テスト
    sheet_names = api.get_sheet_names(test_url)
    print(f"📋 取得したシート: {sheet_names}")
    
    if sheet_names:
        # 最初のシートのコピー列検出
        first_sheet = sheet_names[0]
        copy_columns = api.find_copy_columns(test_url, first_sheet)
        print(f"🎯 コピー列: {copy_columns}")

if __name__ == "__main__":
    test_api()