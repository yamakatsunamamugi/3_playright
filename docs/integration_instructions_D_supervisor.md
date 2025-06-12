# 統括者D 作業指示書

## 1. 役割と責任

### 1.1 主要責任
- 全体進捗の管理と調整
- 各担当者のブロッカー解消
- 最終的な統合とマージ
- リリース準備と品質保証
- ステークホルダーへの報告

### 1.2 担当ファイル
- `docs/integration_status.md` - 統合状況レポート
- `CHANGELOG.md` - 変更履歴
- `main.py` - エントリーポイントの最終調整

## 2. A～C作業中の管理

### 2.1 日次スタンドアップ（毎日10:00）
```markdown
## 日次スタンドアップ テンプレート

日付: YYYY-MM-DD

### 参加者
- [ ] 担当者A
- [ ] 担当者B  
- [ ] 担当者C
- [ ] 統括者D

### 各担当者の報告（3分以内）
**担当者A（コア実装）**
- 昨日の完了事項：
- 本日の予定：
- ブロッカー：

**担当者B（テスト）**
- 昨日の完了事項：
- 本日の予定：
- ブロッカー：

**担当者C（UI/ドキュメント）**
- 昨日の完了事項：
- 本日の予定：
- ブロッカー：

### アクションアイテム
- [ ] 
- [ ] 
```

### 2.2 進捗管理
```bash
# 各担当者のブランチ状況確認
git fetch --all
git branch -r | grep integration

# 進捗確認スクリプト
cat > check_progress.sh << 'EOF'
#!/bin/bash
echo "=== 統合ブランチ進捗状況 ==="
for branch in feature/integration-core-impl feature/integration-tests feature/integration-ui-docs; do
    echo "\n--- $branch ---"
    git log origin/$branch --oneline -5
done
EOF

chmod +x check_progress.sh
```

### 2.3 ブロッカー対応フロー
1. **即時対応（15分以内）**
   - Slackで通知を受信
   - 問題の詳細を確認
   - 解決策の提案

2. **エスカレーション（15分超過）**
   - 緊急ミーティング招集
   - 関係者全員で解決策検討
   - 必要に応じて作業分担変更

## 3. A～C作業完了後の統合作業

### 3.1 各ブランチのレビューとマージ
```bash
# 1. 各担当者の作業完了確認
git checkout feature/integration
git pull origin feature/integration

# 2. A担当者のブランチをマージ
git fetch origin feature/integration-core-impl
git merge origin/feature/integration-core-impl --no-ff -m "merge: コア実装の統合完了"

# 3. B担当者のブランチをマージ
git fetch origin feature/integration-tests
git merge origin/feature/integration-tests --no-ff -m "merge: テストスイートの統合完了"

# 4. C担当者のブランチをマージ
git fetch origin feature/integration-ui-docs
git merge origin/feature/integration-ui-docs --no-ff -m "merge: UI統合とドキュメントの完了"
```

### 3.2 統合テスト実施
```bash
# 1. 依存関係の確認
pip install -r requirements.txt

# 2. 全テストの実行
pytest tests/ -v --tb=short

# 3. 統合動作確認
python main.py --test-mode

# 4. パフォーマンステスト
python -m cProfile -o profile.stats main.py
python -m pstats profile.stats
```

### 3.3 最終調整

#### main.py の調整
```python
"""
main.py
アプリケーションのエントリーポイント
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.gui.controllers.main_controller import MainController
from src.utils.logger import setup_logging
from src.config_manager import get_config_manager

def main():
    """メイン関数"""
    # ロギングの設定
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 設定の読み込み
    config_manager = get_config_manager()
    
    # アプリケーションの起動
    app = QApplication(sys.argv)
    app.setApplicationName("スプレッドシートAI自動処理ツール")
    app.setOrganizationName("YourOrganization")
    
    # メインウィンドウの作成
    main_window = MainWindow()
    
    # コントローラーの設定
    controller = MainController(main_window)
    main_window.set_controller(controller)
    
    # ウィンドウの表示
    main_window.show()
    
    # イベントループの開始
    logger.info("アプリケーションを起動しました")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

## 4. リリース準備

### 4.1 品質チェックリスト
- [ ] 全テストがパス
- [ ] コードカバレッジ80%以上
- [ ] パフォーマンステスト基準クリア
- [ ] ドキュメント完成度確認
- [ ] セキュリティスキャン実施

### 4.2 リリースブランチ作成
```bash
# 1. リリースブランチ作成
git checkout -b release/v1.0.0 feature/integration

# 2. バージョン情報更新
echo "1.0.0" > VERSION

# 3. CHANGELOG作成
cat > CHANGELOG.md << 'EOF'
# Changelog

## [1.0.0] - 2024-XX-XX

### 追加機能
- Googleスプレッドシート連携
- 複数AI対応（ChatGPT, Claude, Gemini等）
- バッチ処理機能
- GUIインターフェース
- 自動リトライ機能

### 技術仕様
- Python 3.9+
- PyQt6 GUI
- 非同期処理対応
- 包括的なテストスイート
EOF

git add VERSION CHANGELOG.md
git commit -m "chore: v1.0.0リリース準備"
```

### 4.3 最終マージとタグ付け
```bash
# 1. mainブランチへマージ
git checkout main
git merge --no-ff release/v1.0.0 -m "release: v1.0.0"

# 2. タグ付け
git tag -a v1.0.0 -m "Version 1.0.0 - 初回リリース"

# 3. プッシュ
git push origin main --tags
```

## 5. 作業完了後の手順

### 5.1 デプロイメントガイド作成
```markdown
# デプロイメントガイド

## macOS向けパッケージング
```bash
# PyInstallerでの実行ファイル作成
pip install pyinstaller
pyinstaller --name="SpreadsheetAI" \
            --windowed \
            --icon=assets/icon.icns \
            --add-data "config:config" \
            main.py
```

## Windows向けパッケージング
```bash
# Windows環境でのビルド
pyinstaller --name="SpreadsheetAI" \
            --windowed \
            --icon=assets/icon.ico \
            --add-data "config;config" \
            main.py
```
```

### 5.2 プロジェクト完了報告
```markdown
# プロジェクト完了報告書

## 概要
スプレッドシートAI自動処理ツール v1.0.0 の開発が完了しました。

## 達成事項
- ✅ 全機能の実装完了
- ✅ テストカバレッジ: 85%
- ✅ ドキュメント完成
- ✅ パフォーマンス基準達成

## 成果物
- ソースコード（GitHubリポジトリ）
- 実行可能ファイル（macOS/Windows）
- ユーザーマニュアル
- 開発者ガイド

## 今後の展開
- v1.1: 追加AI対応
- v1.2: バッチ処理の高速化
- v2.0: Web版の開発
```

## 6. 緊急時対応

### 6.1 重大なバグ発見時
1. 全作業を一時停止
2. 緊急ミーティング招集
3. ホットフィックスブランチ作成
4. 修正とテスト
5. 緊急リリース

### 6.2 スケジュール遅延時
1. 原因分析
2. リソース再配分検討
3. スコープ調整の判断
4. ステークホルダーへの報告

## 7. コミュニケーション

### 7.1 定期報告
- 日次: Slackでの進捗共有
- 週次: ステークホルダーへのレポート
- 完了時: 最終報告書提出

### 7.2 ツール
- Slack: #integration-channel
- GitHub: Issues/PR/Discussions
- ドキュメント: Google Docs共有

この指示書に従って、効率的な統合作業の管理をお願いします。