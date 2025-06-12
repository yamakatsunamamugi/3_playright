"""
列ごとのAI設定ウィジェット
各「コピー」列に対してAIとモデルを個別に選択できる機能
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Any, Optional, Callable
import asyncio
import threading
from pathlib import Path

from config.settings import settings
from src.utils.logger import get_logger
from src.ai_tools.model_fetcher import create_model_fetcher, ModelProvider

logger = get_logger(__name__)


class ColumnAIConfigWidget:
    """単一列用のAI設定ウィジェット"""
    
    def __init__(self, parent: tk.Widget, column_name: str, column_index: int, 
                 on_config_changed: Optional[Callable] = None):
        """
        ColumnAIConfigWidgetを初期化
        
        Args:
            parent: 親ウィジェット
            column_name: 列名（例: "コピー1", "コピー2"）
            column_index: 列インデックス
            on_config_changed: 設定変更時のコールバック
        """
        self.parent = parent
        self.column_name = column_name
        self.column_index = column_index
        self.on_config_changed = on_config_changed
        
        # 利用可能なAI一覧
        self.available_ais = ["ChatGPT", "Claude", "Gemini", "Genspark", "Google AI Studio"]
        
        # 変数の初期化
        self.selected_ai_var = tk.StringVar(value="ChatGPT")
        self.selected_model_var = tk.StringVar()
        self.settings_vars = {}
        
        # モデル情報
        self.available_models = {}
        self.model_settings = {}
        
        self._create_widgets()
        self._setup_callbacks()
        self._load_initial_models()
        
        logger.debug(f"列設定ウィジェット初期化: {column_name}")
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        self.frame = ttk.LabelFrame(self.parent, text=f"{self.column_name}の設定", padding="10")
        
        # AI選択行
        ai_frame = ttk.Frame(self.frame)
        ai_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(ai_frame, text="AI選択:").pack(side=tk.LEFT, padx=5)
        self.ai_combo = ttk.Combobox(
            ai_frame,
            textvariable=self.selected_ai_var,
            values=self.available_ais,
            state="readonly",
            width=20
        )
        self.ai_combo.pack(side=tk.LEFT, padx=5)
        
        # モデル選択行
        model_frame = ttk.Frame(self.frame)
        model_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(model_frame, text="モデル:").pack(side=tk.LEFT, padx=5)
        self.model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.selected_model_var,
            state="readonly",
            width=30
        )
        self.model_combo.pack(side=tk.LEFT, padx=5)
        
        # モデル更新ボタン
        self.refresh_button = ttk.Button(
            model_frame,
            text="最新モデル取得",
            command=self._refresh_models_async,
            width=15
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        # 設定フレーム（動的生成）
        self.settings_frame = ttk.LabelFrame(self.frame, text="AI設定", padding="5")
        self.settings_frame.pack(fill=tk.X, pady=5)
        
        # ステータス表示
        self.status_label = ttk.Label(self.frame, text="初期化中...", foreground="gray")
        self.status_label.pack(pady=5)
    
    def _setup_callbacks(self):
        """コールバック設定"""
        self.selected_ai_var.trace('w', self._on_ai_changed)
        self.selected_model_var.trace('w', self._on_model_changed)
    
    def _on_ai_changed(self, *args):
        """AI選択変更時の処理"""
        selected_ai = self.selected_ai_var.get()
        logger.info(f"{self.column_name}: AI変更 -> {selected_ai}")
        
        # モデル一覧を更新
        self._update_model_list()
        
        # 設定項目を更新
        self._update_settings_ui()
        
        # コールバック実行
        if self.on_config_changed:
            self.on_config_changed(self.column_index, self.get_config())
    
    def _on_model_changed(self, *args):
        """モデル選択変更時の処理"""
        selected_model = self.selected_model_var.get()
        if selected_model:
            logger.info(f"{self.column_name}: モデル変更 -> {selected_model}")
            
            # コールバック実行
            if self.on_config_changed:
                self.on_config_changed(self.column_index, self.get_config())
    
    def _load_initial_models(self):
        """初期モデル一覧の読み込み"""
        threading.Thread(target=self._load_models_thread, daemon=True).start()
    
    def _load_models_thread(self):
        """モデル読み込みスレッド"""
        try:
            for ai_name in self.available_ais:
                self._load_models_for_ai(ai_name)
            
            # UIを更新
            self.parent.after(0, self._update_model_list)
            self.parent.after(0, lambda: self.status_label.config(text="準備完了"))
            
        except Exception as e:
            logger.error(f"モデル読み込み失敗: {e}")
            self.parent.after(0, lambda: self.status_label.config(text="エラー", foreground="red"))
    
    def _load_models_for_ai(self, ai_name: str):
        """指定AIのモデル一覧を読み込み"""
        try:
            # キャッシュから読み込み
            cache_file = Path(f"cache/models/{ai_name.lower().replace(' ', '')}_models.json")
            
            if cache_file.exists():
                import json
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.available_models[ai_name] = data.get('models', [])
                    self.model_settings[ai_name] = data.get('settings', [])
                    logger.debug(f"{ai_name}のモデル読み込み: {len(self.available_models[ai_name])}件")
            else:
                # デフォルトモデル
                self._set_default_models(ai_name)
                
        except Exception as e:
            logger.error(f"{ai_name}のモデル読み込み失敗: {e}")
            self._set_default_models(ai_name)
    
    def _set_default_models(self, ai_name: str):
        """デフォルトモデルを設定"""
        default_models = {
            "ChatGPT": ["GPT-4", "GPT-4 Turbo", "GPT-3.5 Turbo"],
            "Claude": ["Claude-3.5 Sonnet", "Claude-3 Opus", "Claude-3 Haiku"],
            "Gemini": ["Gemini 1.5 Pro", "Gemini 1.5 Flash", "Gemini Pro"],
            "Genspark": ["Genspark Pro", "Genspark Standard"],
            "Google AI Studio": ["Gemini 1.5 Pro", "Gemini 1.5 Flash"]
        }
        
        self.available_models[ai_name] = default_models.get(ai_name, ["Default Model"])
        self.model_settings[ai_name] = []
    
    def _update_model_list(self):
        """モデル一覧を更新"""
        selected_ai = self.selected_ai_var.get()
        models = self.available_models.get(selected_ai, [])
        
        self.model_combo['values'] = models
        
        # 最初のモデルを選択
        if models and not self.selected_model_var.get():
            self.selected_model_var.set(models[0])
    
    def _update_settings_ui(self):
        """設定UIを更新"""
        # 既存の設定ウィジェットを削除
        for widget in self.settings_frame.winfo_children():
            widget.destroy()
        
        # 新しい設定ウィジェットを作成
        selected_ai = self.selected_ai_var.get()
        settings = self.model_settings.get(selected_ai, [])
        
        if not settings:
            # デフォルト設定を作成
            settings = self._get_default_settings(selected_ai)
        
        for i, setting in enumerate(settings):
            self._create_setting_widget(setting, i)
    
    def _get_default_settings(self, ai_name: str):
        """デフォルト設定を取得"""
        default_settings = {
            "ChatGPT": [
                {"name": "DeepThink", "type": "checkbox", "default": False},
                {"name": "Temperature", "type": "scale", "default": 0.7, "min": 0, "max": 2}
            ],
            "Claude": [
                {"name": "系統的思考", "type": "checkbox", "default": False},
                {"name": "創造性", "type": "scale", "default": 0.5, "min": 0, "max": 1}
            ],
            "Gemini": [
                {"name": "安全性フィルター", "type": "checkbox", "default": True},
                {"name": "応答長", "type": "scale", "default": 0.5, "min": 0, "max": 1}
            ]
        }
        
        return default_settings.get(ai_name, [])
    
    def _create_setting_widget(self, setting: Dict[str, Any], row: int):
        """設定ウィジェットを作成"""
        setting_name = setting.get('name', f'設定{row}')
        setting_type = setting.get('type', 'checkbox')
        
        frame = ttk.Frame(self.settings_frame)
        frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(frame, text=f"{setting_name}:").pack(side=tk.LEFT, padx=5)
        
        if setting_type == 'checkbox':
            var = tk.BooleanVar(value=setting.get('default', False))
            widget = ttk.Checkbutton(frame, variable=var)
            widget.pack(side=tk.LEFT, padx=5)
            self.settings_vars[setting_name] = var
            
        elif setting_type == 'scale':
            var = tk.DoubleVar(value=setting.get('default', 0.5))
            widget = ttk.Scale(
                frame, 
                variable=var,
                from_=setting.get('min', 0),
                to=setting.get('max', 1),
                length=100
            )
            widget.pack(side=tk.LEFT, padx=5)
            
            # 値表示ラベル
            value_label = ttk.Label(frame, text=f"{var.get():.2f}")
            value_label.pack(side=tk.LEFT, padx=5)
            
            # 値変更時の更新
            def update_label(*args, label=value_label, variable=var):
                label.config(text=f"{variable.get():.2f}")
            var.trace('w', update_label)
            
            self.settings_vars[setting_name] = var
    
    def _refresh_models_async(self):
        """非同期でモデル一覧を更新"""
        self.refresh_button.config(state=tk.DISABLED, text="取得中...")
        self.status_label.config(text="最新モデル取得中...", foreground="blue")
        
        threading.Thread(target=self._refresh_models_thread, daemon=True).start()
    
    def _refresh_models_thread(self):
        """モデル更新スレッド（Playwright使用）"""
        try:
            selected_ai = self.selected_ai_var.get()
            logger.info(f"Playwrightで最新モデル取得開始: {selected_ai}")
            
            # Playwrightでモデル取得（実装は後で詳細化）
            self._fetch_latest_models_with_playwright(selected_ai)
            
            # UI更新
            self.parent.after(0, self._update_model_list)
            self.parent.after(0, lambda: self.status_label.config(text="更新完了", foreground="green"))
            self.parent.after(0, lambda: self.refresh_button.config(state=tk.NORMAL, text="最新モデル取得"))
            
        except Exception as e:
            logger.error(f"モデル更新失敗: {e}")
            self.parent.after(0, lambda: self.status_label.config(text="更新失敗", foreground="red"))
            self.parent.after(0, lambda: self.refresh_button.config(state=tk.NORMAL, text="最新モデル取得"))
    
    def _fetch_latest_models_with_playwright(self, ai_name: str):
        """Playwrightで最新モデル情報を取得"""
        # TODO: 実際のPlaywright実装
        # ここでは仮の実装
        import time
        time.sleep(2)  # 取得処理のシミュレーション
        
        # 新しいモデルを追加（例）
        new_models = {
            "ChatGPT": ["GPT-4o", "GPT-4 Turbo", "GPT-4", "GPT-3.5 Turbo"],
            "Claude": ["Claude-3.5 Sonnet New", "Claude-3.5 Sonnet", "Claude-3 Opus"],
            "Gemini": ["Gemini 2.0 Flash", "Gemini 1.5 Pro", "Gemini 1.5 Flash"],
        }
        
        if ai_name in new_models:
            self.available_models[ai_name] = new_models[ai_name]
            logger.info(f"{ai_name}の最新モデル取得完了: {len(new_models[ai_name])}件")
    
    def get_config(self) -> Dict[str, Any]:
        """現在の設定を取得"""
        config = {
            'column_name': self.column_name,
            'column_index': self.column_index,
            'ai': self.selected_ai_var.get(),
            'model': self.selected_model_var.get(),
            'settings': {}
        }
        
        # 設定値を取得
        for name, var in self.settings_vars.items():
            config['settings'][name] = var.get()
        
        return config
    
    def set_config(self, config: Dict[str, Any]):
        """設定を適用"""
        if 'ai' in config:
            self.selected_ai_var.set(config['ai'])
        if 'model' in config:
            self.selected_model_var.set(config['model'])
        
        # 設定値を適用
        settings = config.get('settings', {})
        for name, value in settings.items():
            if name in self.settings_vars:
                self.settings_vars[name].set(value)


class ColumnAIConfigPanel:
    """複数列のAI設定を管理するパネル"""
    
    def __init__(self, parent: tk.Widget, on_config_changed: Optional[Callable] = None):
        """
        ColumnAIConfigPanelを初期化
        
        Args:
            parent: 親ウィジェット
            on_config_changed: 設定変更時のコールバック
        """
        self.parent = parent
        self.on_config_changed = on_config_changed
        self.column_widgets: Dict[int, ColumnAIConfigWidget] = {}
        self.copy_columns = []  # 検出されたコピー列情報
        
        self._create_widgets()
        
        logger.debug("列AI設定パネルを初期化しました")
    
    def _create_widgets(self):
        """パネルのウィジェットを作成"""
        self.frame = ttk.LabelFrame(self.parent, text="列ごとのAI設定", padding="10")
        
        # 説明ラベル
        info_label = ttk.Label(
            self.frame, 
            text="各「コピー」列に対してAIとモデルを個別に設定できます",
            foreground="gray"
        )
        info_label.pack(pady=5)
        
        # スクロール可能なフレーム
        self.canvas = tk.Canvas(self.frame, height=400)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初期メッセージ
        self.empty_label = ttk.Label(
            self.scrollable_frame,
            text="スプレッドシートを読み込んで「コピー」列を検出してください",
            foreground="gray"
        )
        self.empty_label.pack(pady=20)
    
    def update_copy_columns(self, copy_columns: List[Dict[str, Any]]):
        """検出されたコピー列情報で設定を更新"""
        self.copy_columns = copy_columns
        
        # 既存のウィジェットを削除
        for widget in self.column_widgets.values():
            widget.frame.destroy()
        self.column_widgets.clear()
        
        # 空のメッセージを削除
        if self.empty_label.winfo_exists():
            self.empty_label.destroy()
        
        # 各コピー列用のウィジェットを作成
        for i, column_info in enumerate(copy_columns):
            column_name = f"コピー列{i+1} ({column_info.get('column_letter', 'Unknown')})"
            column_index = column_info.get('column_index', i)
            
            widget = ColumnAIConfigWidget(
                self.scrollable_frame,
                column_name,
                column_index,
                self._on_column_config_changed
            )
            widget.frame.pack(fill=tk.X, pady=5)
            
            self.column_widgets[column_index] = widget
        
        logger.info(f"列AI設定更新: {len(copy_columns)}列")
    
    def _on_column_config_changed(self, column_index: int, config: Dict[str, Any]):
        """列設定変更時のコールバック"""
        logger.debug(f"列{column_index}設定変更: {config['ai']} - {config['model']}")
        
        if self.on_config_changed:
            self.on_config_changed(column_index, config)
    
    def get_all_configs(self) -> Dict[int, Dict[str, Any]]:
        """全列の設定を取得"""
        configs = {}
        for column_index, widget in self.column_widgets.items():
            configs[column_index] = widget.get_config()
        return configs
    
    def get_frame(self):
        """フレームを取得"""
        return self.frame