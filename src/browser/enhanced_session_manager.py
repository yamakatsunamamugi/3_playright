"""拡張セッション管理 - 認証状態の永続化と自動復元"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
from cryptography.fernet import Fernet
import base64

from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)


class EnhancedSessionManager:
    """認証セッションの永続化と管理を行うクラス
    
    - 認証状態の暗号化保存
    - セッション有効性チェック
    - 自動再認証メカニズム
    - マルチサービス対応
    """
    
    def __init__(self, storage_dir: str = "auth_states"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # 暗号化キーの管理
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # セッションメタデータ
        self.session_metadata_file = self.storage_dir / "session_metadata.json"
        self.session_metadata = self._load_session_metadata()
        
        # サービス別の認証確認設定
        self.auth_check_configs = {
            'chatgpt': {
                'url': 'https://chat.openai.com',
                'auth_indicator': 'textarea[data-testid="textbox"]',
                'login_url': 'https://chat.openai.com/auth/login'
            },
            'claude': {
                'url': 'https://claude.ai',
                'auth_indicator': 'div[contenteditable="true"]',
                'login_url': 'https://claude.ai/login'
            },
            'gemini': {
                'url': 'https://gemini.google.com',
                'auth_indicator': 'div[contenteditable="true"]',
                'login_url': 'https://gemini.google.com'
            },
            'genspark': {
                'url': 'https://www.genspark.ai',
                'auth_indicator': 'textarea',
                'login_url': 'https://www.genspark.ai/signin'
            },
            'google_ai_studio': {
                'url': 'https://aistudio.google.com',
                'auth_indicator': 'div.prompt-textarea',
                'login_url': 'https://aistudio.google.com'
            }
        }
    
    def _get_or_create_encryption_key(self) -> bytes:
        """暗号化キーを取得または作成"""
        key_file = self.storage_dir / ".encryption_key"
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            # ファイルを読み取り専用に設定（セキュリティ強化）
            os.chmod(key_file, 0o400)
            return key
    
    def _load_session_metadata(self) -> Dict[str, Any]:
        """セッションメタデータを読み込む"""
        if self.session_metadata_file.exists():
            try:
                data = json.loads(self.session_metadata_file.read_text())
                return data
            except Exception as e:
                logger.error(f"Failed to load session metadata: {e}")
        
        return {}
    
    def _save_session_metadata(self):
        """セッションメタデータを保存"""
        try:
            self.session_metadata_file.write_text(
                json.dumps(self.session_metadata, indent=2)
            )
        except Exception as e:
            logger.error(f"Failed to save session metadata: {e}")
    
    async def save_session(
        self,
        context: BrowserContext,
        service_name: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """セッション状態を暗号化して保存
        
        Args:
            context: ブラウザコンテキスト
            service_name: サービス名
            additional_data: 追加で保存するデータ
            
        Returns:
            保存成功時True
        """
        try:
            # セッション状態を取得
            state = await context.storage_state()
            
            # 重要な情報のみを抽出（サイズ削減）
            minimal_state = {
                'cookies': state.get('cookies', []),
                'origins': []  # localStorage/sessionStorageは必要に応じて
            }
            
            # 追加データがある場合はマージ
            if additional_data:
                minimal_state['additional'] = additional_data
            
            # JSONに変換して暗号化
            state_json = json.dumps(minimal_state)
            encrypted_state = self.fernet.encrypt(state_json.encode())
            
            # ファイルに保存
            state_file = self.storage_dir / f"{service_name}_session.enc"
            state_file.write_bytes(encrypted_state)
            
            # メタデータを更新
            self.session_metadata[service_name] = {
                'saved_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
                'status': 'active'
            }
            self._save_session_metadata()
            
            logger.info(f"Session saved for {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session for {service_name}: {e}")
            return False
    
    async def restore_session(
        self,
        context: BrowserContext,
        service_name: str
    ) -> Optional[Dict[str, Any]]:
        """保存されたセッションを復元
        
        Args:
            context: ブラウザコンテキスト
            service_name: サービス名
            
        Returns:
            復元成功時は追加データ、失敗時はNone
        """
        try:
            state_file = self.storage_dir / f"{service_name}_session.enc"
            
            if not state_file.exists():
                logger.info(f"No saved session for {service_name}")
                return None
            
            # セッションの有効期限をチェック
            if not self._is_session_valid(service_name):
                logger.info(f"Session expired for {service_name}")
                return None
            
            # 暗号化されたデータを読み込み
            encrypted_state = state_file.read_bytes()
            
            # 復号化
            state_json = self.fernet.decrypt(encrypted_state).decode()
            state = json.loads(state_json)
            
            # Cookieを復元
            if 'cookies' in state:
                await context.add_cookies(state['cookies'])
            
            # localStorageを復元（必要に応じて）
            # for origin in state.get('origins', []):
            #     if 'localStorage' in origin:
            #         # localStorage復元のロジック
            
            logger.info(f"Session restored for {service_name}")
            
            # 追加データを返す
            return state.get('additional', {})
            
        except Exception as e:
            logger.error(f"Failed to restore session for {service_name}: {e}")
            return None
    
    def _is_session_valid(self, service_name: str) -> bool:
        """セッションが有効かチェック"""
        if service_name not in self.session_metadata:
            return False
        
        metadata = self.session_metadata[service_name]
        
        # ステータスチェック
        if metadata.get('status') != 'active':
            return False
        
        # 有効期限チェック
        expires_at = datetime.fromisoformat(metadata.get('expires_at', ''))
        if datetime.now() > expires_at:
            return False
        
        return True
    
    async def verify_session(
        self,
        page: Page,
        service_name: str,
        timeout: int = 10000
    ) -> bool:
        """セッションが実際に有効か確認
        
        Args:
            page: ページオブジェクト
            service_name: サービス名
            timeout: タイムアウト（ミリ秒）
            
        Returns:
            有効な場合True
        """
        if service_name not in self.auth_check_configs:
            logger.warning(f"No auth check config for {service_name}")
            return False
        
        config = self.auth_check_configs[service_name]
        
        try:
            # サービスのURLにアクセス
            await page.goto(config['url'], wait_until='domcontentloaded')
            
            # 認証インジケーターを探す
            try:
                await page.wait_for_selector(
                    config['auth_indicator'],
                    timeout=timeout
                )
                logger.info(f"Session verified for {service_name}")
                return True
            except:
                # ログインページにリダイレクトされているかチェック
                current_url = page.url
                if config['login_url'] in current_url:
                    logger.info(f"Redirected to login page for {service_name}")
                    return False
                
                # その他の理由で見つからない場合
                logger.warning(f"Auth indicator not found for {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Session verification failed for {service_name}: {e}")
            return False
    
    def invalidate_session(self, service_name: str):
        """セッションを無効化"""
        if service_name in self.session_metadata:
            self.session_metadata[service_name]['status'] = 'invalid'
            self._save_session_metadata()
        
        # セッションファイルを削除
        state_file = self.storage_dir / f"{service_name}_session.enc"
        if state_file.exists():
            state_file.unlink()
        
        logger.info(f"Session invalidated for {service_name}")
    
    async def auto_reauth(
        self,
        page: Page,
        service_name: str,
        manual_auth_callback=None
    ) -> bool:
        """自動再認証を試みる
        
        Args:
            page: ページオブジェクト
            service_name: サービス名
            manual_auth_callback: 手動認証が必要な場合のコールバック
            
        Returns:
            再認証成功時True
        """
        logger.info(f"Attempting auto re-authentication for {service_name}")
        
        # まず既存のセッションが使えるか確認
        if await self.verify_session(page, service_name):
            return True
        
        # セッションが無効な場合、無効化
        self.invalidate_session(service_name)
        
        # 手動認証コールバックがある場合は実行
        if manual_auth_callback:
            logger.info(f"Manual authentication required for {service_name}")
            success = await manual_auth_callback(page, service_name)
            
            if success:
                # 新しいセッションを保存
                context = page.context
                await self.save_session(context, service_name)
                return True
        
        return False
    
    def get_session_status(self) -> Dict[str, Dict[str, Any]]:
        """全サービスのセッション状態を取得"""
        status = {}
        
        for service_name, metadata in self.session_metadata.items():
            is_valid = self._is_session_valid(service_name)
            
            status[service_name] = {
                'valid': is_valid,
                'saved_at': metadata.get('saved_at'),
                'expires_at': metadata.get('expires_at'),
                'status': metadata.get('status')
            }
        
        return status
    
    def cleanup_expired_sessions(self):
        """期限切れセッションをクリーンアップ"""
        expired_services = []
        
        for service_name in list(self.session_metadata.keys()):
            if not self._is_session_valid(service_name):
                expired_services.append(service_name)
                self.invalidate_session(service_name)
        
        if expired_services:
            logger.info(f"Cleaned up expired sessions: {expired_services}")
        
        return expired_services


class SessionPool:
    """複数のセッションを管理するプール"""
    
    def __init__(self, max_sessions_per_service: int = 3):
        self.max_sessions = max_sessions_per_service
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.session_manager = EnhancedSessionManager()
    
    async def get_available_session(
        self,
        service_name: str,
        context: BrowserContext
    ) -> Optional[Page]:
        """利用可能なセッションを取得"""
        if service_name not in self.sessions:
            self.sessions[service_name] = []
        
        # 既存のセッションから利用可能なものを探す
        for session in self.sessions[service_name]:
            if not session['in_use']:
                session['in_use'] = True
                return session['page']
        
        # 新しいセッションを作成
        if len(self.sessions[service_name]) < self.max_sessions:
            page = await context.new_page()
            
            # 保存されたセッションを復元
            await self.session_manager.restore_session(context, service_name)
            
            session = {
                'page': page,
                'in_use': True,
                'created_at': datetime.now()
            }
            
            self.sessions[service_name].append(session)
            return page
        
        # 利用可能なセッションがない
        return None
    
    def release_session(self, service_name: str, page: Page):
        """セッションを解放"""
        if service_name in self.sessions:
            for session in self.sessions[service_name]:
                if session['page'] == page:
                    session['in_use'] = False
                    break