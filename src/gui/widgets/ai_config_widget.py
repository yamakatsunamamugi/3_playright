"""
AI設定ウィジェット

各AIツールの使用可否、モデル選択、詳細設定を管理する
設定内容は ConfigManager を通じて永続化される
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Any, Optional, Callable
from config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AIConfigWidget:
    """単一AI用の設定ウィジェット"""
    
    def __init__(self, parent: tk.Widget, ai_name: str, config: Dict[str, Any] = None):
        """
        AIConfigWidgetを初期化
        
        Args:
            parent: 親ウィジェット
            ai_name: AI名（例: "ChatGPT"）
            config: 初期設定辞書
        """
        self.parent = parent
        self.ai_name = ai_name
        self.config = config or {}
        
        # 変数の初期化
        self.enabled_var = tk.BooleanVar()
        self.model_var = tk.StringVar()
        
        # モックデータでモデル一覧を定義
        self.available_models = self._get_available_models()
        
        self._create_widgets()
        self._load_config()
        
        logger.debug(f"{ai_name}のAI設定ウィジェットを初期化しました")
    
    def _get_available_models(self) -> List[str]:
        """
        利用可能なモデル一覧を取得（モック実装）
        実際の実装では各AIのAPIから最新モデル一覧を取得
        """
        model_lists = {
            "ChatGPT": [
                "gpt-4o",
                "gpt-4o-mini", 
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo"
            ],
            "Claude": [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ],
            "Gemini": [
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-pro"
            ],
            "Genspark": [
                "genspark-latest",
                "genspark-pro",
                "genspark-standard"
            ],
            "Google AI Studio": [
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro", 
                "gemini-1.5-flash",
                "gemini-pro"
            ]
        }
        
        return model_lists.get(self.ai_name, ["default-model"])
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        self.frame = ttk.Frame(self.parent)
        
        # AI名ラベル
        self.name_label = ttk.Label(self.frame, text=f"{self.ai_name}:", width=18, anchor="w")
        
        # 使用チェックボックス
        self.enabled_checkbox = ttk.Checkbutton(
            self.frame,
            text="使用",
            variable=self.enabled_var,
            command=self._on_enabled_changed
        )
        
        # モデル選択
        self.model_label = ttk.Label(self.frame, text="モデル:")
        self.model_combo = ttk.Combobox(
            self.frame,
            textvariable=self.model_var,
            values=self.available_models,
            state="readonly",
            width=25
        )
        
        # 詳細設定ボタン
        self.settings_button = ttk.Button(
            self.frame,
            text="詳細設定",
            command=self._open_advanced_settings,
            width=10
        )
        
        # ステータス表示
        self.status_label = ttk.Label(self.frame, text="", foreground="gray", width=15)
        
        self._layout_widgets()
        self._setup_callbacks()
    
    def _layout_widgets(self):
        """ウィジェットのレイアウト"""
        self.name_label.pack(side=tk.LEFT, padx=5)
        self.enabled_checkbox.pack(side=tk.LEFT, padx=5)
        self.model_label.pack(side=tk.LEFT, padx=5)
        self.model_combo.pack(side=tk.LEFT, padx=5)
        self.settings_button.pack(side=tk.LEFT, padx=5)
        self.status_label.pack(side=tk.LEFT, padx=5)
    
    def _setup_callbacks(self):
        """コールバック設定"""
        self.model_var.trace('w', self._on_model_changed)
    
    def _on_enabled_changed(self):
        """使用チェックボックス変更時の処理"""
        enabled = self.enabled_var.get()
        
        # モデル選択の有効/無効切り替え
        if enabled:
            self.model_combo.config(state="readonly")
            self.settings_button.config(state=tk.NORMAL)
            self.status_label.config(text="有効", foreground="green")
            
            # デフォルトモデルを設定
            if not self.model_var.get() and self.available_models:
                self.model_var.set(self.available_models[0])
        else:
            self.model_combo.config(state=tk.DISABLED)
            self.settings_button.config(state=tk.DISABLED)
            self.status_label.config(text="無効", foreground="gray")
        
        logger.debug(f"{self.ai_name}の使用設定を{'有効' if enabled else '無効'}に変更しました")
    
    def _on_model_changed(self, *args):
        """モデル選択変更時の処理"""
        model = self.model_var.get()
        if model:
            logger.debug(f"{self.ai_name}のモデルを{model}に変更しました")
    
    def _open_advanced_settings(self):
        """詳細設定ダイアログを開く"""
        dialog = AdvancedSettingsDialog(self.frame, self.ai_name, self.config.get('settings', {}))
        if dialog.result:
            self.config['settings'] = dialog.result
            logger.info(f"{self.ai_name}の詳細設定を更新しました")
    
    def _load_config(self):
        """設定を読み込み"""
        self.enabled_var.set(self.config.get('enabled', False))
        
        model = self.config.get('model', '')
        if model in self.available_models:
            self.model_var.set(model)
        elif self.available_models:
            self.model_var.set(self.available_models[0])
        
        # UI状態を更新
        self._on_enabled_changed()
    
    def get_config(self) -> Dict[str, Any]:
        """現在の設定を取得"""
        return {
            'enabled': self.enabled_var.get(),
            'model': self.model_var.get(),
            'settings': self.config.get('settings', {})
        }
    
    def set_config(self, config: Dict[str, Any]):
        """設定を外部から設定"""
        self.config = config
        self._load_config()


class AdvancedSettingsDialog:
    """詳細設定ダイアログ"""
    
    def __init__(self, parent: tk.Widget, ai_name: str, current_settings: Dict[str, Any]):
        """
        詳細設定ダイアログを初期化
        
        Args:
            parent: 親ウィジェット
            ai_name: AI名
            current_settings: 現在の設定
        """
        self.ai_name = ai_name
        self.current_settings = current_settings.copy()
        self.result = None
        
        # ダイアログウィンドウ作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"{ai_name} 詳細設定")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._load_settings()
        
        # ウィンドウを中央に配置
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self.dialog.wait_window()
    
    def _create_widgets(self):
        """ダイアログのウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text=f"{self.ai_name} 詳細設定", font=("", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 設定フレーム
        settings_frame = ttk.LabelFrame(main_frame, text="設定項目", padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # AI固有の設定項目を作成
        self.setting_vars = {}
        self._create_ai_specific_settings(settings_frame)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="OK", command=self._ok_clicked).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="キャンセル", command=self._cancel_clicked).pack(side=tk.RIGHT)
    
    def _create_ai_specific_settings(self, parent: tk.Widget):
        """AI固有の設定項目を作成"""
        row = 0
        
        if self.ai_name == "ChatGPT":
            # Temperature設定
            ttk.Label(parent, text="Temperature:").grid(row=row, column=0, sticky=tk.W, pady=2)
            temp_var = tk.DoubleVar()
            temp_scale = ttk.Scale(parent, from_=0.0, to=2.0, variable=temp_var, orient=tk.HORIZONTAL)
            temp_scale.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
            temp_label = ttk.Label(parent, text="0.7")
            temp_label.grid(row=row, column=2, sticky=tk.W, pady=2)
            self.setting_vars['temperature'] = temp_var
            
            # スケール変更時のラベル更新
            def update_temp_label(*args):
                temp_label.config(text=f"{temp_var.get():.1f}")
            temp_var.trace('w', update_temp_label)
            row += 1
            
            # Max Tokens設定
            ttk.Label(parent, text="Max Tokens:").grid(row=row, column=0, sticky=tk.W, pady=2)
            tokens_var = tk.IntVar()
            tokens_entry = ttk.Entry(parent, textvariable=tokens_var, width=10)
            tokens_entry.grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)
            self.setting_vars['max_tokens'] = tokens_var
            
        elif self.ai_name == "Claude":
            # Max Tokens設定
            ttk.Label(parent, text="Max Tokens:").grid(row=row, column=0, sticky=tk.W, pady=2)
            tokens_var = tk.IntVar()
            tokens_entry = ttk.Entry(parent, textvariable=tokens_var, width=10)
            tokens_entry.grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)
            self.setting_vars['max_tokens'] = tokens_var
            
        elif self.ai_name == "Gemini":
            # Temperature設定
            ttk.Label(parent, text="Temperature:").grid(row=row, column=0, sticky=tk.W, pady=2)
            temp_var = tk.DoubleVar()
            temp_scale = ttk.Scale(parent, from_=0.0, to=1.0, variable=temp_var, orient=tk.HORIZONTAL)
            temp_scale.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
            temp_label = ttk.Label(parent, text="0.9")
            temp_label.grid(row=row, column=2, sticky=tk.W, pady=2)
            self.setting_vars['temperature'] = temp_var
            
            def update_temp_label(*args):
                temp_label.config(text=f"{temp_var.get():.1f}")
            temp_var.trace('w', update_temp_label)
            row += 1
            
            # Max Output Tokens設定
            ttk.Label(parent, text="Max Output Tokens:").grid(row=row, column=0, sticky=tk.W, pady=2)
            tokens_var = tk.IntVar()
            tokens_entry = ttk.Entry(parent, textvariable=tokens_var, width=10)
            tokens_entry.grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)
            self.setting_vars['max_output_tokens'] = tokens_var
        
        # 列の重み設定
        parent.columnconfigure(1, weight=1)
    
    def _load_settings(self):
        """現在の設定値をUIに読み込み"""
        for key, var in self.setting_vars.items():
            if key in self.current_settings:
                var.set(self.current_settings[key])
            else:
                # デフォルト値を設定
                default_values = {
                    'temperature': 0.7,
                    'max_tokens': 2000,
                    'max_output_tokens': 2048
                }
                if key in default_values:
                    var.set(default_values[key])
    
    def _ok_clicked(self):
        """OKボタンクリック時の処理"""
        # 設定値を収集
        result = {}
        for key, var in self.setting_vars.items():
            result[key] = var.get()
        
        self.result = result
        self.dialog.destroy()
    
    def _cancel_clicked(self):
        """キャンセルボタンクリック時の処理"""
        self.result = None
        self.dialog.destroy()


