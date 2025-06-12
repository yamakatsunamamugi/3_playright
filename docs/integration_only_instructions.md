# 統合作業のみの指示書（既存モジュール接続）

## 現在の状況
既に以下のモジュールが実装済みです：
- ✅ GUI（完全動作）
- ✅ Google Sheets認証とクライアント
- ✅ AIツール基本実装（ChatGPT）
- ✅ ブラウザマネージャー
- ✅ エラーハンドリング基盤
- ✅ ログシステム

**残り作業は既存モジュールを接続するだけです！**

## チーム分担（ファイルコンフリクトを避ける）

### チームA: Sheets処理の接続
**作業ファイル:**
- `src/sheets/reader.py` (新規)
- `src/sheets/writer.py` (新規)  
- `src/sheets/column_detector.py` (新規)

**既存ファイルは触らない！**

### チームB: AI処理の接続
**作業ファイル:**
- `src/ai_tools/claude.py` (新規)
- `src/ai_tools/gemini.py` (新規)
- `src/ai_tools/genspark.py` (新規)
- `src/ai_tools/google_ai_studio.py` (新規)

**既存のchatgpt.pyとbrowser_manager.pyは触らない！**

### チームC: 統合処理の接続
**作業ファイル:**
- `src/process_coordinator.py` (新規 - orchestrator.pyとは別)
- `src/gui/processing_thread.py` (新規)

**既存のmain_window.pyとorchestrator.pyは触らない！**

---

# チームA: Sheets接続作業

## reader.py (新規作成)
```python
"""
Google Sheets読み取り専用モジュール
既存のGoogleSheetsClientを使用してデータ読み取りを行う
"""
from src.sheets.google_sheets_client import GoogleSheetsClient
from typing import List

class SheetReader:
    def __init__(self, client: GoogleSheetsClient):
        self.client = client
    
    def read_all_data(self, spreadsheet_id: str, sheet_name: str) -> List[List[str]]:
        """シート全体を読み取り（既存のread_sheet_dataを使用）"""
        return self.client.read_sheet_data(spreadsheet_id, f"{sheet_name}!A1:Z1000")
```

## writer.py (新規作成)
```python
"""
Google Sheets書き込み専用モジュール
既存のGoogleSheetsClientを使用してデータ書き込みを行う
"""
from src.sheets.google_sheets_client import GoogleSheetsClient
from typing import List, Dict

class SheetWriter:
    def __init__(self, client: GoogleSheetsClient):
        self.client = client
    
    def write_cell(self, spreadsheet_id: str, sheet_name: str, row: int, col: int, value: str):
        """単一セルへの書き込み"""
        # A1表記に変換
        col_letter = chr(ord('A') + col - 1)
        range_name = f"{sheet_name}!{col_letter}{row}"
        self.client.write_sheet_data(spreadsheet_id, range_name, [[value]])
    
    def mark_processed(self, spreadsheet_id: str, sheet_name: str, row: int, process_col: int):
        """処理済みマークを付ける"""
        self.write_cell(spreadsheet_id, sheet_name, row, process_col, "処理済み")
```

## column_detector.py (新規作成)
```python
"""
列検出専用モジュール
スプレッドシートから作業指示行とコピー列を検出
"""
from typing import List, Dict, Optional

class ColumnDetector:
    def find_work_instruction_row(self, sheet_data: List[List[str]]) -> int:
        """作業指示行（5行目でA列が「作業指示行」）を検出"""
        if len(sheet_data) < 5:
            return -1
        
        # 5行目（インデックス4）をチェック
        if sheet_data[4] and sheet_data[4][0] == "作業指示行":
            return 4
        
        # 見つからない場合は全行を検索
        for i, row in enumerate(sheet_data):
            if row and row[0] == "作業指示行":
                return i
        
        return -1
    
    def find_copy_columns(self, header_row: List[str]) -> List[int]:
        """「コピー」列のインデックスリストを返す"""
        copy_columns = []
        for i, cell in enumerate(header_row):
            if cell == "コピー":
                copy_columns.append(i)
        return copy_columns
    
    def get_related_columns(self, copy_col_index: int) -> Dict[str, int]:
        """コピー列に関連する列のインデックスを計算"""
        return {
            'process': max(0, copy_col_index - 2),  # 処理列
            'error': max(0, copy_col_index - 1),    # エラー列  
            'paste': copy_col_index + 1              # 貼り付け列
        }
```

