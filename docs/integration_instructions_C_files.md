# 担当者C（UI統合・ドキュメント担当）作業指示書

## 1. 担当範囲（専任ファイル）

### 1.1 新規作成ファイル
- `src/gui/controllers/main_controller.py` - GUI統合コントローラー
- `src/gui/dialogs/progress_dialog.py` - 進捗表示ダイアログ
- `src/gui/dialogs/error_dialog.py` - エラー表示ダイアログ
- `docs/user_manual.md` - ユーザーマニュアル
- `docs/developer_guide.md` - 開発者ガイド
- `docs/api_reference.md` - API リファレンス
- `README.md` - プロジェクト説明（更新）

### 1.2 修正担当ファイル
- `src/gui/main_window.py` - Orchestratorとの連携追加（軽微な修正のみ）
- `requirements.txt` - 最終的な依存関係の整理

## 2. 作業詳細

### 2.1 事前準備
```bash
# 最新のintegrationブランチに切り替え
git checkout feature/integration
git pull origin feature/integration

# 作業用サブブランチを作成
git checkout -b feature/integration-ui-docs
```

### 2.2 main_controller.py の実装

```python
"""
src/gui/controllers/main_controller.py
GUIとOrchestratorを繋ぐコントローラー
"""

from PyQt6.QtCore import QObject, pyqtSignal, QThread
from typing import Dict, Optional
import asyncio
from src.orchestrator import Orchestrator
from src.utils.logger import get_logger

logger = get_logger(__name__)

class MainController(QObject):
    """GUI統合コントローラー"""
    
    # シグナル定義
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal(dict)
    progress_updated = pyqtSignal(int, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.orchestrator = Orchestrator()
        self.processing_thread: Optional[ProcessingThread] = None
        
    def start_processing(self, config: Dict):
        """処理を開始"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.error_occurred.emit("処理が既に実行中です")
            return
            
        self.processing_thread = ProcessingThread(self.orchestrator, config)
        self.processing_thread.finished_signal.connect(self._on_processing_finished)
        self.processing_thread.progress_signal.connect(self._on_progress_updated)
        self.processing_thread.error_signal.connect(self._on_error_occurred)
        
        self.processing_started.emit()
        self.processing_thread.start()
        
    def stop_processing(self):
        """処理を停止"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            
    def _on_processing_finished(self, result: Dict):
        """処理完了時の処理"""
        self.processing_finished.emit(result)
        
    def _on_progress_updated(self, progress: int, message: str):
        """進捗更新時の処理"""
        self.progress_updated.emit(progress, message)
        
    def _on_error_occurred(self, error: str):
        """エラー発生時の処理"""
        self.error_occurred.emit(error)


class ProcessingThread(QThread):
    """非同期処理用スレッド"""
    
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, orchestrator: Orchestrator, config: Dict):
        super().__init__()
        self.orchestrator = orchestrator
        self.config = config
        self._is_running = True
        
    def run(self):
        """スレッドのメイン処理"""
        try:
            # 非同期イベントループを作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Orchestratorの処理を実行
            result = loop.run_until_complete(
                self.orchestrator.process_spreadsheet(
                    self.config['url'],
                    self.config['sheet_name'],
                    self.config['ai_configs']
                )
            )
            
            self.finished_signal.emit(result)
            
        except Exception as e:
            logger.error(f"処理中にエラー発生: {e}")
            self.error_signal.emit(str(e))
        finally:
            loop.close()
            
    def stop(self):
        """処理を停止"""
        self._is_running = False
        # Orchestratorの停止処理を呼び出す
        asyncio.run(self.orchestrator.stop())
```

### 2.3 progress_dialog.py の実装

```python
"""
src/gui/dialogs/progress_dialog.py
処理進捗表示ダイアログ
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QProgressBar, 
                            QLabel, QPushButton, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal

class ProgressDialog(QDialog):
    """進捗表示ダイアログ"""
    
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("処理中...")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()
        
    def setup_ui(self):
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        
        # 進捗バー
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # ステータスラベル
        self.status_label = QLabel("処理を開始しています...")
        layout.addWidget(self.status_label)
        
        # 詳細ログ
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)
        
        # キャンセルボタン
        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        layout.addWidget(self.cancel_button)
        
    def update_progress(self, value: int, message: str):
        """進捗を更新"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self.log_text.append(f"[{value}%] {message}")
        
    def set_finished(self):
        """完了状態に設定"""
        self.progress_bar.setValue(100)
        self.status_label.setText("処理が完了しました")
        self.cancel_button.setText("閉じる")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)
```

### 2.4 user_manual.md の作成

