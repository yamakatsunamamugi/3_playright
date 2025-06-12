"""
設定の保存・読み込み・管理を行うモジュール

GUIアプリケーションの設定を JSON ファイルで永続化し、
ユーザーの操作設定を次回起動時に復元する機能を提供
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """アプリケーション設定の管理クラス"""
    
    def __init__(self, config_file: str = "config/user_settings.json"):
        """
        ConfigManagerを初期化
        
        Args:
            config_file: 設定ファイルのパス
        """
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_default_config()
        self.load_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を作成"""
        return {
            "spreadsheet": {
                "last_url": "",
                "last_sheet": ""
            },
            "ai_settings": {
                "ChatGPT": {
                    "enabled": False,
                    "model": "gpt-4",
                    "settings": {
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                },
                "Claude": {
                    "enabled": False,
                    "model": "claude-3-opus-20240229",
                    "settings": {
                        "max_tokens": 4000
                    }
                },
                "Gemini": {
                    "enabled": False,
                    "model": "gemini-pro",
                    "settings": {
                        "temperature": 0.9,
                        "max_output_tokens": 2048
                    }
                },
                "Genspark": {
                    "enabled": False,
                    "model": "genspark-latest",
                    "settings": {}
                },
                "Google AI Studio": {
                    "enabled": False,
                    "model": "gemini-pro",
                    "settings": {
                        "safety_settings": "moderate"
                    }
                }
            },
            "processing": {
                "max_retries": 5,
                "retry_delay": 10,
                "timeout": 300
            },
            "ui": {
                "window_width": 1000,
                "window_height": 700,
                "log_lines": 100
            }
        }
    
    def load_config(self) -> bool:
        """
        設定ファイルから設定を読み込む
        
        Returns:
            読み込み成功時 True、失敗時 False
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self._merge_configs(saved_config)
                    logger.info(f"設定ファイルを読み込みました: {self.config_file}")
                    return True
            else:
                logger.info("設定ファイルが存在しないため、デフォルト設定を使用します")
                return False
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        現在の設定をファイルに保存
        
        Returns:
            保存成功時 True、失敗時 False
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"設定ファイルを保存しました: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"設定ファイルの保存に失敗しました: {e}")
            return False
    
    def _merge_configs(self, saved_config: Dict[str, Any]):
        """
        保存された設定とデフォルト設定をマージ
        
        Args:
            saved_config: 保存された設定
        """
        def deep_merge(default: Dict, saved: Dict) -> Dict:
            result = default.copy()
            for key, value in saved.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        self._config = deep_merge(self._config, saved_config)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        設定値を取得（ドット記法対応）
        
        Args:
            key_path: 設定のキーパス（例: "ai_settings.ChatGPT.enabled"）
            default: デフォルト値
            
        Returns:
            設定値またはデフォルト値
        """
        try:
            keys = key_path.split('.')
            value = self._config
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """
        設定値を設定（ドット記法対応）
        
        Args:
            key_path: 設定のキーパス
            value: 設定する値
        """
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def get_ai_config(self, ai_name: str) -> Dict[str, Any]:
        """
        特定のAIの設定を取得
        
        Args:
            ai_name: AI名
            
        Returns:
            AI設定辞書
        """
        return self.get(f"ai_settings.{ai_name}", {})
    
    def set_ai_config(self, ai_name: str, config: Dict[str, Any]):
        """
        特定のAIの設定を保存
        
        Args:
            ai_name: AI名
            config: AI設定辞書
        """
        self.set(f"ai_settings.{ai_name}", config)
    
    def get_spreadsheet_config(self) -> Dict[str, str]:
        """スプレッドシート設定を取得"""
        return self.get("spreadsheet", {})
    
    def set_spreadsheet_config(self, url: str, sheet: str):
        """
        スプレッドシート設定を保存
        
        Args:
            url: スプレッドシートURL
            sheet: シート名
        """
        self.set("spreadsheet.last_url", url)
        self.set("spreadsheet.last_sheet", sheet)
    
    def get_ui_config(self) -> Dict[str, Any]:
        """UI設定を取得"""
        return self.get("ui", {})
    
    def auto_save(self):
        """設定を自動保存（エラーが発生しても継続）"""
        try:
            self.save_config()
        except Exception as e:
            logger.warning(f"設定の自動保存に失敗しました: {e}")


# グローバルインスタンス（シングルトンパターン）
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """ConfigManagerのグローバルインスタンスを取得"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager