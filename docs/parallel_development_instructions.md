# Google Sheets AI自動化ツール - 並行開発指示書

## 概要
本ドキュメントは、3つのAIチーム（A、B、C）が並行して開発作業を進めるための詳細な指示書です。
各チームは独立して作業を進められるよう、明確なインターフェースと責任範囲を定義しています。

## 現在の完成状況
- ✅ プロジェクト構造: 完成
- ✅ Python環境設定: 完成
- ✅ Google Sheets API認証: 基本実装完成
- ✅ GUI基本フレームワーク: 完成（tkinter実装）
- ✅ ログシステム: 完成

## 作業分担

### チームA: Google Sheets処理とデータ管理
**責任範囲**: スプレッドシートのデータ読み取り、処理、書き込み機能の実装

### チームB: AI自動化基盤とブラウザ制御
**責任範囲**: Playwright/Seleniumを使用したブラウザ自動化とAIツール操作の基盤実装

### チームC: 統合とエラーハンドリング
**責任範囲**: 各モジュールの統合、エラーハンドリング、リトライ機能、全体的な処理フローの実装

---

# チームA: Google Sheets処理実装指示書

## 1. 作業概要
Google Sheetsのデータ読み取り、処理列の検出、結果の書き込み機能を実装します。

## 2. 実装ファイル
- `src/sheets/processor.py` - メイン処理ロジック（既存）
- `src/sheets/reader.py` - データ読み取り機能（新規作成）
- `src/sheets/writer.py` - データ書き込み機能（新規作成）
- `src/sheets/column_detector.py` - 列検出ロジック（新規作成）

## 3. 実装すべき機能

### 3.1 データ読み取り機能 (reader.py)
```python
class SheetReader:
    def __init__(self, credentials_path: str):
        """Google Sheets APIクライアントを初期化"""
        pass
    
    def read_sheet(self, spreadsheet_id: str, sheet_name: str) -> List[List[str]]:
        """シート全体を読み取り"""
        pass
    
    def read_range(self, spreadsheet_id: str, range_name: str) -> List[List[str]]:
        """指定範囲を読み取り"""
        pass
```

### 3.2 列検出機能 (column_detector.py)
```python
class ColumnDetector:
    def find_work_instruction_row(self, sheet_data: List[List[str]]) -> int:
        """
        作業指示行を見つける
        - 5行目をチェック
        - A列に「作業指示行」というテキストがある行を探す
        - 見つからない場合は-1を返す
        """
        pass
    
    def find_copy_columns(self, header_row: List[str]) -> List[int]:
        """
        「コピー」列をすべて見つける
        - ヘッダー行から「コピー」というテキストを持つ列のインデックスリストを返す
        """
        pass
    
    def calculate_related_columns(self, copy_column_index: int) -> Dict[str, int]:
        """
        コピー列に関連する列のインデックスを計算
        返り値: {
            'process': copy_column_index - 2,  # 処理列
            'error': copy_column_index - 1,    # エラー列
            'paste': copy_column_index + 1     # 貼り付け列
        }
        """
        pass
```

### 3.3 データ書き込み機能 (writer.py)
```python
class SheetWriter:
    def __init__(self, credentials_path: str):
        """Google Sheets APIクライアントを初期化"""
        pass
    
    def write_cell(self, spreadsheet_id: str, range_name: str, value: str):
        """単一セルに書き込み"""
        pass
    
    def write_batch(self, spreadsheet_id: str, updates: List[Dict[str, str]]):
        """
        バッチ更新
        updates = [{'range': 'A1', 'value': 'text'}, ...]
        """
        pass
    
    def mark_as_processed(self, spreadsheet_id: str, sheet_name: str, row: int, col: int):
        """処理済みマークを付ける"""
        pass
```

### 3.4 メイン処理ロジックの更新 (processor.py)
既存の `SheetProcessor` クラスに以下のメソッドを実装：

```python
def process_spreadsheet(self, url: str, sheet_name: str, ai_handler_callback: Callable):
    """
    スプレッドシート処理のメインロジック
    
    1. シートデータを読み取る
    2. 作業指示行を見つける
    3. コピー列をすべて見つける
    4. 各コピー列に対して：
       - A列が「1」の行から処理開始
       - 処理列が空白または「未処理」の行を処理
       - コピー列のテキストをai_handler_callbackに渡す
       - 結果を貼り付け列に書き込む
       - エラーの場合はエラー列に記録
       - 処理列に「処理済み」を記録
    """
    pass
```

