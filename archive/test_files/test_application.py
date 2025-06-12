#!/usr/bin/env python3
"""
アプリケーションテストツール
"""

import sys
import subprocess
from pathlib import Path

def run_test():
    """テストを実行"""
    print("🧪 スプレッドシートAI自動処理ツール - テスト開始")
    print("=" * 60)
    
    # プロジェクトルートに移動
    project_root = Path(__file__).parent
    print(f"📁 プロジェクトディレクトリ: {project_root}")
    
    try:
        # メインアプリケーションを起動
        print("\n🚀 アプリケーション起動中...")
        print("📋 標準モードで起動します")
        print("💡 テスト用設定:")
        print("   - スプレッドシートURL: https://docs.google.com/spreadsheets/d/1mhvJKjNNdFqn_xo1D7iZzEyoLm9_2Qh3TbcV8NrW5Sx")
        print("   - シート名: 1.原稿本文作成")
        print()
        
        # main.pyを実行
        result = subprocess.run([
            sys.executable, "main.py"
        ], cwd=project_root, capture_output=False)
        
        if result.returncode == 0:
            print("\n✅ アプリケーションが正常に終了しました")
        else:
            print(f"\n❌ アプリケーションがエラーで終了しました (終了コード: {result.returncode})")
            
    except KeyboardInterrupt:
        print("\n⏸️  ユーザーによってテストが中断されました")
    except Exception as e:
        print(f"\n❌ テスト実行中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()

def show_test_instructions():
    """テスト手順を表示"""
    print("\n📋 テスト手順:")
    print("-" * 40)
    print("1. アプリケーションが起動したら、以下を確認してください:")
    print("   ✓ スプレッドシートURLが正しく入力されている")
    print("   ✓ シート名が選択可能")
    print("   ✓ AI設定パネルが表示されている")
    print("   ✓ 最新のAIモデルが表示されている")
    print()
    print("2. 機能テスト:")
    print("   ✓ 「スプレッドシート分析」ボタンをクリック")
    print("   ✓ 列構造が正しく認識される")
    print("   ✓ 「コピー」列が検出される")
    print("   ✓ 列ごとのAI選択が可能")
    print()
    print("3. 期待される動作:")
    print("   ✓ ChatGPT: GPT-4o, o1-preview等が表示")
    print("   ✓ Claude: Claude-3.5 Sonnet (New)等が表示")
    print("   ✓ Gemini: Gemini 2.5 Flash等が表示")
    print()
    print("4. 問題があった場合:")
    print("   ✓ エラーメッセージをスクリーンショット")
    print("   ✓ ログファイル(logs/app.log)を確認")
    print("   ✓ コンソール出力をコピー")

if __name__ == "__main__":
    show_test_instructions()
    print("\n🎯 テストを開始しますか？ (Enter で開始、Ctrl+C で中止)")
    try:
        input()
        run_test()
    except KeyboardInterrupt:
        print("\n👋 テストをキャンセルしました")