```markdown
# スプレッドシート自動処理ツール ユーザーマニュアル

## 目次
1. [はじめに](#はじめに)
2. [インストール](#インストール)
3. [初期設定](#初期設定)
4. [基本的な使い方](#基本的な使い方)
5. [高度な機能](#高度な機能)
6. [トラブルシューティング](#トラブルシューティング)

## はじめに

本ツールは、Googleスプレッドシートのデータを自動的にAIツールで処理し、結果を書き戻すための自動化ツールです。

### 主な機能
- 複数のAIツール（ChatGPT、Claude、Gemini等）に対応
- バッチ処理による効率的な実行
- エラーハンドリングと自動リトライ
- 処理履歴の記録

## インストール

### 必要な環境
- macOS 10.15以降 / Windows 10以降
- Python 3.9以降
- Google Chrome（最新版）

### インストール手順

1. リポジトリをクローン
```bash
git clone https://github.com/your-repo/spreadsheet-ai-automation.git
cd spreadsheet-ai-automation
```

2. 仮想環境の作成
```bash
python -m venv venv
source venv/bin/activate  # macOS
# または
venv\Scripts\activate  # Windows
```

3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

## 初期設定

### 1. Google API認証

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成
3. Google Sheets APIを有効化
4. 認証情報を作成（OAuth 2.0 クライアントID）
5. `credentials.json`をプロジェクトルートに配置

### 2. AIツールの設定

各AIツールにログインし、使用可能な状態にしておく必要があります。

## 基本的な使い方

### 1. アプリケーションの起動

```bash
python main.py
```

### 2. スプレッドシートの設定

1. 「スプレッドシート」タブでURLを入力
2. 「読み込み」ボタンをクリック
3. シート一覧から対象シートを選択

### 3. AI設定

1. 「AI設定」タブで使用するAIを選択
2. 各AIのモデルと詳細設定を構成
3. 「保存」ボタンで設定を保存

### 4. 処理の実行

1. 「処理開始」ボタンをクリック
2. 進捗ダイアログで状況を確認
3. 完了後、スプレッドシートで結果を確認

## 高度な機能

### バッチ処理
複数のコピー列を一度に処理できます。

### エラーハンドリング
- 自動リトライ（最大5回）
- エラー内容の記録
- 部分的な処理の継続

### 処理履歴
すべての処理はログに記録され、後から確認できます。

## トラブルシューティング

### よくある問題

**Q: スプレッドシートが読み込めない**
A: Google APIの認証を確認してください。`token.json`を削除して再認証することで解決する場合があります。

**Q: AIツールでエラーが発生する**
A: 各AIツールにブラウザで手動ログインできるか確認してください。

**Q: 処理が途中で止まる**
A: ログファイル（`logs/`フォルダ）を確認し、エラー内容を特定してください。

### サポート

問題が解決しない場合は、以下の情報とともにイシューを作成してください：
- エラーメッセージ
- ログファイル
- 使用環境（OS、Pythonバージョン等）
```

### 2.5 README.md の更新

```markdown
# スプレッドシート AI自動処理ツール

[![Tests](https://github.com/your-repo/spreadsheet-ai-automation/workflows/Tests/badge.svg)](https://github.com/your-repo/spreadsheet-ai-automation/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Googleスプレッドシートのデータを複数のAIツールで自動処理するPythonアプリケーション

## 特徴

- 🤖 複数AI対応（ChatGPT、Claude、Gemini、Genspark、Google AI Studio）
- 📊 Googleスプレッドシートとの完全統合
- 🔄 自動リトライとエラーハンドリング
- 🖥️ 使いやすいGUIインターフェース
- 📝 詳細なログと処理履歴

## クイックスタート

```bash
# クローン
git clone https://github.com/your-repo/spreadsheet-ai-automation.git
cd spreadsheet-ai-automation

# セットアップ
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# 実行
python main.py
```

## ドキュメント

- [ユーザーマニュアル](docs/user_manual.md)
- [開発者ガイド](docs/developer_guide.md)
- [APIリファレンス](docs/api_reference.md)

## プロジェクト構造

```
.
├── src/
│   ├── gui/              # GUIコンポーネント
│   ├── sheets/            # スプレッドシート処理
│   ├── ai_tools/          # AI連携
│   └── utils/             # ユーティリティ
├── tests/                 # テストスイート
├── docs/                  # ドキュメント
└── config/                # 設定ファイル
```

## 開発

### テストの実行

```bash
# 全テスト
pytest tests/

# カバレッジ付き
pytest tests/ --cov=src
```

### コントリビュート

1. Forkする
2. Feature branchを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. Branchにプッシュ (`git push origin feature/AmazingFeature`)
5. Pull Requestを作成

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
```

## 3. Git管理

### 3.1 コミット規則
```bash
# UI機能追加
git add src/gui/controllers/main_controller.py
git commit -m "feat: GUI統合コントローラーの実装"

# ダイアログ追加
git add src/gui/dialogs/*.py
git commit -m "feat: 進捗表示とエラーダイアログの追加"

# ドキュメント
git add docs/user_manual.md
git commit -m "docs: ユーザーマニュアルの作成"

git add README.md
git commit -m "docs: READMEの更新と整理"
```

### 3.2 マージリクエスト
```bash
# 作業完了後
git push origin feature/integration-ui-docs

# PRメッセージ
"""
UI統合とドキュメント整備

実装内容:
- MainController（GUI-Orchestrator連携）
- 進捗/エラーダイアログ
- ユーザーマニュアル
- 開発者向けドキュメント
- README更新

レビュー: 統括者Dによる最終確認待ち
"""
```

## 4. 他担当者との連携

### 4.1 A担当者との連携
- Orchestratorのインターフェース仕様を確認
- MainControllerでの呼び出し方法を調整

### 4.2 B担当者との連携
- テスト実行方法をドキュメントに記載
- GUIテストのためのフィクスチャを提供

## 5. 完了条件
- [ ] GUI統合コントローラーの実装
- [ ] 進捗/エラーダイアログの実装
- [ ] ユーザーマニュアルの完成
- [ ] 開発者ガイドの作成
- [ ] README.mdの更新
- [ ] 動作確認（手動テスト）

## 6. 注意事項
- 既存ファイルの修正は最小限に
- UIの変更は見た目より機能性を優先
- ドキュメントは初心者でも理解できるように
- 他担当者のファイルは編集しない