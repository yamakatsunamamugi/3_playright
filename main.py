#!/usr/bin/env python3
"""
スプレッドシートAI自動処理ツール
メインエントリーポイント
"""

import sys
import asyncio
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """メイン関数"""
    print("=" * 50)
    print("スプレッドシートAI自動処理ツール")
    print("=" * 50)
    
    try:
        # GUIアプリケーションを起動
        from src.gui.main_window import MainWindow
        from src.utils.logger import setup_logger
        
        # ログ設定
        setup_logger("INFO", "logs/app.log")
        print("✓ ログ設定完了")
        
        # メインウィンドウを起動
        app = MainWindow()
        print("✓ アプリケーション起動")
        
        # GUIを実行
        app.run()
        
    except ImportError as e:
        print(f"\n❌ 必要なモジュールが見つかりません: {e}")
        print("\n以下のコマンドで依存関係をインストールしてください:")
        print("pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()