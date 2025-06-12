# 担当者B（テスト・検証担当）作業指示書

## 1. 担当範囲（専任ファイル）

### 1.1 新規作成ファイル
- `tests/test_orchestrator.py` - Orchestratorの単体テスト
- `tests/test_e2e.py` - エンドツーエンドテスト
- `tests/test_process_manager.py` - ProcessManagerのテスト
- `tests/fixtures/test_data.json` - テスト用データ
- `tests/conftest.py` - pytest設定とフィクスチャ

### 1.2 修正担当ファイル
- `tests/test_integration.py` - 統合テストの拡充
- `.github/workflows/test.yml` - CI/CDテスト設定（新規作成）

## 2. 作業詳細

### 2.1 事前準備
```bash
# 最新のintegrationブランチに切り替え
git checkout feature/integration
git pull origin feature/integration

# 作業用サブブランチを作成
git checkout -b feature/integration-tests
```

### 2.2 test_orchestrator.py の実装

```python
"""
tests/test_orchestrator.py
Orchestratorクラスの単体テスト
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.orchestrator import Orchestrator

class TestOrchestrator:
    """Orchestratorのテストクラス"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Orchestratorのフィクスチャ"""
        orch = Orchestrator()
        await orch.initialize()
        yield orch
        await orch.stop()
        
    @pytest.mark.asyncio
    async def test_initialize(self, orchestrator):
        """初期化テスト"""
        assert orchestrator.sheet_processor is not None
        assert orchestrator.browser_manager is not None
        assert orchestrator.is_running is False
        
    @pytest.mark.asyncio
    async def test_process_spreadsheet_success(self, orchestrator):
        """正常系：スプレッドシート処理"""
        # モックの設定
        with patch.object(orchestrator.sheet_processor, 'load_sheet') as mock_load:
            mock_load.return_value = [
                ["作業指示行", "A", "B", "コピー", "貼り付け"],
                ["1", "データ1", "未処理", "テキスト1", ""],
                ["2", "データ2", "未処理", "テキスト2", ""]
            ]
            
            result = await orchestrator.process_spreadsheet(
                "https://example.com/sheet",
                "Sheet1",
                {"ChatGPT": {"enabled": True, "model": "gpt-4"}}
            )
            
            assert result["success"] is True
            assert result["processed_rows"] > 0
            
    @pytest.mark.asyncio
    async def test_process_spreadsheet_error(self, orchestrator):
        """異常系：エラーハンドリング"""
        with patch.object(orchestrator.sheet_processor, 'load_sheet') as mock_load:
            mock_load.side_effect = Exception("接続エラー")
            
            result = await orchestrator.process_spreadsheet(
                "https://example.com/sheet",
                "Sheet1",
                {}
            )
            
            assert result["success"] is False
            assert len(result["errors"]) > 0
            assert "接続エラー" in result["errors"][0]
```

### 2.3 test_e2e.py の実装

```python
"""
tests/test_e2e.py
エンドツーエンドテスト
"""

import pytest
from unittest.mock import patch
from src.gui.main_window import MainWindow
from src.orchestrator import Orchestrator

class TestE2E:
    """E2Eテストクラス"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_workflow(self, qtbot):
        """完全なワークフローのテスト"""
        # GUIの起動
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        
        # スプレッドシートURL入力
        window.sheet_widget.url_input.setText("https://example.com/sheet")
        
        # AI設定
        window.ai_widget.ai_configs["ChatGPT"]["enabled"] = True
        
        # 処理開始
        with patch('src.sheets.client.SheetsClient.read_sheet'):
            window.start_processing()
            
            # 処理完了を待つ
            qtbot.wait(5000)  # 5秒待機
            
            # 結果確認
            assert window.status_bar.currentMessage() == "処理が完了しました"
```

### 2.4 conftest.py の実装

```python
"""
tests/conftest.py
pytest共通設定とフィクスチャ
"""

import pytest
import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(scope="session")
def event_loop():
    """非同期テスト用のイベントループ"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_sheet_data():
    """テスト用シートデータ"""
    return [
        ["", "", "", "作業指示行", "", "", ""],
        ["", "", "", "", "", "", ""],
        ["", "", "", "", "", "", ""],
        ["", "", "", "", "", "", ""],
        ["作業", "データ", "処理", "エラー", "コピー", "貼り付け", ""],
        ["1", "テスト1", "未処理", "", "入力テキスト1", "", ""],
        ["2", "テスト2", "未処理", "", "入力テキスト2", "", ""],
        ["3", "テスト3", "未処理", "", "入力テキスト3", "", ""],
    ]

@pytest.fixture
def mock_ai_response():
    """AI応答のモック"""
    return {
        "response": "これはAIの応答です",
        "model": "gpt-4",
        "tokens": 150
    }
```

### 2.5 GitHub Actions テスト設定

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, feature/integration ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-qt pytest-cov
        
    - name: Run tests
      run: |
        pytest tests/ -v --cov=src --cov-report=xml
        
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 3. Git管理

### 3.1 コミット規則
```bash
# テストファイル追加
git add tests/test_orchestrator.py
git commit -m "test: Orchestratorの単体テスト追加"

git add tests/test_e2e.py
git commit -m "test: E2Eテストの実装"

# CI/CD設定
git add .github/workflows/test.yml
git commit -m "ci: GitHub Actionsでのテスト自動化設定"
```

### 3.2 テスト実行とレポート
```bash
# 全テスト実行
pytest tests/ -v

# カバレッジ付き実行
pytest tests/ --cov=src --cov-report=html

# 特定のテストのみ
pytest tests/test_orchestrator.py -v
```

## 4. 他担当者との連携

### 4.1 A担当者との連携
- Orchestratorの実装完了を待ってテスト作成
- インターフェース変更時は即座に対応

### 4.2 C担当者との連携
- ドキュメントに記載するテスト実行方法を提供
- テストカバレッジレポートを共有

## 5. 完了条件
- [ ] 全モジュールの単体テスト（カバレッジ80%以上）
- [ ] E2Eテストの実装と成功
- [ ] CI/CD設定の完了
- [ ] テストドキュメントの作成
- [ ] 全テストがグリーン

## 6. 注意事項
- モックを適切に使用し、外部依存を排除
- 非同期テストは必ず@pytest.mark.asyncioを使用
- テストは独立して実行可能にする
- 他担当者のファイルは編集しない