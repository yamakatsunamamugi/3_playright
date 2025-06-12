#!/usr/bin/env python3
"""
直接テスト用スクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

def test_improved_gui():
    """改善されたGUIを直接テスト"""
    try:
        print("🔍 改善されたGUIモジュールをインポート中...")
        from src.gui.improved_main_window import ImprovedMainWindow
        
        print("✅ インポート成功")
        print("🚀 アプリケーション起動中...")
        
        app = ImprovedMainWindow()
        print("✅ アプリケーション初期化完了")
        print("📋 GUIを表示中...")
        
        app.run()
        
    except ImportError as e:
        print(f"❌ インポートエラー: {e}")
        print("📁 モジュール構造を確認してください")
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 改善されたGUI直接テスト")
    print("=" * 50)
    test_improved_gui()