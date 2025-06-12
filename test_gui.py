#!/usr/bin/env python3
"""
GUIテスト用スクリプト
メインGUIアプリケーションの動作確認を行う
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

def test_gui_launch():
    """GUI起動テスト"""
    try:
        print("GUIアプリケーションを起動中...")
        
        from src.gui.main_window import MainWindow
        from src.utils.logger import setup_logger
        from config.settings import settings
        
        # ログ設定
        setup_logger(settings.LOG_LEVEL, settings.LOG_FILE)
        print("✓ ログ設定完了")
        
        # メインウィンドウ作成
        app = MainWindow()
        print("✓ メインウィンドウ作成完了")
        
        # アプリケーション実行
        print("✓ GUI起動成功 - ウィンドウが表示されました")
        app.run()
        
    except Exception as e:
        print(f"❌ GUI起動エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("Google Sheets AI自動化ツール - GUIテスト")
    print("=" * 50)
    
    success = test_gui_launch()
    
    if success:
        print("\n✓ テスト完了: GUI正常起動")
    else:
        print("\n❌ テスト失敗: GUI起動エラー")
        sys.exit(1)