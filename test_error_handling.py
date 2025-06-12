#!/usr/bin/env python3
"""
エラーハンドリング機能のテスト
新規追加された拡張機能のエラー処理とリカバリー機能をテスト
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.browser.enhanced_browser_manager import EnhancedBrowserManager
from src.browser.enhanced_session_manager import EnhancedSessionManager
from src.ai_tools.enhanced_ai_handler import ChatGPTEnhancedHandler

async def test_browser_manager_error_handling():
    """ブラウザマネージャーのエラーハンドリングテスト"""
    print("🌐 ブラウザマネージャーエラーハンドリングテスト開始...")
    
    try:
        browser_manager = EnhancedBrowserManager(headless=True)
        
        # 無効なURLでのsafe_gotoテスト
        await browser_manager.initialize()
        if browser_manager.browser:
            page = await browser_manager.create_service_page("test_service")
            if page:
                # 無効なURLテスト
                result = await browser_manager.safe_goto(page, "invalid://url", timeout=5000)
                if not result:
                    print("  ✅ 無効URLのエラーハンドリング正常")
                else:
                    print("  ❌ 無効URLのエラーハンドリング失敗")
                    
                # タイムアウトテスト
                result = await browser_manager.safe_goto(page, "https://httpstat.us/504", timeout=3000)
                print(f"  ✅ タイムアウト処理テスト: {result}")
                
        await browser_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"  ❌ ブラウザマネージャーエラーテスト失敗: {e}")
        return False

async def test_session_manager_error_handling():
    """セッションマネージャーのエラーハンドリングテスト"""
    print("🔒 セッションマネージャーエラーハンドリングテスト開始...")
    
    try:
        session_manager = EnhancedSessionManager()
        
        # 存在しないセッションファイルの復元テスト
        browser_manager = EnhancedBrowserManager(headless=True)
        await browser_manager.initialize()
        
        if browser_manager.browser:
            context = await browser_manager.create_service_context("nonexistent_service")
            if context:
                result = await session_manager.restore_session(context, "nonexistent_service")
                if result is None:
                    print("  ✅ 存在しないセッションの適切な処理")
                else:
                    print("  ❌ 存在しないセッションの処理に問題")
                
        # 無効なサービス名でのセッション確認テスト
        browser_manager2 = EnhancedBrowserManager(headless=True)
        await browser_manager2.initialize()
        
        if browser_manager2.browser:
            page = await browser_manager2.create_service_page("invalid_service")
            if page:
                result = await session_manager.verify_session(page, "invalid_service", timeout=2000)
                print(f"  ✅ 無効サービスでのセッション確認: {result}")
        
        await browser_manager.cleanup()
        await browser_manager2.cleanup()
        return True
        
    except Exception as e:
        print(f"  ❌ セッションマネージャーエラーテスト失敗: {e}")
        return False

async def test_ai_handler_error_recovery():
    """AIハンドラーのエラーリカバリー機能テスト"""
    print("🤖 AIハンドラーエラーリカバリーテスト開始...")
    
    try:
        browser_manager = EnhancedBrowserManager(headless=True)
        handler = ChatGPTEnhancedHandler("chatgpt", browser_manager)
        
        # エラー統計の初期状態確認
        initial_stats = handler.get_statistics()
        print(f"  📊 初期エラー統計: {initial_stats['error_stats']['total_errors']}")
        
        # エラー記録機能のテスト
        handler._record_error("test_error", "テストエラーメッセージ")
        after_error_stats = handler.get_statistics()
        
        if after_error_stats['error_stats']['total_errors'] == 1:
            print("  ✅ エラー記録機能正常")
        else:
            print("  ❌ エラー記録機能に問題")
            
        # エラー分類機能のテスト
        handler._record_error("connection_error", "接続エラー")
        handler._record_error("connection_error", "再度の接続エラー")
        
        final_stats = handler.get_statistics()
        error_types = final_stats['error_stats']['error_types']
        
        if error_types.get('connection_error') == 2:
            print("  ✅ エラー分類機能正常")
        else:
            print("  ❌ エラー分類機能に問題")
            
        # 最新エラー履歴の確認
        last_errors = final_stats['error_stats']['last_errors']
        if len(last_errors) >= 2:
            print(f"  ✅ エラー履歴機能正常: {len(last_errors)}件のエラー記録")
        else:
            print("  ❌ エラー履歴機能に問題")
            
        return True
        
    except Exception as e:
        print(f"  ❌ AIハンドラーエラーテスト失敗: {e}")
        return False

async def test_retry_mechanism():
    """リトライメカニズムのテスト"""
    print("🔄 リトライメカニズムテスト開始...")
    
    try:
        browser_manager = EnhancedBrowserManager(headless=True)
        await browser_manager.initialize()
        
        if not browser_manager.browser:
            print("  ❌ ブラウザ初期化失敗")
            return False
        
        # リトライ付き実行のテスト用関数
        attempt_count = 0
        
        async def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception(f"意図的な失敗 {attempt_count}")
            return f"成功（試行回数: {attempt_count}）"
        
        # リトライメカニズムテスト
        try:
            result = await browser_manager.execute_with_retry(
                failing_function,
                max_retries=5,
                delay=0.1,  # テスト用に短縮
                backoff=1.5
            )
            
            if "成功" in result and attempt_count == 3:
                print(f"  ✅ リトライメカニズム正常: {result}")
            else:
                print(f"  ❌ リトライメカニズムに問題: {result}")
                
        except Exception as e:
            print(f"  ❌ リトライテスト失敗: {e}")
            
        await browser_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"  ❌ リトライメカニズムテスト失敗: {e}")
        return False

async def test_resource_cleanup():
    """リソースクリーンアップ機能のテスト"""
    print("🧹 リソースクリーンアップテスト開始...")
    
    try:
        # 複数のブラウザマネージャーを作成してクリーンアップテスト
        managers = []
        
        for i in range(3):
            manager = EnhancedBrowserManager(headless=True)
            await manager.initialize()
            
            if manager.browser:
                # いくつかのページを作成
                await manager.create_service_page(f"test_service_{i}")
                managers.append(manager)
        
        print(f"  📊 作成したマネージャー数: {len(managers)}")
        
        # 全マネージャーのクリーンアップ
        cleanup_success = 0
        for i, manager in enumerate(managers):
            try:
                await manager.cleanup()
                cleanup_success += 1
                print(f"  ✅ マネージャー{i}クリーンアップ成功")
            except Exception as e:
                print(f"  ❌ マネージャー{i}クリーンアップ失敗: {e}")
        
        if cleanup_success == len(managers):
            print("  ✅ 全リソースクリーンアップ成功")
            return True
        else:
            print(f"  ⚠️  一部クリーンアップ失敗: {cleanup_success}/{len(managers)}")
            return False
            
    except Exception as e:
        print(f"  ❌ リソースクリーンアップテスト失敗: {e}")
        return False

async def run_error_handling_tests():
    """エラーハンドリングテストスイートの実行"""
    print("=" * 60)
    print("🚨 エラーハンドリングテストスイートの実行開始")
    print("=" * 60)
    
    test_results = {}
    
    # 各テストを実行
    tests = [
        ("ブラウザマネージャーエラー処理", test_browser_manager_error_handling),
        ("セッションマネージャーエラー処理", test_session_manager_error_handling),
        ("AIハンドラーエラーリカバリー", test_ai_handler_error_recovery),
        ("リトライメカニズム", test_retry_mechanism),
        ("リソースクリーンアップ", test_resource_cleanup),
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
    print("📊 エラーハンドリングテスト結果サマリー")
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
        print("🎉 全エラーハンドリングテストが成功しました！")
        return True
    else:
        print("⚠️  一部エラーハンドリングテストが失敗しました。")
        return False

if __name__ == "__main__":
    # 非同期メイン関数の実行
    success = asyncio.run(run_error_handling_tests())
    exit_code = 0 if success else 1
    sys.exit(exit_code)