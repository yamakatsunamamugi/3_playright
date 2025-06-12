#!/usr/bin/env python3
"""
最新Cloudflare回避・AIサービス自動ログイン デモスクリプト
2024年最新技術を統合した実証デモ

使用例:
python demo_latest_cloudflare_bypass.py --service chatgpt --headless false
python demo_latest_cloudflare_bypass.py --service claude --debug true
python demo_latest_cloudflare_bypass.py --service gemini --use-google true
"""

import asyncio
import argparse
import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.browser.cloudflare_bypass_manager import CloudflareBypassManager
from src.browser.ai_service_login_handlers import AIServiceLoginManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/cloudflare_bypass_demo.log')
    ]
)

logger = logging.getLogger(__name__)


class CloudflareBypassDemo:
    """
    Cloudflare回避・AIサービスログインデモクラス
    """
    
    def __init__(
        self,
        headless: bool = False,
        debug_mode: bool = False,
        proxy: str = None
    ):
        self.headless = headless
        self.debug_mode = debug_mode
        self.proxy = proxy
        
        # コンポーネント初期化
        self.browser_manager = CloudflareBypassManager(
            headless=headless,
            debug_mode=debug_mode,
            proxy=proxy
        )
        self.login_manager = AIServiceLoginManager()
        
        # テスト結果
        self.test_results = {
            'browser_init': False,
            'cloudflare_bypass': False,
            'login_success': False,
            'session_persistence': False,
            'error_messages': []
        }
    
    async def run_comprehensive_test(self, service_name: str, credentials: Dict[str, Any] = None):
        """
        包括的なテストを実行
        
        Args:
            service_name: テストするサービス名
            credentials: ログイン情報（省略可）
        """
        try:
            logger.info("=" * 60)
            logger.info("🚀 Cloudflare回避・AIサービスログイン 最新技術デモ開始")
            logger.info("=" * 60)
            
            # Step 1: ブラウザマネージャー初期化
            logger.info("📦 Step 1: ブラウザマネージャー初期化")
            await self._test_browser_initialization()
            
            # Step 2: Cloudflare回避テスト
            logger.info("🛡️  Step 2: Cloudflare回避機能テスト")
            await self._test_cloudflare_bypass(service_name)
            
            # Step 3: AIサービスログインテスト
            logger.info("🔐 Step 3: AIサービスログインテスト")
            await self._test_ai_service_login(service_name, credentials)
            
            # Step 4: セッション永続化テスト
            logger.info("💾 Step 4: セッション永続化テスト")
            await self._test_session_persistence(service_name)
            
            # Step 5: パフォーマンス測定
            logger.info("⚡ Step 5: パフォーマンス測定")
            await self._test_performance_metrics()
            
            # 結果レポート
            await self._generate_test_report()
            
        except Exception as e:
            logger.error(f"❌ デモ実行中にエラーが発生: {e}")
            self.test_results['error_messages'].append(str(e))
        finally:
            await self._cleanup()
    
    async def _test_browser_initialization(self):
        """
        ブラウザ初期化テスト
        """
        try:
            logger.info("  🔧 ブラウザマネージャーを初期化中...")
            
            success = await self.browser_manager.initialize()
            
            if success:
                logger.info("  ✅ ブラウザ初期化成功")
                self.test_results['browser_init'] = True
                
                # ブラウザステータスを表示
                status = self.browser_manager.get_status()
                logger.info(f"  📊 ブラウザステータス: {status}")
            else:
                logger.error("  ❌ ブラウザ初期化失敗")
                self.test_results['error_messages'].append("Browser initialization failed")
                
        except Exception as e:
            logger.error(f"  ❌ ブラウザ初期化エラー: {e}")
            self.test_results['error_messages'].append(f"Browser init error: {e}")
    
    async def _test_cloudflare_bypass(self, service_name: str):
        """
        Cloudflare回避テスト
        """
        try:
            logger.info("  🛡️  Cloudflare回避機能をテスト中...")
            
            # サービス用のコンテキスト作成
            context = await self.browser_manager.create_stealth_context(
                service_name=service_name,
                restore_session=False
            )
            
            if not context:
                logger.error("  ❌ ステルスコンテキスト作成失敗")
                return
            
            # ページ作成
            page = await self.browser_manager.create_page_with_stealth(
                service_name=service_name
            )
            
            if not page:
                logger.error("  ❌ ステルスページ作成失敗")
                return
            
            # Cloudflareが有効なサイトをテスト
            test_urls = [
                "https://chat.openai.com",
                "https://claude.ai",
                "https://gemini.google.com"
            ]
            
            for url in test_urls:
                logger.info(f"    🌐 テストURL: {url}")
                
                success = await self.browser_manager.safe_goto(page, url)
                
                if success:
                    logger.info(f"    ✅ {url} アクセス成功")
                    
                    # ページタイトルを確認
                    title = await page.title()
                    logger.info(f"    📄 ページタイトル: {title}")
                    
                    # Cloudflareチャレンジが発生していないか確認
                    is_challenge = await self.browser_manager._is_cloudflare_challenge(page)
                    if not is_challenge:
                        logger.info("    🎉 Cloudflareチャレンジ回避成功")
                        self.test_results['cloudflare_bypass'] = True
                    else:
                        logger.warning("    ⚠️  Cloudflareチャレンジ検出")
                else:
                    logger.error(f"    ❌ {url} アクセス失敗")
                
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"  ❌ Cloudflare回避テストエラー: {e}")
            self.test_results['error_messages'].append(f"Cloudflare bypass error: {e}")
    
    async def _test_ai_service_login(self, service_name: str, credentials: Dict[str, Any]):
        """
        AIサービスログインテスト
        """
        try:
            logger.info(f"  🔐 {service_name.upper()}ログインをテスト中...")
            
            # ページとコンテキストを取得
            page = self.browser_manager.pages.get(service_name)
            context = self.browser_manager.contexts.get(service_name)
            
            if not page or not context:
                logger.error("  ❌ ページまたはコンテキストが見つかりません")
                return
            
            # ログイン状態をチェック
            is_logged_in = await self.login_manager.check_login_status(
                service_name, page, context
            )
            
            if is_logged_in:
                logger.info("  ✅ 既にログイン済み")
                self.test_results['login_success'] = True
                return
            
            # ログイン情報がない場合のデフォルト設定
            if not credentials:
                credentials = {'use_google': True}  # デフォルトでGoogle認証を使用
            
            # ログイン実行
            logger.info("  🔄 ログイン処理を開始...")
            login_success = await self.login_manager.login_to_service(
                service_name, page, context, credentials
            )
            
            if login_success:
                logger.info("  ✅ ログイン成功")
                self.test_results['login_success'] = True
                
                # ログイン後のページ情報を表示
                title = await page.title()
                url = page.url
                logger.info(f"  📄 ログイン後タイトル: {title}")
                logger.info(f"  🌐 ログイン後URL: {url}")
            else:
                logger.error("  ❌ ログイン失敗")
                
        except Exception as e:
            logger.error(f"  ❌ AIサービスログインテストエラー: {e}")
            self.test_results['error_messages'].append(f"AI service login error: {e}")
    
    async def _test_session_persistence(self, service_name: str):
        """
        セッション永続化テスト
        """
        try:
            logger.info("  💾 セッション永続化をテスト中...")
            
            # セッションを保存
            save_success = await self.browser_manager.save_session(service_name)
            
            if save_success:
                logger.info("  ✅ セッション保存成功")
                
                # セッションファイルの存在確認
                session_file = self.browser_manager.session_dir / f"{service_name}_session.json"
                if session_file.exists():
                    logger.info(f"  📁 セッションファイル: {session_file}")
                    
                    # セッションファイルの内容を表示（認証情報は除く）
                    try:
                        with open(session_file, 'r') as f:
                            session_data = json.load(f)
                        
                        cookies_count = len(session_data.get('cookies', []))
                        origins_count = len(session_data.get('origins', []))
                        
                        logger.info(f"  🍪 保存されたCookie数: {cookies_count}")
                        logger.info(f"  🌐 保存されたオリジン数: {origins_count}")
                        
                        self.test_results['session_persistence'] = True
                        
                    except Exception as e:
                        logger.warning(f"  ⚠️  セッションファイル読み取りエラー: {e}")
                else:
                    logger.error("  ❌ セッションファイルが作成されませんでした")
            else:
                logger.error("  ❌ セッション保存失敗")
                
        except Exception as e:
            logger.error(f"  ❌ セッション永続化テストエラー: {e}")
            self.test_results['error_messages'].append(f"Session persistence error: {e}")
    
    async def _test_performance_metrics(self):
        """
        パフォーマンス測定
        """
        try:
            logger.info("  ⚡ パフォーマンス測定中...")
            
            status = self.browser_manager.get_status()
            
            logger.info(f"  📊 アクティブコンテキスト数: {len(status['contexts'])}")
            logger.info(f"  📊 アクティブページ数: {len(status['pages'])}")
            logger.info(f"  📊 一時ディレクトリ数: {status['temp_dirs_count']}")
            
            # メモリ使用量（概算）
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            logger.info(f"  📊 メモリ使用量: {memory_mb:.1f} MB")
            
            if memory_mb < 500:  # 500MB未満
                logger.info("  ✅ メモリ使用量: 良好")
            elif memory_mb < 1000:  # 1GB未満
                logger.info("  ⚠️  メモリ使用量: やや高い")
            else:
                logger.warning("  ❌ メモリ使用量: 高い")
                
        except Exception as e:
            logger.error(f"  ❌ パフォーマンス測定エラー: {e}")
    
    async def _generate_test_report(self):
        """
        テスト結果レポートを生成
        """
        logger.info("=" * 60)
        logger.info("📋 テスト結果レポート")
        logger.info("=" * 60)
        
        total_tests = 4
        passed_tests = sum([
            self.test_results['browser_init'],
            self.test_results['cloudflare_bypass'],
            self.test_results['login_success'],
            self.test_results['session_persistence']
        ])
        
        logger.info(f"📊 テスト結果: {passed_tests}/{total_tests} 成功")
        logger.info(f"✅ ブラウザ初期化: {'成功' if self.test_results['browser_init'] else '失敗'}")
        logger.info(f"🛡️  Cloudflare回避: {'成功' if self.test_results['cloudflare_bypass'] else '失敗'}")
        logger.info(f"🔐 ログイン: {'成功' if self.test_results['login_success'] else '失敗'}")
        logger.info(f"💾 セッション永続化: {'成功' if self.test_results['session_persistence'] else '失敗'}")
        
        if self.test_results['error_messages']:
            logger.error("❌ エラーメッセージ:")
            for error in self.test_results['error_messages']:
                logger.error(f"  - {error}")
        
        success_rate = (passed_tests / total_tests) * 100
        logger.info(f"🎯 成功率: {success_rate:.1f}%")
        
        if success_rate >= 75:
            logger.info("🎉 テスト結果: 優秀")
        elif success_rate >= 50:
            logger.info("⚠️  テスト結果: 良好")
        else:
            logger.warning("❌ テスト結果: 改善が必要")
    
    async def _cleanup(self):
        """
        リソースのクリーンアップ
        """
        try:
            logger.info("🧹 クリーンアップ中...")
            await self.browser_manager.cleanup()
            logger.info("✅ クリーンアップ完了")
        except Exception as e:
            logger.error(f"❌ クリーンアップエラー: {e}")