## 4. エラーハンドリング要件
- Google Sheets APIのレート制限（100リクエスト/分）を考慮
- ネットワークエラーは自動リトライ（最大3回）
- 認証エラーは即座に上位に伝播
- すべてのエラーはログに詳細を記録

## 5. テストデータ
`tests/data/sample_spreadsheet.json` に以下の形式でテストデータを作成：
```json
{
    "sheets": [
        {
            "name": "メインシート",
            "data": [
                ["", "", "", "", ""],
                ["", "", "", "", ""],
                ["", "", "", "", ""],
                ["", "", "", "", ""],
                ["作業指示行", "データ1", "処理", "エラー", "コピー", "貼り付け"],
                ["1", "テストデータ1", "", "", "こんにちは、AIです", ""],
                ["2", "テストデータ2", "", "", "天気はどうですか？", ""],
                ["3", "テストデータ3", "処理済み", "", "計算してください", "結果"],
                ["", "", "", "", "", ""]
            ]
        }
    ]
}
```

## 6. 必要な依存関係
```python
google-auth>=2.23.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
google-api-python-client>=2.100.0
```

---

# チームB: AI自動化基盤実装指示書

## 1. 作業概要
Playwrightを使用したブラウザ自動化基盤と、5つのAIツールの操作モジュールを実装します。

## 2. 実装ファイル
- `src/ai_tools/browser_manager.py` - ブラウザ管理（既存）
- `src/ai_tools/chatgpt.py` - ChatGPT操作（既存・要更新）
- `src/ai_tools/claude.py` - Claude操作（新規作成）
- `src/ai_tools/gemini.py` - Gemini操作（新規作成）
- `src/ai_tools/genspark.py` - Genspark操作（新規作成）
- `src/ai_tools/google_ai_studio.py` - Google AI Studio操作（新規作成）

## 3. 実装すべき機能

### 3.1 ブラウザマネージャーの強化 (browser_manager.py)
```python
class BrowserManager:
    def __init__(self, browser_type: str = "chromium", use_existing_profile: bool = True):
        """
        ブラウザマネージャーを初期化
        - 既存のChromeプロファイルを使用（ログイン状態を維持）
        - macOSのChromeプロファイルパス: ~/Library/Application Support/Google/Chrome/Default
        """
        pass
    
    async def get_browser_context(self, profile_name: str = "default"):
        """プロファイル別のブラウザコンテキストを取得"""
        pass
    
    async def create_page(self, context_name: str, url: str):
        """新しいページを作成して指定URLにアクセス"""
        pass
```

### 3.2 各AIツールの実装仕様

#### Claude (claude.py)
```python
class ClaudeTool(AIToolBase):
    URL = "https://claude.ai"
    
    async def login(self) -> bool:
        """既存のブラウザセッションでログイン確認"""
        pass
    
    async def get_available_models(self) -> List[str]:
        """利用可能なモデルリストを取得"""
        # Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus など
        pass
    
    async def send_prompt(self, text: str) -> str:
        """プロンプト送信と応答取得"""
        # セレクター例:
        # 入力: 'div[contenteditable="true"]'
        # 送信: 'button[aria-label="Send"]'
        # 応答: 'div[data-testid="chat-message-assistant"]'
        pass
```

#### Gemini (gemini.py)
```python
class GeminiTool(AIToolBase):
    URL = "https://gemini.google.com"
    
    # 実装内容はClaudeと同様の構造
    # セレクター例:
    # 入力: 'div[contenteditable="true"].ql-editor'
    # 送信: 'button[aria-label="Send message"]'
    # 応答: 'div.model-response-text'
```

#### Genspark (genspark.py)
```python
class GensparkTool(AIToolBase):
    URL = "https://www.genspark.ai"
    
    # 実装内容は他のAIツールと同様
    # サイトの実際のDOM構造に基づいてセレクターを調整
```

#### Google AI Studio (google_ai_studio.py)
```python
class GoogleAIStudioTool(AIToolBase):
    URL = "https://aistudio.google.com"
    
    # 実装内容は他のAIツールと同様
    # APIキーベースの可能性もあるため、両方に対応
```

### 3.3 共通機能の実装
各AIツールクラスは `AIToolBase` を継承し、以下の共通メソッドを実装：

