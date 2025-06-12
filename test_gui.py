#!/usr/bin/env python3
"""
GUI機能テストスクリプト

開発中のGUI機能をテストするためのスクリプト
各ウィジェットの基本動作を確認
"""

import sys
import os

# パスを追加してローカルモジュールをインポート可能にする
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gui():
    """GUIのテスト実行"""
    try:
        print("GUI機能のテストを開始します...")
        
        # 拡張メインウィンドウをインポート・起動
        from src.gui.main_window_enhanced import MainWindowEnhanced
        
        # アプリケーションの起動
        app = MainWindowEnhanced()
        print("アプリケーションが正常に初期化されました")
        print("GUIウィンドウが表示されます...")
        
        app.run()
        
    except ImportError as e:
        print(f"インポートエラー: {e}")
        print("必要なモジュールが見つかりません")
        return False
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("AI Tools Automation - GUI テスト")
    print("=" * 50)
    
    success = test_gui()
    
    if success:
        print("\\nテスト完了")
    else:
        print("\\nテストに失敗しました")
        sys.exit(1)