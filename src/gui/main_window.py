import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from src.utils.logger import get_logger
from config.settings import settings
from src.config_manager import get_config_manager
from src.gui.widgets import (
    SpreadsheetWidget,
    AIConfigPanel,
    ProgressWidget,
    LogWidget
)
from src.gui.widgets.column_ai_config_widget import ColumnAIConfigPanel


logger = get_logger(__name__)


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(settings.WINDOW_TITLE)
        
        # 設定マネージャーを取得
        self.config_manager = get_config_manager()
        
        # UI設定を読み込み
        ui_config = self.config_manager.get_ui_config()
        window_width = ui_config.get('window_width', settings.WINDOW_WIDTH)
        window_height = ui_config.get('window_height', settings.WINDOW_HEIGHT)
        self.root.geometry(f"{window_width}x{window_height}")
        
        # 処理状態管理
        self.processing = False
        
        # ウィジェット作成
        self._create_widgets()
        self._layout_widgets()
        self._load_saved_settings()
        
        # ウィンドウクローズ時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        logger.info("メインウィンドウを初期化しました")
        
    def _create_widgets(self):
        self.main_frame = ttk.Frame(self.root, padding="10")
        
        # スプレッドシート設定ウィジェット
        self.spreadsheet_widget = SpreadsheetWidget(
            self.main_frame,
            on_sheet_selected=self._on_sheet_selected
        )
        
        # AI設定パネル
        self.ai_config_panel = AIConfigPanel(
            self.main_frame,
            on_config_changed=self._on_ai_config_changed
        )
        
        # 列ごとのAI設定パネル（新機能）
        self.column_ai_config_panel = ColumnAIConfigPanel(
            self.main_frame,
            on_config_changed=self._on_column_ai_config_changed
        )
        
        # 進捗表示ウィジェット
        self.progress_widget = ProgressWidget(self.main_frame)
        
        # ログ表示ウィジェット
        self.log_widget = LogWidget(self.main_frame, max_lines=1000)
        
        # 制御ボタン
        self.button_frame = ttk.Frame(self.main_frame)
        self.start_button = ttk.Button(
            self.button_frame, 
            text="処理開始", 
            command=self._start_processing,
            width=12
        )
        self.stop_button = ttk.Button(
            self.button_frame, 
            text="停止", 
            command=self._stop_processing, 
            state=tk.DISABLED,
            width=12
        )
        
        # ステータスバー
        self.status_label = ttk.Label(self.main_frame, text="待機中", relief=tk.SUNKEN)
        
    def _layout_widgets(self):
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        row = 0
        # スプレッドシート設定
        self.spreadsheet_widget.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        row += 1
        # AI設定パネル
        self.ai_config_panel.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        row += 1
        # 列ごとのAI設定パネル（新機能）
        self.column_ai_config_panel.get_frame().grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        row += 1
        # 進捗表示
        self.progress_widget.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        row += 1
        # ログ表示
        self.log_widget.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        row += 1
        # 制御ボタン
        self.button_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        row += 1
        # ステータスバー
        self.status_label.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        # グリッドの重み設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(row-2, weight=1)  # ログ表示エリアを伸縮可能に
        
    def add_log(self, message: str, level: str = "INFO"):
        """ログメッセージを追加"""
        self.log_widget.add_log(message, level)
        
    def update_status(self, status: str):
        self.status_label.config(text=status)
    
    def _on_sheet_selected(self, url: str, sheet_name: str):
        """シート選択時のコールバック処理"""
        self.add_log(f"シートが選択されました: {sheet_name}")
        self.update_status(f"シート選択: {sheet_name}")
        
        # スプレッドシートを分析してコピー列を検出
        self._analyze_spreadsheet_structure(url, sheet_name)
    
    def _on_ai_config_changed(self):
        """AI設定変更時のコールバック処理"""
        configs = self.ai_config_panel.get_all_configs()
        enabled_ais = [name for name, config in configs.items() if config.get('enabled', False)]
        self.add_log(f"AI設定が変更されました: {len(enabled_ais)}個のAIが有効")
    
    def _on_column_ai_config_changed(self, column_index: int, config: dict):
        """列ごとのAI設定変更時のコールバック処理"""
        ai_name = config.get('ai', 'Unknown')
        model_name = config.get('model', 'Unknown')
        column_name = config.get('column_name', f'列{column_index}')
        self.add_log(f"{column_name}: {ai_name} - {model_name}に設定されました")
    
    def _analyze_spreadsheet_structure(self, url: str, sheet_name: str):
        """スプレッドシート構造を分析してコピー列を検出"""
        def analyze_thread():
            try:
                self.add_log("📊 スプレッドシート構造を分析中...")
                
                # TODO: 実際のスプレッドシート分析ロジックを実装
                # ここでは仮のデータを使用
                copy_columns = [
                    {'column_letter': 'F', 'column_index': 5, 'column_name': 'コピー1'},
                    {'column_letter': 'I', 'column_index': 8, 'column_name': 'コピー2'},
                ]
                
                # UIスレッドで列AI設定を更新
                self.root.after(0, lambda: self._update_column_ai_config(copy_columns))
                self.root.after(0, lambda: self.add_log(f"✅ {len(copy_columns)}個のコピー列を検出しました"))
                
            except Exception as e:
                logger.error(f"スプレッドシート分析エラー: {e}")
                self.root.after(0, lambda: self.add_log(f"❌ スプレッドシート分析に失敗: {e}"))
        
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def _update_column_ai_config(self, copy_columns: list):
        """列AI設定パネルを更新"""
        self.column_ai_config_panel.update_copy_columns(copy_columns)
    
    def _load_saved_settings(self):
        """保存された設定を読み込み"""
        try:
            # 設定マネージャーから設定を読み込み
            pass
        except Exception as e:
            logger.error(f"設定の読み込みに失敗: {e}")
    
    def _on_window_close(self):
        """ウィンドウクローズ時の処理"""
        if self.processing:
            result = messagebox.askyesno("確認", "処理中です。終了しますか？")
            if not result:
                return
        
        try:
            # 設定を保存
            self.config_manager.save_config()
            logger.info("設定を保存しました")
        except Exception as e:
            logger.error(f"設定の保存に失敗: {e}")
        
        self.root.destroy()
        
    def _start_processing(self):
        # シート選択の確認
        url, sheet_name = self.spreadsheet_widget.get_values()
        if not url or not sheet_name:
            messagebox.showwarning("警告", "スプレッドシートとシートを選択してください")
            return
        
        # AI設定の確認
        ai_configs = self.ai_config_panel.get_all_configs()
        enabled_ais = [name for name, config in ai_configs.items() if config.get('enabled', False)]
        if not enabled_ais:
            messagebox.showwarning("警告", "少なくとも1つのAIを有効にしてください")
            return
            
        self.processing = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.update_status("処理中...")
        self.add_log("処理を開始します")
        
        thread = threading.Thread(target=self._process_data)
        thread.daemon = True
        thread.start()
        
    def _stop_processing(self):
        self.processing = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.update_status("停止しました")
        self.add_log("処理を停止しました", "WARNING")
        
    def _process_data(self):
        try:
            self.add_log("データ処理を開始しました")
            self.update_status("処理完了")
            
        except Exception as e:
            logger.error(f"処理中にエラーが発生しました: {e}")
            self.add_log(f"エラー: {e}", "ERROR")
            self.update_status("エラーが発生しました")
            
        finally:
            self.processing = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
    def run(self):
        logger.info("アプリケーションを起動します")
        self.root.mainloop()