class AIConfigPanel:
    """複数AI設定を管理するパネル"""
    
    def __init__(self, parent: tk.Widget, on_config_changed: Optional[Callable] = None):
        """
        AIConfigPanelを初期化
        
        Args:
            parent: 親ウィジェット
            on_config_changed: 設定変更時のコールバック
        """
        self.parent = parent
        self.on_config_changed = on_config_changed
        self.ai_widgets: Dict[str, AIConfigWidget] = {}
        
        self._create_widgets()
        self._create_ai_widgets()
        
        logger.debug("AI設定パネルを初期化しました")
    
    def _create_widgets(self):
        """パネルのウィジェットを作成"""
        self.frame = ttk.LabelFrame(self.parent, text="AI設定", padding="10")
        
        # スクロール可能なフレーム
        self.canvas = tk.Canvas(self.frame, height=200)
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
    
    def _create_ai_widgets(self):
        """各AI用のウィジェットを作成"""
        for i, ai_name in enumerate(settings.SUPPORTED_AI_TOOLS):
            widget = AIConfigWidget(self.scrollable_frame, ai_name)
            widget.frame.pack(fill=tk.X, pady=2)
            self.ai_widgets[ai_name] = widget
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """全AI設定を取得"""
        configs = {}
        for ai_name, widget in self.ai_widgets.items():
            configs[ai_name] = widget.get_config()
        return configs
    
    def set_all_configs(self, configs: Dict[str, Dict[str, Any]]):
        """全AI設定を外部から設定"""
        for ai_name, config in configs.items():
            if ai_name in self.ai_widgets:
                self.ai_widgets[ai_name].set_config(config)
    
    def grid(self, **kwargs):
        """パネルをgridで配置"""
        self.frame.grid(**kwargs)
    
    def pack(self, **kwargs):
        """パネルをpackで配置"""
        self.frame.pack(**kwargs)