---

# チームB: AI接続作業

## 基本テンプレート（各AIツール共通）
```python
"""
[AI名]自動操作ツール
既存のAIToolBaseとBrowserManagerを使用
"""
from src.ai_tools.base import AIToolBase
from src.ai_tools.browser_manager import BrowserManager
import asyncio

class [AI名]Tool(AIToolBase):
    URL = "[AIのURL]"
    
    def __init__(self, browser_manager: BrowserManager):
        super().__init__("[AI名]")
        self.browser_manager = browser_manager
        self.selectors = {
            'input': '[入力欄のセレクター]',
            'send_button': '[送信ボタンのセレクター]',
            'response': '[応答表示エリアのセレクター]'
        }
    
    async def login(self) -> bool:
        """既存のChromeプロファイルでログイン済みを確認"""
        self.page = await self.browser_manager.create_page(self.name.lower(), self.URL)
        await asyncio.sleep(3)
        
        # ログイン確認（入力欄が表示されていればOK）
        if await self.wait_for_element(self.selectors['input'], timeout=10):
            self.is_logged_in = True
            return True
        return False
    
    async def send_prompt(self, text: str) -> str:
        """プロンプト送信（ChatGPTの実装を参考に）"""
        # 1. 入力欄にテキスト入力
        await self.page.fill(self.selectors['input'], text)
        
        # 2. 送信
        await self.page.click(self.selectors['send_button'])
        
        # 3. 応答待機
        await self.wait_for_response_complete()
        
        # 4. 応答取得
        response_element = await self.page.query_selector(self.selectors['response'])
        if response_element:
            return await response_element.inner_text()
        return ""
```

## claude.py
```python
# 上記テンプレートを使用
# URL = "https://claude.ai"
# セレクター:
#   input: 'div[contenteditable="true"]'
#   send_button: 'button[aria-label="Send"]'
#   response: 'div[data-testid="chat-message-assistant"]:last-child'
```

## gemini.py
```python
# 上記テンプレートを使用
# URL = "https://gemini.google.com"
# セレクター:
#   input: 'rich-textarea .ql-editor'
#   send_button: 'button[aria-label="Send message"]'
#   response: '.model-response-container:last-child'
```

---

# チームC: 統合接続作業