async def main():
    """
    メイン関数
    """
    parser = argparse.ArgumentParser(description="Cloudflare回避・AIサービスログインデモ")
    parser.add_argument(
        '--service',
        choices=['chatgpt', 'claude', 'gemini'],
        default='chatgpt',
        help='テストするAIサービス'
    )
    parser.add_argument(
        '--headless',
        type=str,
        choices=['true', 'false'],
        default='false',
        help='ヘッドレスモードで実行'
    )
    parser.add_argument(
        '--debug',
        type=str,
        choices=['true', 'false'],
        default='false',
        help='デバッグモードを有効化'
    )
    parser.add_argument(
        '--use-google',
        type=str,
        choices=['true', 'false'],
        default='true',
        help='Google認証を使用'
    )
    parser.add_argument(
        '--proxy',
        type=str,
        help='プロキシサーバー（形式: host:port）'
    )
    parser.add_argument(
        '--email',
        type=str,
        help='ログイン用Email（ChatGPT/Claude）'
    )
    parser.add_argument(
        '--password',
        type=str,
        help='ログイン用Password（ChatGPT）'
    )
    
    args = parser.parse_args()
    
    # 引数の変換
    headless = args.headless.lower() == 'true'
    debug_mode = args.debug.lower() == 'true'
    use_google = args.use_google.lower() == 'true'
    
    # 認証情報の設定
    credentials = {}
    if use_google:
        credentials['use_google'] = True
    if args.email:
        credentials['email'] = args.email
    if args.password:
        credentials['password'] = args.password
    
    # ログディレクトリを作成
    Path('logs').mkdir(exist_ok=True)
    
    # デモ実行
    demo = CloudflareBypassDemo(
        headless=headless,
        debug_mode=debug_mode,
        proxy=args.proxy
    )
    
    await demo.run_comprehensive_test(args.service, credentials)


if __name__ == "__main__":
    asyncio.run(main())