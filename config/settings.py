import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / '.env'
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv(BASE_DIR / '.env.example')


class Settings:
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'config/credentials.json')
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    APP_ENV = os.getenv('APP_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', '300'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '5'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '10'))
    
    SUPPORTED_AI_TOOLS = [
        'ChatGPT',
        'Claude',
        'Gemini',
        'Genspark',
        'Google AI Studio'
    ]
    
    SPREADSHEET_HEADER_ROW = 5
    WORK_INDICATOR = "作業指示行"
    COPY_COLUMN_HEADER = "コピー"
    PROCESS_STATUS_EMPTY = "空白"
    PROCESS_STATUS_UNPROCESSED = "未処理"
    PROCESS_STATUS_PROCESSED = "処理済み"
    
    WINDOW_TITLE = "AI Tools Automation"
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600


settings = Settings()