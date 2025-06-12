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
    
    # 起動モードの選択
    if len(sys.argv) > 1 and sys.argv[1] == "--enhanced":
        use_enhanced = True
        print("✓ 拡張版モードで起動")
    else:
        use_enhanced = False
        print("✓ 標準モードで起動")
    
    try:
        # ログ設定
        from src.utils.logger import setup_logger
        setup_logger("INFO", "logs/app.log")
        print("✓ ログ設定完了")
        
        # GUIアプリケーションを起動
        if use_enhanced:
            from src.gui.enhanced_main_window import EnhancedMainWindow
            app = EnhancedMainWindow()
        else:
            # 改良版メインウィンドウを使用（実際のブラウザテスト付き）
            from src.gui.improved_main_window import ImprovedMainWindow
            app = ImprovedMainWindow()
            
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