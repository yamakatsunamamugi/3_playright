# 担当者A（コア統合実装）作業指示書

## 1. 担当範囲（専任ファイル）

### 1.1 新規作成ファイル
- `src/orchestrator.py` - メイン統合コントローラー
- `src/utils/process_manager.py` - プロセス管理ユーティリティ
- `config/default_settings.json` - デフォルト設定ファイル

### 1.2 修正担当ファイル
- `src/__init__.py` - orchestratorの追加
- `src/utils/__init__.py` - process_managerの追加

## 2. 作業詳細

### 2.1 事前準備
```bash
# 最新のintegrationブランチに切り替え
git checkout feature/integration
git pull origin feature/integration

# 作業用サブブランチを作成
git checkout -b feature/integration-core-impl
```

### 2.2 orchestrator.py の実装

```python
"""
src/orchestrator.py
全体の処理フローを制御する統合コントローラー
"""

import asyncio
from typing import Dict, List, Optional
from src.sheets.processor import SpreadsheetProcessor
from src.ai_tools.browser_manager import BrowserManager
from src.config_manager import get_config_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Orchestrator:
    """メイン処理オーケストレーター"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.sheet_processor = SpreadsheetProcessor()
        self.browser_manager = BrowserManager()
        self.is_running = False
        self.current_task = None
        
    async def initialize(self):
        """初期化処理"""
        logger.info("Orchestrator初期化開始")
        # 各コンポーネントの初期化
        await self.browser_manager.initialize()
        
    async def process_spreadsheet(self, url: str, sheet_name: str, 
                                 ai_configs: Dict[str, Dict]) -> Dict:
        """
        スプレッドシート処理のメインフロー
        
        Args:
            url: スプレッドシートURL
            sheet_name: シート名
            ai_configs: AI設定辞書
            
        Returns:
            処理結果辞書
        """
        try:
            self.is_running = True
            results = {
                "processed_rows": 0,
                "errors": [],
                "success": True
            }
            
            # 1. シートデータの読み込み
            logger.info(f"シート読み込み開始: {sheet_name}")
            sheet_data = await self.sheet_processor.load_sheet(url, sheet_name)
            
            # 2. 作業指示行とコピー列の検出
            work_config = self._detect_work_configuration(sheet_data)
            
            # 3. 各行・各列の処理
            for row_idx in work_config["target_rows"]:
                for col_config in work_config["copy_columns"]:
                    await self._process_cell(
                        sheet_data, row_idx, col_config, ai_configs
                    )
                    results["processed_rows"] += 1
                    
            return results
            
        except Exception as e:
            logger.error(f"処理中にエラー発生: {e}")
            results["success"] = False
            results["errors"].append(str(e))
            return results
        finally:
            self.is_running = False
            
    def _detect_work_configuration(self, sheet_data: List[List]) -> Dict:
        """作業設定を検出"""
        # 実装詳細...
        pass
        
    async def _process_cell(self, sheet_data, row_idx, col_config, ai_configs):
        """個別セルの処理"""
        # 実装詳細...
        pass
        
    async def stop(self):
        """処理を停止"""
        self.is_running = False
        if self.current_task:
            self.current_task.cancel()
```

### 2.3 process_manager.py の実装

```python
"""
src/utils/process_manager.py
プロセス管理とタスク制御
"""

import asyncio
from typing import Optional, Callable
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ProcessManager:
    """非同期プロセス管理クラス"""
    
    def __init__(self):
        self.tasks = {}
        self.callbacks = {}
        
    async def run_with_timeout(self, coro, timeout: int, task_name: str):
        """タイムアウト付きでコルーチンを実行"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"タスク '{task_name}' がタイムアウトしました")
            raise
            
    def register_callback(self, event: str, callback: Callable):
        """イベントコールバックを登録"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
        
    async def emit_event(self, event: str, data: Dict):
        """イベントを発火"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                await callback(data)
```

## 3. Git管理

### 3.1 コミット規則
```bash
# 機能追加
git add src/orchestrator.py
git commit -m "feat: Orchestratorクラスの実装"

# ユーティリティ追加
git add src/utils/process_manager.py
git commit -m "feat: ProcessManagerの実装"

# 設定ファイル
git add config/default_settings.json
git commit -m "chore: デフォルト設定ファイルの追加"
```

### 3.2 プッシュタイミング
- 各主要機能の実装完了後
- 1日の作業終了時
- 他メンバーとの連携が必要な時

### 3.3 マージリクエスト
```bash
# 作業完了後
git push origin feature/integration-core-impl

# PRメッセージ例
"""
統合コア機能の実装

実装内容:
- Orchestratorクラス（メイン処理フロー）
- ProcessManager（非同期タスク管理）
- デフォルト設定ファイル

テスト: B担当者のテストを待つ
"""
```

## 4. 他担当者との連携

### 4.1 B担当者への連携
- orchestrator.pyのインターフェース仕様を共有
- ProcessManagerの使用方法をドキュメント化

### 4.2 C担当者への連携  
- テスト用のモックメソッドを提供
- 統合テストで必要なフィクスチャを準備

## 5. 完了条件
- [ ] orchestrator.pyの完全実装
- [ ] process_manager.pyの実装
- [ ] 単体テストの作成（可能な範囲で）
- [ ] 他メンバーへの仕様共有
- [ ] コードレビューの実施

## 6. 注意事項
- 他のファイルは絶対に編集しない
- インターフェースは既存のものを使用
- 不明点は統括者Dに確認
- 非同期処理のエラーハンドリングを確実に実装