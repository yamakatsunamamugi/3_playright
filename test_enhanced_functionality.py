#!/usr/bin/env python3
"""
拡張機能の基本テストスクリプト
新規追加された5つのファイルの基本動作をテスト
"""

import asyncio
import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

# テスト対象のインポート
from src.browser.enhanced_browser_manager import EnhancedBrowserManager
from src.browser.enhanced_selector_strategy import EnhancedSelectorStrategy
from src.browser.enhanced_session_manager import EnhancedSessionManager
from src.ai_tools.enhanced_ai_handler import AIHandlerFactory, ChatGPTEnhancedHandler

async def test_enhanced_session_manager():
    """セッション管理機能のテスト"""
    print("🔒 セッション管理機能のテスト開始...")
    
    try:
        session_manager = EnhancedSessionManager()
        
        # セッションメタデータの基本動作確認
        status = session_manager.get_session_status()
        print(f"  ✅ セッション状態取得: {len(status)}件のセッション")
        
        # 期限切れセッションのクリーンアップテスト
        expired = session_manager.cleanup_expired_sessions()
        print(f"  ✅ 期限切れセッションクリーンアップ: {len(expired)}件削除")
        
        # 認証設定の確認
        configs = session_manager.auth_check_configs
        print(f"  ✅ AI認証設定: {len(configs)}種類のAIに対応")
        
        return True
        
    except Exception as e:
        print(f"  ❌ セッション管理テスト失敗: {e}")
        return False

async def test_enhanced_selector_strategy():
    """セレクター戦略機能のテスト"""
    print("🎯 セレクター戦略機能のテスト開始...")
    
    try:
        selector_strategy = EnhancedSelectorStrategy()
        
        # セレクター定義の確認
        definitions = selector_strategy.selector_definitions
        print(f"  ✅ セレクター定義: {len(definitions)}種類のAIに対応")
        
        # 各AIのセレクター数を確認
        for ai_name, selectors in definitions.items():
            input_selectors = len(selectors.get('input', []))
            send_selectors = len(selectors.get('send_button', []))
            print(f"    - {ai_name}: input={input_selectors}, send={send_selectors}")
        
        # インタラクション戦略の確認
        chatgpt_strategy = selector_strategy.get_interaction_strategies('chatgpt')
        print(f"  ✅ ChatGPTインタラクション戦略: {chatgpt_strategy}")
        
        # 汎用セレクターの確認
        generic = selector_strategy.generic_selectors
        print(f"  ✅ 汎用セレクター: {len(generic)}種類")
        
        return True
        
    except Exception as e:
        print(f"  ❌ セレクター戦略テスト失敗: {e}")
        return False

async def test_browser_manager_initialization():
    """ブラウザマネージャーの初期化テスト"""
    print("🌐 ブラウザマネージャー初期化テスト開始...")
    
    try:
        # ヘッドレスモードで軽量テスト
        browser_manager = EnhancedBrowserManager(
            use_existing_profile=False,
            headless=True
        )
        
        # 基本設定の確認
        config = browser_manager.performance_config
        print(f"  ✅ パフォーマンス設定確認: {len(config)}項目")
        print(f"    - ブロックリソース: {config['block_resources']}")
        print(f"    - ブロックドメイン数: {len(config['block_domains'])}")
        print(f"    - ビューポート: {config['viewport']}")
        
        # 状態確認
        status = browser_manager.get_status()
        print(f"  ✅ 初期状態: browser_active={status['browser_active']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ ブラウザマネージャーテスト失敗: {e}")
        return False

async def test_ai_handler_factory():
    """AIハンドラーファクトリーのテスト"""
    print("🤖 AIハンドラーファクトリーテスト開始...")
    
    try:
        # ファクトリーでハンドラー作成テスト（初期化なし）
        browser_manager = EnhancedBrowserManager(headless=True)
        
        # ChatGPTハンドラーの作成テスト
        handler = AIHandlerFactory.create_handler('chatgpt', browser_manager)
        if handler:
            print(f"  ✅ ChatGPTハンドラー作成: {type(handler).__name__}")
            
            # 統計情報の確認
            stats = handler.get_statistics()
            print(f"    - サービス: {stats['service']}")
            print(f"    - エラー統計: {stats['error_stats']}")
            print(f"    - 処理統計: {stats['processing_stats']}")
        else:
            print("  ❌ ChatGPTハンドラー作成失敗")
            return False
        
        # 不明なサービスのテスト
        unknown_handler = AIHandlerFactory.create_handler('unknown', browser_manager)
        if unknown_handler is None:
            print("  ✅ 不明サービスの適切な処理確認")
        else:
            print("  ❌ 不明サービスの処理に問題")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ AIハンドラーファクトリーテスト失敗: {e}")
        return False

async def test_session_encryption():
    """セッション暗号化機能のテスト"""
    print("🔐 セッション暗号化機能のテスト開始...")
    
    try:
        session_manager = EnhancedSessionManager()
        
        # 暗号化キーの存在確認
        key_file = session_manager.storage_dir / ".encryption_key"
        if key_file.exists():
            print("  ✅ 暗号化キーファイル存在確認")
            
            # ファイル権限の確認
            permissions = oct(os.stat(key_file).st_mode)[-3:]
            print(f"  ✅ キーファイル権限: {permissions}")
            
            if permissions == '400':
                print("  ✅ 適切なセキュリティ権限設定")
            else:
                print(f"  ⚠️  セキュリティ権限要注意: {permissions}")
        else:
            print("  ✅ 暗号化キー自動生成機能確認")
        
        # Fernet暗号化オブジェクトの確認
        if hasattr(session_manager, 'fernet') and session_manager.fernet:
            print("  ✅ Fernet暗号化オブジェクト初期化確認")
        else:
            print("  ❌ Fernet暗号化オブジェクト初期化失敗")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ セッション暗号化テスト失敗: {e}")
        return False

async def run_all_tests():
    """全テストの実行"""
    print("=" * 60)
    print("🚀 拡張機能テストスイートの実行開始")
    print("=" * 60)
    
    test_results = {}
    
    # 各テストを実行
    tests = [
        ("セッション管理", test_enhanced_session_manager),
        ("セレクター戦略", test_enhanced_selector_strategy),
        ("ブラウザマネージャー", test_browser_manager_initialization),
        ("AIハンドラーファクトリー", test_ai_handler_factory),
        ("セッション暗号化", test_session_encryption),
    ]
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}テスト:")
        try:
            result = await test_func()
            test_results[test_name] = result
        except Exception as e:
            print(f"  ❌ {test_name}テスト実行エラー: {e}")
            test_results[test_name] = False
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 総合結果: {passed}/{total} テスト成功")
    
    if passed == total:
        print("🎉 全テストが成功しました！")
        return True
    else:
        print("⚠️  一部テストが失敗しました。")
        return False

if __name__ == "__main__":
    # 非同期メイン関数の実行
    success = asyncio.run(run_all_tests())
    exit_code = 0 if success else 1
    sys.exit(exit_code)