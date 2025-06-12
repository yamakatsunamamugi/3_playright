"""
設定管理モジュール

アプリケーションの設定を管理する。
- UI設定（ウィンドウサイズ、位置など）
- AI設定（モデル選択、API設定など）
- スプレッドシート設定（URL、シート名など）
- その他のユーザー設定
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        ConfigManagerを初期化
        
        Args:
            config_file: 設定ファイル名
        """
        self.config_file = Path(config_file)
        self.config_data: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """
        設定ファイルを読み込む
        
        Returns:
            bool: 読み込み成功時True
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                logger.info(f"設定ファイルを読み込みました: {self.config_file}")
            else:
                # デフォルト設定で初期化
                self.config_data = self._get_default_config()
                logger.info("デフォルト設定で初期化しました")
            return True
            
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗: {e}")
            self.config_data = self._get_default_config()
            return False
    
    def save_config(self) -> bool:
        """
        設定ファイルに保存
        
        Returns:
            bool: 保存成功時True
        """
        try:
            # 設定ディレクトリを作成（存在しない場合）
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"設定ファイルを保存しました: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"設定ファイルの保存に失敗: {e}")
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        デフォルト設定を取得
        
        Returns:
            Dict[str, Any]: デフォルト設定辞書
        """
        return {
            "ui": {
                "window_width": 1200,
                "window_height": 800,
                "window_x": -1,  # -1は中央配置を意味
                "window_y": -1,
                "theme": "default",
                "font_size": 10
            },
            "spreadsheet": {
                "last_url": "",
                "last_sheet": "",
                "auto_load": False
            },
            "ai_tools": {
                "ChatGPT": {
                    "enabled": False,
                    "model": "gpt-4o",
                    "settings": {
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                },
                "Claude": {
                    "enabled": False,
                    "model": "claude-3-5-sonnet-20241022",
                    "settings": {
                        "max_tokens": 2000
                    }
                },
                "Gemini": {
                    "enabled": False,
                    "model": "gemini-2.0-flash-exp",
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
                    "model": "gemini-2.0-flash-exp",
                    "settings": {
                        "temperature": 0.9,
                        "max_output_tokens": 2048
                    }
                }
            },
            "processing": {
                "retry_count": 5,
                "retry_delay": 10,
                "timeout": 120,
                "parallel_processing": False
            },
            "logging": {
                "level": "INFO",
                "max_log_files": 10,
                "max_log_size_mb": 10
            }
        }
    
    def get_ui_config(self) -> Dict[str, Any]:
        """UI設定を取得"""
        return self.config_data.get("ui", {})
    
    def set_ui_config(self, ui_config: Dict[str, Any]):
        """UI設定を設定"""
        if "ui" not in self.config_data:
            self.config_data["ui"] = {}
        self.config_data["ui"].update(ui_config)
    
    def get_spreadsheet_config(self) -> Dict[str, Any]:
        """スプレッドシート設定を取得"""
        return self.config_data.get("spreadsheet", {})
    
    def set_spreadsheet_config(self, spreadsheet_config: Dict[str, Any]):
        """スプレッドシート設定を設定"""
        if "spreadsheet" not in self.config_data:
            self.config_data["spreadsheet"] = {}
        self.config_data["spreadsheet"].update(spreadsheet_config)
    
    def get_ai_tools_config(self) -> Dict[str, Any]:
        """AIツール設定を取得"""
        return self.config_data.get("ai_tools", {})
    
    def set_ai_tools_config(self, ai_tools_config: Dict[str, Any]):
        """AIツール設定を設定"""
        if "ai_tools" not in self.config_data:
            self.config_data["ai_tools"] = {}
        self.config_data["ai_tools"].update(ai_tools_config)
    
    def get_processing_config(self) -> Dict[str, Any]:
        """処理設定を取得"""
        return self.config_data.get("processing", {})
    
    def set_processing_config(self, processing_config: Dict[str, Any]):
        """処理設定を設定"""
        if "processing" not in self.config_data:
            self.config_data["processing"] = {}
        self.config_data["processing"].update(processing_config)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        指定されたキーの設定値を取得
        
        Args:
            key: 設定キー（ドット記法対応。例: "ui.window_width"）
            default: デフォルト値
            
        Returns:
            設定値
        """
        keys = key.split('.')
        data = self.config_data
        
        try:
            for k in keys:
                data = data[k]
            return data
        except (KeyError, TypeError):
            return default
    
    def set_config(self, key: str, value: Any):
        """
        指定されたキーに設定値を設定
        
        Args:
            key: 設定キー（ドット記法対応。例: "ui.window_width"）
            value: 設定値
        """
        keys = key.split('.')
        data = self.config_data
        
        # 辞書の階層を作成
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        
        # 最後のキーに値を設定
        data[keys[-1]] = value
    
    def reset_to_default(self):
        """設定をデフォルトにリセット"""
        self.config_data = self._get_default_config()
        logger.info("設定をデフォルトにリセットしました")
    
    def export_config(self, export_file: str) -> bool:
        """
        設定をファイルにエクスポート
        
        Args:
            export_file: エクスポート先ファイル
            
        Returns:
            bool: エクスポート成功時True
        """
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"設定をエクスポートしました: {export_file}")
            return True
            
        except Exception as e:
            logger.error(f"設定のエクスポートに失敗: {e}")
            return False
    
    def import_config(self, import_file: str) -> bool:
        """
        設定をファイルからインポート
        
        Args:
            import_file: インポート元ファイル
            
        Returns:
            bool: インポート成功時True
        """
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 設定をマージ（既存設定を保持しつつ新しい設定を上書き）
            self._merge_config(self.config_data, imported_config)
            
            logger.info(f"設定をインポートしました: {import_file}")
            return True
            
        except Exception as e:
            logger.error(f"設定のインポートに失敗: {e}")
            return False
    
    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]):
        """
        設定辞書を再帰的にマージ
        
        Args:
            target: マージ先辞書
            source: マージ元辞書
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value


# グローバルConfigManagerインスタンス
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    ConfigManagerのシングルトンインスタンスを取得
    
    Returns:
        ConfigManager: ConfigManagerインスタンス
    """
    global _config_manager_instance
    
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    
    return _config_manager_instance


def reset_config_manager():
    """ConfigManagerインスタンスをリセット（主にテスト用）"""
    global _config_manager_instance
    _config_manager_instance = None