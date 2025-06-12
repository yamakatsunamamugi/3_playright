"""
ブラウザマネージャー選択ユーティリティ
状況に応じて最適なブラウザマネージャーを選択
"""

import logging
from typing import Optional, Union
from .simple_browser_manager import SimpleBrowserManager
from .stealth_browser_manager import StealthBrowserManager
from .real_chrome_manager import RealChromeManager
from .enhanced_real_chrome_manager import EnhancedRealChromeManager

logger = logging.getLogger(__name__)


class BrowserSelector:
    """ブラウザマネージャーを選択するクラス"""
    
    BROWSER_TYPES = {
        'simple': SimpleBrowserManager,
        'stealth': StealthBrowserManager,
        'real_chrome': RealChromeManager,
        'enhanced': EnhancedRealChromeManager
    }
    
    @classmethod
    def create_browser_manager(
        cls, 
        browser_type: str = 'enhanced',
        profile_name: str = 'Default',
        headless: bool = False
    ) -> Optional[Union[SimpleBrowserManager, StealthBrowserManager, RealChromeManager, EnhancedRealChromeManager]]:
        """
        指定されたタイプのブラウザマネージャーを作成
        
        Args:
            browser_type: ブラウザタイプ ('simple', 'stealth', 'real_chrome', 'enhanced')
            profile_name: Chromeプロファイル名（real_chrome, enhancedのみ）
            headless: ヘッドレスモード
            
        Returns:
            ブラウザマネージャーインスタンス
        """
        if browser_type not in cls.BROWSER_TYPES:
            logger.error(f"Unknown browser type: {browser_type}")
            return None
        
        try:
            if browser_type in ['real_chrome', 'enhanced']:
                # プロファイルを使用するマネージャー
                return cls.BROWSER_TYPES[browser_type](
                    profile_name=profile_name,
                    headless=headless
                )
            else:
                # 通常のマネージャー
                return cls.BROWSER_TYPES[browser_type](headless=headless)
                
        except Exception as e:
            logger.error(f"Failed to create browser manager: {e}")
            return None
    
    @classmethod
    async def auto_select_browser_manager(
        cls,
        target_site: str,
        profile_name: str = 'Default',
        headless: bool = False
    ) -> Optional[Union[SimpleBrowserManager, StealthBrowserManager, RealChromeManager, EnhancedRealChromeManager]]:
        """
        ターゲットサイトに基づいて最適なブラウザマネージャーを自動選択
        
        Args:
            target_site: アクセスするサイト名
            profile_name: Chromeプロファイル名
            headless: ヘッドレスモード
            
        Returns:
            最適なブラウザマネージャーインスタンス
        """
        # Cloudflareを使用しているサイト
        cloudflare_sites = ['chatgpt', 'claude', 'openai', 'anthropic']
        
        # 高度な検出を行うサイト
        advanced_detection_sites = ['google', 'gmail', 'youtube']
        
        site_lower = target_site.lower()
        
        # Cloudflareサイトの場合
        if any(cf_site in site_lower for cf_site in cloudflare_sites):
            logger.info(f"Detected Cloudflare site: {target_site}")
            # まずEnhanced Real Chromeを試す
            manager = cls.create_browser_manager('enhanced', profile_name, headless)
            if manager:
                logger.info("Using Enhanced Real Chrome Manager for Cloudflare bypass")
                return manager
            
            # フォールバック
            logger.warning("Enhanced failed, falling back to Stealth")
            return cls.create_browser_manager('stealth', profile_name, headless)
        
        # 高度な検出サイトの場合
        elif any(adv_site in site_lower for adv_site in advanced_detection_sites):
            logger.info(f"Detected advanced detection site: {target_site}")
            return cls.create_browser_manager('stealth', profile_name, headless)
        
        # その他のサイト
        else:
            logger.info(f"Using simple browser for: {target_site}")
            return cls.create_browser_manager('simple', profile_name, headless)
    
    @classmethod
    def get_browser_info(cls) -> dict:
        """利用可能なブラウザタイプの情報を取得"""
        return {
            'simple': {
                'name': 'シンプルブラウザ',
                'description': '基本的なブラウザ（高速）',
                'recommended_for': '一般的なサイト'
            },
            'stealth': {
                'name': 'ステルスブラウザ',
                'description': '高度な偽装機能付き',
                'recommended_for': 'Bot検出があるサイト'
            },
            'real_chrome': {
                'name': 'リアルChrome',
                'description': '実際のChromeプロファイルを使用',
                'recommended_for': 'ログイン必要なサイト'
            },
            'enhanced': {
                'name': '強化版リアルChrome',
                'description': 'CDP接続で既存セッションを利用',
                'recommended_for': 'Cloudflare/高度な検出があるサイト'
            }
        }