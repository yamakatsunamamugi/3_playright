"""
モデルフェッチャー機能のテストスクリプト

このスクリプトを実行して、各AIサービスから動的にモデル情報を取得する機能をテストします。
"""

import asyncio
import logging
from pathlib import Path
from src.ai_tools.model_fetcher import create_model_fetcher, ModelProvider

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_model_fetcher(provider: ModelProvider):
    """
    指定したプロバイダーのモデルフェッチャーをテスト
    
    Args:
        provider: テストするプロバイダー
    """
    print(f"\n{'='*60}")
    print(f"テスト開始: {provider.value}")
    print(f"{'='*60}")
    
    try:
        # キャッシュディレクトリを設定
        cache_dir = Path.home() / ".ai_tools_cache" / "test"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # モデルフェッチャーを作成
        fetcher = create_model_fetcher(provider, cache_dir)
        
        # モデル情報を取得
        print(f"\n{provider.value} のモデル情報を取得中...")
        models = await fetcher.fetch_models()
        
        print(f"\n取得したモデル数: {len(models)}")
        print("\n--- モデル一覧 ---")
        for i, model in enumerate(models, 1):
            print(f"\n{i}. {model.display_name}")
            print(f"   ID: {model.id}")
            if model.description:
                print(f"   説明: {model.description}")
            if model.context_length:
                print(f"   コンテキスト長: {model.context_length:,} tokens")
            if model.capabilities:
                print(f"   能力: {', '.join(model.capabilities)}")
            if model.is_default:
                print(f"   ★ デフォルトモデル")
        
        # 設定オプションを取得
        print(f"\n\n{provider.value} の設定オプションを取得中...")
        settings = await fetcher.fetch_settings()
        
        print(f"\n取得した設定数: {len(settings)}")
        print("\n--- 設定オプション ---")
        for i, setting in enumerate(settings, 1):
            print(f"\n{i}. {setting.display_name}")
            print(f"   ID: {setting.id}")
            print(f"   タイプ: {setting.type}")
            if setting.description:
                print(f"   説明: {setting.description}")
            if setting.default_value is not None:
                print(f"   デフォルト値: {setting.default_value}")
            if setting.options:
                print(f"   選択肢: {', '.join(map(str, setting.options))}")
            if setting.min_value is not None and setting.max_value is not None:
                print(f"   範囲: {setting.min_value} ~ {setting.max_value}")
        
        # キャッシュテスト
        print(f"\n\nキャッシュ機能のテスト...")
        print("2回目の取得（キャッシュから）...")
        cached_models = await fetcher.fetch_models()
        print(f"キャッシュから取得したモデル数: {len(cached_models)}")
        
        print(f"\n{provider.value} のテスト完了 ✓")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


async def test_all_providers():
    """すべてのプロバイダーをテスト"""
    providers_to_test = [
        ModelProvider.CHATGPT,
        ModelProvider.CLAUDE,
        ModelProvider.GEMINI,
        ModelProvider.GENSPARK,
        ModelProvider.GOOGLE_AI_STUDIO
    ]
    
    print("AI モデル動的取得機能のテスト")
    print("=" * 80)
    print("\n注意事項:")
    print("- このテストはフォールバックデータを使用します")
    print("- 実際のWebUIからの取得をテストする場合は、ブラウザが開きます")
    print("- 各AIサービスにログインしていると、より詳細な情報が取得できます")
    
    for provider in providers_to_test:
        await test_model_fetcher(provider)
        await asyncio.sleep(1)  # プロバイダー間で少し待機
    
    print("\n" + "=" * 80)
    print("すべてのテストが完了しました")


async def test_cache_functionality():
    """キャッシュ機能の詳細テスト"""
    print("\n" + "=" * 80)
    print("キャッシュ機能の詳細テスト")
    print("=" * 80)
    
    cache_dir = Path.home() / ".ai_tools_cache" / "test"
    fetcher = create_model_fetcher(ModelProvider.CHATGPT, cache_dir)
    
    # 強制リフレッシュ
    print("\n1. 強制リフレッシュでモデル情報を取得...")
    models1 = await fetcher.fetch_models(force_refresh=True)
    print(f"   取得したモデル数: {len(models1)}")
    
    # キャッシュから取得
    print("\n2. キャッシュから取得...")
    models2 = await fetcher.fetch_models()
    print(f"   取得したモデル数: {len(models2)}")
    print(f"   キャッシュが正常に機能: {len(models1) == len(models2)}")
    
    # キャッシュクリア
    print("\n3. キャッシュをクリア...")
    fetcher.cache_manager.clear()
    
    print("\nキャッシュテスト完了 ✓")


if __name__ == "__main__":
    print("モデルフェッチャーテストを開始します\n")
    
    # イベントループを作成して実行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # すべてのプロバイダーをテスト
        loop.run_until_complete(test_all_providers())
        
        # キャッシュ機能の詳細テスト
        loop.run_until_complete(test_cache_functionality())
        
    finally:
        loop.close()
    
    print("\n使用方法:")
    print("1. このスクリプトを実行: python test_model_fetcher.py")
    print("2. 各AIサービスのモデル情報が表示されます")
    print("3. エラーが発生した場合は、ログを確認してください")