```python
async def wait_for_element(self, selector: str, timeout: int = 30) -> bool:
    """要素の出現を待機"""
    pass

async def wait_for_response_complete(self, timeout: int = 120) -> bool:
    """AIの応答完了を待機（ストリーミング対応）"""
    pass

async def handle_rate_limit(self):
    """レート制限への対処"""
    pass

async def clear_conversation(self) -> bool:
    """会話履歴をクリア"""
    pass
```

## 4. セレクター取得方法
1. 各AIサイトにアクセス
2. Chrome DevToolsを開く（F12）
3. Elements タブで要素を右クリック → Copy → Copy selector
4. 動的に変わる可能性があるため、複数の候補を用意

## 5. エラーハンドリング要件
- タイムアウト: デフォルト30秒、応答待機は120秒
- セレクター変更対応: 複数のセレクター候補を試行
- ネットワークエラー: 自動リトライ（最大3回）
- ログイン失敗: ユーザーに手動ログインを促す

## 6. テスト方法
```python
# tests/test_ai_tools.py
async def test_chatgpt_basic_flow():
    """ChatGPTの基本フローテスト"""
    tool = ChatGPTTool(browser_manager)
    assert await tool.login()
    models = await tool.get_available_models()
    assert len(models) > 0
    response = await tool.send_prompt("Hello, this is a test")
    assert len(response) > 0
```

## 7. 必要な依存関係
```python
playwright>=1.40.0
asyncio>=3.11.0
```

---

# チームC: 統合とエラーハンドリング実装指示書

## 1. 作業概要
各モジュールを統合し、エラーハンドリング、リトライ機能、全体的な処理フローを実装します。

## 2. 実装ファイル
- `src/orchestrator.py` - メイン処理オーケストレーター（既存・要更新）
- `src/error_handler.py` - エラーハンドリング機能（新規作成）
- `src/retry_manager.py` - リトライ管理（新規作成）
- `src/gui/main_window.py` - GUI統合（既存・要更新）

## 3. 実装すべき機能

### 3.1 エラーハンドラー (error_handler.py)
```python
class ErrorHandler:
    def __init__(self):
        self.error_counts = {}
        self.error_history = []
    
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> ErrorAction:
        """
        エラーを分類して適切なアクションを決定
        
        ErrorAction:
        - RETRY: リトライ可能
        - SKIP: スキップして次へ
        - ABORT: 処理中断
        - MANUAL: ユーザー介入必要
        """
        pass
    
    def classify_error(self, error: Exception) -> ErrorType:
        """
        エラーを分類
        - NETWORK: ネットワークエラー
        - AUTHENTICATION: 認証エラー
        - RATE_LIMIT: レート制限
        - SELECTOR: セレクターエラー
        - TIMEOUT: タイムアウト
        - UNKNOWN: 不明なエラー
        """
        pass
```

### 3.2 リトライマネージャー (retry_manager.py)
```python
class RetryManager:
    def __init__(self, max_retries: int = 5, base_delay: int = 10):
        """
        リトライマネージャーを初期化
        - max_retries: 最大リトライ回数
        - base_delay: 基本待機時間（秒）
        """
        pass
    
    async def retry_with_backoff(self, func: Callable, *args, **kwargs):
        """
        エクスポネンシャルバックオフでリトライ
        - 1回目: 10秒待機
        - 2回目: 20秒待機
        - 3回目: 40秒待機...
        """
        pass
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """リトライすべきか判定"""
        pass
```

### 3.3 オーケストレーター更新 (orchestrator.py)
```python
class Orchestrator:
    def __init__(self):
        self.sheet_processor = None
        self.ai_tools = {}
        self.error_handler = ErrorHandler()
        self.retry_manager = RetryManager()
        self.progress_callback = None
        self.log_callback = None
    
    async def process_spreadsheet(self, config: Dict[str, Any]):
        """
        メイン処理フロー
        
        1. 設定の検証
        2. Google Sheetsへの接続
        3. AIツールの初期化
        4. 作業指示行とコピー列の検出
        5. 各行の処理：
           - 処理対象チェック
           - AIツールへのプロンプト送信
           - 結果の書き込み
           - エラーハンドリング
        6. 完了処理
        """
        pass
    
    async def process_single_cell(self, row_data: Dict[str, Any], ai_tool: AIToolBase):
        """
        単一セルの処理（リトライ機能付き）
        """
        try:
            # リトライマネージャーを使用
            result = await self.retry_manager.retry_with_backoff(
                ai_tool.send_prompt,
                row_data['copy_text']
            )
            return result
        except Exception as e:
            # エラーハンドラーで処理
            action = self.error_handler.handle_error(e, row_data)
            return self._handle_error_action(action, e, row_data)
```

