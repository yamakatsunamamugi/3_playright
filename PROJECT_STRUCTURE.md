# プロジェクト構造ガイド

## 📁 現在の開発で使用する重要ファイル

### メインエントリーポイント
- `main.py` - アプリケーションのメインエントリーポイント

### GUI (ユーザーインターフェース)
- `src/gui/improved_main_window.py` - **メインGUI（実際のブラウザテスト実装済み）**
- `src/gui/enhanced_main_window.py` - 拡張版GUI（--enhanced フラグ）
- `src/gui/widgets/` - GUI コンポーネント

### AI自動化システム
- `src/ai_tools/browser_manager.py` - ブラウザ管理（Playwright）
- `src/ai_tools/chatgpt_handler.py` - ChatGPT操作ハンドラー
- `src/ai_tools/claude.py` - Claude操作ハンドラー
- `src/ai_tools/gemini.py` - Gemini操作ハンドラー
- `src/ai_tools/genspark.py` - Genspark操作ハンドラー
- `src/ai_tools/google_ai_studio.py` - Google AI Studio操作ハンドラー

### Google Sheets連携
- `src/sheets/` - スプレッドシート処理
- `setup_credentials.py` - Google Sheets API認証設定
- `google_sheets_api.py` - Google Sheets API基本機能

### 設定・ログ
- `config/settings.py` - アプリケーション設定
- `src/utils/logger.py` - ログ機能
- `src/config_manager.py` - 設定管理

## 📦 アーカイブ済み（未使用）ファイル

### `archive/old_gui_files/`
- `fixed_main_window.py` - 旧メインGUI（フェイクテスト版）
- `main_window.py` - 初期版GUI
- `main_window_backup.py` - バックアップファイル
- `main_window_enhanced.py` - 旧拡張版GUI

### `archive/test_files/`
- `test_*.py` - 各種テストファイル
- `direct_test.py` - 直接テスト用ファイル

### `archive/experimental/`
- `advanced_ai_login_solver.py` - 高度なログイン解決実験
- `bot_detection_test.py` - Bot検出テスト実験
- `demo_latest_cloudflare_bypass.py` - Cloudflare回避実験
- `fix_login_issues.py` - ログイン問題修正実験
- `simple_stealth_test.py` - ステルスモードテスト

### `archive/debug_tools/`
- `debug_ai_models.py` - AIモデルデバッグツール
- `get_latest_models.py` - 最新モデル取得ツール
- `improved_model_fetcher.py` - 改良版モデル取得

## 🚀 アプリケーション起動方法

```bash
# 標準モード（推奨）
python3 main.py

# 拡張版モード
python3 main.py --enhanced
```

## ⚠️ 重要な注意事項

1. **使用するGUIファイル**: `src/gui/improved_main_window.py` のみ
2. **archiveフォルダ**: 削除しないでください（必要時に参照可能）
3. **新機能追加時**: 既存の構造に従って適切なディレクトリに配置

## 🔧 今後の開発指針

- 新しいAIツール: `src/ai_tools/` に追加
- 新しいGUI機能: `src/gui/widgets/` に追加
- 新しいシート機能: `src/sheets/` に追加
- 設定関連: `config/` に追加

このドキュメントにより、プロジェクトの混乱を防ぎ、効率的な開発を継続できます。