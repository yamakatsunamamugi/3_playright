# 並行開発指示書

## 統括者D - 初期準備完了報告

以下の初期準備が完了しました：

### ✅ 作成済みファイル

#### インターフェース定義
- `src/interfaces/sheet_interface.py` - チームB用インターフェース
- `src/interfaces/ai_interface.py` - チームC用インターフェース  
- `src/interfaces/gui_interface.py` - チームA用インターフェース

#### モックファイル
- `tests/mocks/mock_sheet_processor.py` - チームA・C用のシート処理モック
- `tests/mocks/mock_ai_tools.py` - チームA・B用のAIツールモック

#### 統合準備
- `src/orchestrator.py` - 統合時のメインコントローラー（雛形）
- `tests/test_integration.py` - 統合テスト

---

## 各チームへの指示

### 🔵 チームA（GUI担当）へ

#### ブランチ作成
```bash
git checkout main
git pull origin main
git checkout -b feature/gui-enhancement
```

#### 今すぐ開始できること
1. **モックを使った開発**
   - `tests/mocks/mock_sheet_processor.py`をimportして使用
   - `tests/mocks/mock_ai_tools.py`をimportして使用

2. **最初に実装すべき機能**
   ```python
   # src/gui/widgets/ai_config_widget.py
   from src.interfaces.gui_interface import IGUIController
   
   class AIConfigWidget:
       def __init__(self, parent):
           # AI選択チェックボックス
           # モデル選択ドロップダウン
           # 設定ボタン
   ```

3. **テスト方法**
   ```python
   # テスト用コード例
   from tests.mocks.mock_ai_tools import MockAIManager
   
   ai_manager = MockAIManager()
   tools = ai_manager.get_supported_tools()
   # -> ['ChatGPT', 'Claude', 'Gemini', 'Genspark', 'Google AI Studio']
   ```

#### 担当ファイル
- `src/gui/main_window.py` （既存・拡張）
- `src/gui/widgets/ai_config_widget.py` （新規）
- `src/gui/widgets/progress_widget.py` （新規）
- `src/gui/main_controller.py` （新規）

---

### 🟢 チームB（Sheets担当）へ

#### ブランチ作成
```bash
git checkout main
git pull origin main
git checkout -b feature/sheets-processing
```

#### 最初に実装すべきインターフェース
```python
# src/sheets/processor.py
from src.interfaces.sheet_interface import ISheetProcessor

class SpreadsheetProcessor(ISheetProcessor):
    def find_work_instruction_row(self, sheet_data):
        # A列に「作業指示行」がある行を検索
        pass
    
    def find_copy_columns(self, header_row):
        # 「コピー」と完全一致する列のインデックスリストを返す
        pass
```

#### テスト用データ
```python
# テスト用のスプレッドシートデータ例
test_data = [
    ["", "", "", "", ""],
    ["", "", "", "", ""],
    ["", "", "", "", ""],
    ["", "", "", "", ""],
    ["作業指示行", "コピー", "処理", "エラー", "コピー", "貼り付け"],
    ["1", "プロンプト1", "", "", "プロンプト2", ""],
    ["2", "プロンプト3", "", "", "プロンプト4", ""],
]
```

#### 担当ファイル
- `src/sheets/processor.py` （新規）
- `src/sheets/data_handler.py` （新規）
- `src/sheets/validator.py` （新規）
- `src/utils/retry_handler.py` （新規）

---

### 🔴 チームC（Automation担当）へ

#### ブランチ作成
```bash
git checkout main
git pull origin main
git checkout -b feature/ai-automation
```

#### Playwrightセットアップ
```bash
pip install playwright
playwright install chromium
```

#### 最初に実装すべき基底クラス
```python
# src/ai_tools/base.py
from src.interfaces.ai_interface import IAITool, AIToolStatus

class AIToolBase(IAITool):
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.browser = None
        self.page = None
        
    async def initialize(self, profile_path=None):
        # Playwright初期化
        pass
```

#### ChatGPT実装例
```python
# src/ai_tools/chatgpt.py
class ChatGPTTool(AIToolBase):
    URL = "https://chat.openai.com"
    
    SELECTORS = {
        'input': 'textarea[data-id="root"]',
        'send_button': 'button[data-testid="send-button"]',
        'response': '.markdown.prose'
    }
```

#### 担当ファイル
- `src/ai_tools/base.py` （新規）
- `src/ai_tools/browser_manager.py` （新規）
- `src/ai_tools/chatgpt.py` （新規）
- `src/ai_tools/claude.py` （新規）
- 他のAIツールモジュール

---

## 共通ルール

### Git管理
1. **毎日の作業開始時**
   ```bash
   git pull origin main
   git merge main  # 最新の変更を取り込む
   ```

2. **コミット規則**
   ```bash
   # チームA
   git commit -m "[GUI] feat: AI設定ウィジェットの実装"
   
   # チームB  
   git commit -m "[SHEETS] feat: 作業指示行検出機能の実装"
   
   # チームC
   git commit -m "[AI] feat: ChatGPT自動操作の実装"
   ```

3. **1日の終わりにプッシュ**
   ```bash
   git push origin feature/ブランチ名
   ```

### 開発の進め方
1. **インターフェースを必ず参照**
2. **モックを使って独立開発**
3. **毎日の進捗共有（15分）**
4. **問題があれば即座に報告**

### テスト実行
```bash
# 統合テストの実行（統括者D用）
python -m pytest tests/test_integration.py -v

# 個別のモックテスト
python tests/mocks/mock_sheet_processor.py
python tests/mocks/mock_ai_tools.py
```

---

## 次のステップ

### Day 1-3: 各チーム並行開発
- 各チームは自分の担当部分を実装
- インターフェースに従った実装
- モックを使ったテスト

### Day 4-5: 初回統合
- 統括者Dが各ブランチをマージ
- 結合テストの実行
- 問題点の洗い出し

### Day 6-7: 調整・最適化
- バグ修正
- パフォーマンス改善
- ユーザビリティ向上

これで各チームが効率的に並行開発を進められます！