### 3.4 GUI統合更新 (main_window.py の _process_data メソッド)
```python
def _process_data(self):
    """処理実行スレッド"""
    try:
        # 設定を収集
        config = {
            'spreadsheet': {
                'url': self.spreadsheet_widget.get_values()[0],
                'sheet_name': self.spreadsheet_widget.get_values()[1]
            },
            'ai_tools': self.ai_config_panel.get_all_configs(),
            'processing': {
                'retry_count': 5,
                'retry_delay': 10,
                'timeout': 120
            }
        }
        
        # オーケストレーター作成
        orchestrator = Orchestrator()
        
        # プログレスコールバック設定
        orchestrator.progress_callback = lambda current, total, message: 
            self.root.after(0, self._update_progress, current, total, message)
        
        # ログコールバック設定
        orchestrator.log_callback = lambda message, level: 
            self.root.after(0, self.add_log, message, level)
        
        # 非同期処理を実行
        asyncio.run(orchestrator.process_spreadsheet(config))
        
    except Exception as e:
        self.root.after(0, self._handle_processing_error, e)
```

## 4. エラー処理フロー
```
1. エラー発生
   ↓
2. ErrorHandler.classify_error() でエラー分類
   ↓
3. エラータイプに応じた処理:
   - NETWORK/TIMEOUT → RetryManager でリトライ
   - AUTHENTICATION → ユーザーに通知、処理中断
   - RATE_LIMIT → 長時間待機後リトライ
   - SELECTOR → 代替セレクター試行
   ↓
4. リトライ失敗時:
   - エラー列に記録
   - 次の行/列へ継続
   ↓
5. 致命的エラー時:
   - 処理中断
   - ユーザーに詳細通知
```

## 5. 進捗管理
```python
# 進捗計算例
total_cells = len(copy_columns) * len(target_rows)
current_cell = 0

for col_idx, copy_column in enumerate(copy_columns):
    for row_idx, row in enumerate(target_rows):
        current_cell += 1
        progress_percent = (current_cell / total_cells) * 100
        
        # GUIに進捗を通知
        progress_callback(
            current_cell, 
            total_cells, 
            f"処理中: 列{col_idx+1}/{len(copy_columns)}, 行{row_idx+1}/{len(target_rows)}"
        )
```

## 6. ログ出力仕様
```python
# ログレベルと内容
logger.debug(f"セレクター検索: {selector}")
logger.info(f"処理開始: {sheet_name}")
logger.warning(f"リトライ {attempt}/{max_retries}: {error}")
logger.error(f"処理失敗: 行{row} 列{col} - {error}")
```

## 7. 設定ファイル更新
`config.json` に以下を追加：
```json
{
    "error_handling": {
        "max_consecutive_errors": 10,
        "abort_on_auth_error": true,
        "skip_on_selector_error": false
    },
    "performance": {
        "batch_size": 10,
        "parallel_ai_requests": false,
        "rate_limit_delay": 1.0
    }
}
```

---

## 共通注意事項

### 1. コーディング規約
- PEP 8 準拠
- 型ヒントを必ず使用
- docstringは日本語で記述
- エラーメッセージは日本語

### 2. ログ出力
- すべての重要な処理でログ出力
- エラーは必ず詳細情報を含める
- デバッグログは開発時のみ有効

### 3. テスト
- 各モジュールに単体テストを作成
- モックを使用してAIサイトへの実アクセスを避ける
- 統合テストは手動で実施

### 4. Git運用
```bash
# 各チームのブランチ
git checkout -b feature/team-a-sheets
git checkout -b feature/team-b-ai-tools  
git checkout -b feature/team-c-integration

# 作業完了後
git add .
git commit -m "feat: [チーム名] 実装内容の説明"
git push origin feature/team-x-xxx
```

### 5. 連携ポイント
- チームA → チームC: SheetProcessor のインターフェース
- チームB → チームC: AIToolBase のインターフェース
- チームC → チームA/B: エラーハンドリング要件

### 6. 質問・確認事項
各チームは以下のチャンネルで連携：
- Slack: #sheets-ai-automation
- 定期同期: 毎日10:00 JST
- 緊急時: @mention で通知

---

## 開始手順

1. このドキュメントを熟読
2. 担当ブランチを作成
3. 既存コードを確認
4. 実装開始
5. 単体テスト作成
6. プルリクエスト提出

質問があれば遠慮なく確認してください。