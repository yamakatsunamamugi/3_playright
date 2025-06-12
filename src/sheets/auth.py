import os
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from src.utils.logger import get_logger
from config.settings import settings


logger = get_logger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheetsAuth:
    def __init__(self):
        self.creds = None
        self.token_file = Path('config/token.pickle')
        self.credentials_file = Path(settings.GOOGLE_CREDENTIALS_PATH)
        
    def authenticate(self):
        logger.info("Google Sheets認証を開始します")
        
        if self.token_file.exists():
            logger.info("既存のトークンファイルを読み込みます")
            with open(self.token_file, 'rb') as token:
                self.creds = pickle.load(token)
                
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("トークンの更新を試みます")
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.error(f"トークンの更新に失敗しました: {e}")
                    self.creds = None
                    
            if not self.creds:
                if not self.credentials_file.exists():
                    error_msg = (
                        f"認証ファイルが見つかりません: {self.credentials_file}\n"
                        "Google Cloud Consoleから認証情報をダウンロードして、"
                        f"{self.credentials_file}に配置してください。"
                    )
                    logger.error(error_msg)
                    raise FileNotFoundError(error_msg)
                    
                logger.info("新規認証フローを開始します")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                self.creds = flow.run_local_server(port=0)
                
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)
                logger.info("認証トークンを保存しました")
                
        logger.info("Google Sheets認証が完了しました")
        return self.creds
        
    def get_credentials(self):
        if not self.creds:
            self.authenticate()
        return self.creds