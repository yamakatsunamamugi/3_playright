#!/usr/bin/env python3
"""
最新AIモデル情報取得スクリプト
Playwrightを使用して各AIサービスから最新モデル一覧を取得・表示
"""

import sys
import asyncio
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    print("🤖 最新AIモデル情報取得開始")
    print("=" * 60)
    
    try:
        from src.ai_tools.playwright_model_fetcher import PlaywrightModelFetcher
        
        # Playwrightモデル取得クラスを初期化
        fetcher = PlaywrightModelFetcher(headless=True)
        
        print("📡 各AIサービスから最新モデル情報を取得中...")
        print("⏳ この処理には数分かかる場合があります...")
        print()
        
        # 全AIサービスから最新モデル情報を取得
        results = await fetcher.fetch_all_models()
        
        print("📊 取得結果:")
        print("=" * 60)
        
        for service_key, data in results.items():
            service_name = data.get('service', service_key.title())
            models = data.get('models', [])
            settings = data.get('settings', [])
            updated_at = data.get('updated_at', 'Unknown')
            source = data.get('source', 'live')
            
            print(f"\n🤖 **{service_name}**")
            print(f"   ⏰ 更新日時: {updated_at}")
            print(f"   📡 データソース: {source}")
            print(f"   📈 モデル数: {len(models)}個")
            
            print(f"\n   📋 利用可能モデル:")
            for i, model in enumerate(models, 1):
                print(f"      {i:2d}. {model}")
            
            if settings:
                print(f"\n   ⚙️  設定オプション:")
                for setting in settings:
                    setting_name = setting.get('name', 'Unknown')
                    setting_type = setting.get('type', 'unknown')
                    default_value = setting.get('default', 'N/A')
                    print(f"      • {setting_name} ({setting_type}): デフォルト={default_value}")
            
            print("-" * 40)
        
        # サマリー情報
        total_models = sum(len(data.get('models', [])) for data in results.values())
        print(f"\n📈 **サマリー**")
        print(f"   🔢 対応AIサービス: {len(results)}種類")
        print(f"   🎯 総モデル数: {total_models}個")
        print(f"   💾 キャッシュ保存場所: cache/models/")
        
        # 特に注目すべき最新モデル
        print(f"\n⭐ **注目の最新モデル**")
        notable_models = []
        
        for service_key, data in results.items():
            models = data.get('models', [])
            service_name = data.get('service', service_key.title())
            
            # 最新っぽいモデルを検出
            for model in models:
                if any(keyword in model.lower() for keyword in ['4o', '3.5', 'pro', 'turbo', 'flash', 'opus', 'sonnet']):
                    notable_models.append(f"   🌟 {service_name}: {model}")
        
        for model in notable_models[:10]:  # 上位10個
            print(model)
        
        print(f"\n✅ モデル情報取得完了！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())