## process_coordinator.py (新規作成)
```python
"""
処理コーディネーター
既存のモジュールを接続して処理フローを実現
"""
from src.sheets.google_sheets_client import GoogleSheetsClient
from src.sheets.reader import SheetReader
from src.sheets.writer import SheetWriter
from src.sheets.column_detector import ColumnDetector
from src.ai_tools.browser_manager import BrowserManager
from typing import Dict, List, Callable
import asyncio

class ProcessCoordinator:
    def __init__(self):
        # 既存モジュールを使用
        self.sheets_client = GoogleSheetsClient()
        self.reader = SheetReader(self.sheets_client)
        self.writer = SheetWriter(self.sheets_client)
        self.detector = ColumnDetector()
        self.browser_manager = BrowserManager()
        self.ai_tools = {}
        
    def setup_sheets(self, credentials_path: str):
        """Sheets認証設定"""
        self.sheets_client.authenticate(credentials_path)
    
    async def setup_ai_tools(self, ai_configs: Dict):
        """AIツール初期化（有効なもののみ）"""
        for ai_name, config in ai_configs.items():
            if config.get('enabled'):
                # 動的インポート
                module = __import__(f'src.ai_tools.{ai_name.lower().replace(" ", "_")}', fromlist=[f'{ai_name.replace(" ", "")}Tool'])
                tool_class = getattr(module, f'{ai_name.replace(" ", "")}Tool')
                self.ai_tools[ai_name] = tool_class(self.browser_manager)
                await self.ai_tools[ai_name].login()
    
    async def process_sheet(self, url: str, sheet_name: str, progress_callback: Callable):
        """メイン処理フロー"""
        # 1. スプレッドシートID抽出
        spreadsheet_id = url.split('/d/')[1].split('/')[0]
        
        # 2. データ読み取り
        sheet_data = self.reader.read_all_data(spreadsheet_id, sheet_name)
        
        # 3. 作業指示行検出
        work_row = self.detector.find_work_instruction_row(sheet_data)
        if work_row == -1:
            raise ValueError("作業指示行が見つかりません")
        
        # 4. コピー列検出
        copy_columns = self.detector.find_copy_columns(sheet_data[work_row])
        
        # 5. 各コピー列を処理
        for copy_col in copy_columns:
            cols = self.detector.get_related_columns(copy_col)
            
            # 6. データ行を処理（A列が1から始まる行）
            row_num = work_row + 2  # 作業指示行の次の行から
            while row_num < len(sheet_data):
                if not sheet_data[row_num] or not sheet_data[row_num][0]:
                    break
                
                if sheet_data[row_num][0] == "1":  # 処理開始
                    # 処理列チェック
                    process_status = sheet_data[row_num][cols['process']] if cols['process'] < len(sheet_data[row_num]) else ""
                    if process_status in ["", "未処理"]:
                        # AI処理実行
                        copy_text = sheet_data[row_num][copy_col]
                        ai_tool = list(self.ai_tools.values())[0]  # 最初の有効なAIを使用
                        
                        try:
                            response = await ai_tool.send_prompt(copy_text)
                            # 結果書き込み
                            self.writer.write_cell(spreadsheet_id, sheet_name, row_num + 1, cols['paste'] + 1, response)
                            self.writer.mark_processed(spreadsheet_id, sheet_name, row_num + 1, cols['process'] + 1)
                        except Exception as e:
                            # エラー記録
                            self.writer.write_cell(spreadsheet_id, sheet_name, row_num + 1, cols['error'] + 1, str(e))
                
                row_num += 1
```

## processing_thread.py (新規作成)
```python
"""
GUI用処理スレッド
メインウィンドウから呼び出される処理を実装
"""
import threading
import asyncio
from src.process_coordinator import ProcessCoordinator

class ProcessingThread(threading.Thread):
    def __init__(self, config: Dict, callbacks: Dict):
        super().__init__(daemon=True)
        self.config = config
        self.callbacks = callbacks
        self.coordinator = ProcessCoordinator()
        
    def run(self):
        """スレッドのメイン処理"""
        asyncio.run(self._async_process())
    
    async def _async_process(self):
        """非同期処理本体"""
        try:
            # 進捗通知
            self.callbacks['progress'](0, 100, "初期化中...")
            
            # Sheets設定
            self.coordinator.setup_sheets("credentials.json")
            
            # AI設定
            await self.coordinator.setup_ai_tools(self.config['ai_tools'])
            
            # 処理実行
            await self.coordinator.process_sheet(
                self.config['spreadsheet']['url'],
                self.config['spreadsheet']['sheet_name'],
                self.callbacks['progress']
            )
            
            self.callbacks['complete']("処理が完了しました")
            
        except Exception as e:
            self.callbacks['error'](str(e))
```

---

## 統合時の注意点

1. **既存ファイルは絶対に編集しない**
2. **新規ファイルのみ作成する**
3. **インポートは既存モジュールから行う**
4. **テストは最後に統合テストで確認**

## Gitブランチ
```bash
# 各チーム専用ブランチ
git checkout -b integration/team-a-sheets
git checkout -b integration/team-b-ai
git checkout -b integration/team-c-coordinator
```

これで各チームが独立して作業でき、ファイルコンフリクトは発生しません！