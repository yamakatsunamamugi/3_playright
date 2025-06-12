#!/usr/bin/env python3
"""
AIモデル取得機能のテストスクリプト
各AIツールのモデル情報を取得して表示します
"""
import sys
import asyncio
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.ai_tools.chatgpt_model_fetcher import ChatGPTModelFetcher
from src.ai_tools.claude_model_fetcher import ClaudeModelFetcher
from src.ai_tools.gemini_model_fetcher import GeminiModelFetcher
from src.ai_tools.genspark_model_fetcher import GensparkModelFetcher
from src.ai_tools.google_ai_studio_model_fetcher import GoogleAIStudioModelFetcher


def test_model_fetcher():
    """各AIツールのモデル情報を取得してテスト"""
    print("=" * 80)
    print("AIモデル情報取得テスト")
    print("=" * 80)
    
    # 各AIツールのフェッチャーをテスト
    fetchers = [
        ("ChatGPT", ChatGPTModelFetcher()),
        ("Claude", ClaudeModelFetcher()),
        ("Gemini", GeminiModelFetcher()),
        ("Genspark", GensparkModelFetcher()),
        ("Google AI Studio", GoogleAIStudioModelFetcher())
    ]
    
    for ai_name, fetcher in fetchers:
        print(f"\n【{ai_name}】")
        print("-" * 40)
        
        try:
            # モデル情報を取得
            models = fetcher.get_models()
            print(f"✓ {len(models)}個のモデルを取得しました")
            
            # 各モデルの情報を表示
            for i, model in enumerate(models, 1):
                print(f"\n  {i}. {model.name}")
                print(f"     ID: {model.id}")
                print(f"     説明: {model.description}")
                if model.capabilities:
                    print(f"     機能: {', '.join(model.capabilities)}")
                if model.max_tokens:
                    print(f"     最大トークン: {model.max_tokens:,}")
                if model.is_default:
                    print(f"     ★ デフォルトモデル")
            
            # 設定オプションを取得
            print(f"\n  設定オプション:")
            settings = fetcher.get_default_settings()
            for key, value in list(settings.items())[:3]:  # 最初の3つだけ表示
                print(f"    - {key}: {value.get('description', 'No description')}")
            if len(settings) > 3:
                print(f"    ... 他 {len(settings) - 3} 個の設定")
                
        except Exception as e:
            print(f"✗ エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == "__main__":
    test_model_fetcher()