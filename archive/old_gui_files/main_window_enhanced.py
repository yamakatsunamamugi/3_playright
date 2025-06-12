"""
拡張メインウィンドウ

新しいウィジェットを統合した改良版のメインウィンドウ
設定の永続化、進捗表示、ログ機能などを含む
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from src.utils.logger import get_logger
from config.settings import settings
from src.config_manager import get_config_manager
from src.gui.widgets import (
    SpreadsheetWidget,
    ProgressWidget,
    LogWidget
)
from src.gui.widgets.ai_config_widget import AIConfigPanel


logger = get_logger(__name__)


class MainWindowEnhanced:
    """拡張版メインウィンドウクラス"""
    
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
        """ウィジェットを作成"""
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
        """ウィジェットのレイアウト"""
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        row = 0
        # スプレッドシート設定
        self.spreadsheet_widget.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        row += 1
        # AI設定パネル
        self.ai_config_panel.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
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
        """ステータスバーを更新"""
        self.status_label.config(text=status)
    
    def _on_sheet_selected(self, url: str, sheet_name: str):
        """スプレッドシート選択時のコールバック"""
        self.add_log(f"シートが選択されました: {sheet_name}")
        self.update_status(f"シート選択済み: {sheet_name}")
        
        # 設定を保存
        self.config_manager.set_spreadsheet_config(url, sheet_name)
        self.config_manager.auto_save()
        
        logger.info(f"スプレッドシートが選択されました: {url} - {sheet_name}")
    
    def _on_ai_config_changed(self):
        """AI設定変更時のコールバック"""
        configs = self.ai_config_panel.get_all_configs()
        enabled_ais = [name for name, config in configs.items() if config.get('enabled', False)]
        
        if enabled_ais:
            self.add_log(f"AI設定が更新されました: {', '.join(enabled_ais)}")
        else:
            self.add_log("すべてのAIが無効に設定されました", "WARNING")
        
        # 設定を保存
        for ai_name, config in configs.items():
            self.config_manager.set_ai_config(ai_name, config)
        self.config_manager.auto_save()
    
    def _load_saved_settings(self):
        """保存された設定を読み込み"""
        # スプレッドシート設定
        spreadsheet_config = self.config_manager.get_spreadsheet_config()
        if spreadsheet_config.get('last_url'):
            self.spreadsheet_widget.set_values(
                spreadsheet_config['last_url'],
                spreadsheet_config.get('last_sheet', '')
            )
        
        # AI設定
        ai_configs = {}
        for ai_name in settings.SUPPORTED_AI_TOOLS:
            ai_configs[ai_name] = self.config_manager.get_ai_config(ai_name)
        
        self.ai_config_panel.set_all_configs(ai_configs)
        
        self.add_log("保存された設定を読み込みました")
    
    def _on_window_close(self):
        """ウィンドウクローズ時の処理"""
        if self.processing:
            if not messagebox.askyesno("確認", "処理中です。アプリケーションを終了しますか？"):
                return
        
        # 現在のウィンドウサイズを保存
        geometry = self.root.geometry()
        size_part = geometry.split('+')[0]  # "800x600" の部分を取得
        width, height = map(int, size_part.split('x'))
        
        self.config_manager.set('ui.window_width', width)
        self.config_manager.set('ui.window_height', height)
        self.config_manager.save_config()
        
        logger.info("アプリケーションを終了します")
        self.root.destroy()
        
    def _start_processing(self):
        """処理を開始"""
        # バリデーション
        url, sheet_name = self.spreadsheet_widget.get_values()
        if not url or not sheet_name:
            messagebox.showwarning("警告", "スプレッドシートとシートを選択してください")
            return
        
        # 有効なAI設定があるかチェック
        ai_configs = self.ai_config_panel.get_all_configs()
        enabled_ais = [name for name, config in ai_configs.items() if config.get('enabled', False)]
        
        if not enabled_ais:
            messagebox.showwarning("警告", "少なくとも1つのAIを有効にしてください")
            return
        
        # 処理開始
        self.processing = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.update_status("処理中...")
        
        self.add_log("処理を開始します")
        self.add_log(f"対象: {sheet_name} ({url})")
        self.add_log(f"使用AI: {', '.join(enabled_ais)}")
        
        # 進捗表示開始（モック値で開始、実際の処理で更新）
        self.progress_widget.start_progress(10, "データ処理中")
        
        # 非同期で処理実行
        thread = threading.Thread(target=self._process_data_async, args=(url, sheet_name, ai_configs))
        thread.daemon = True
        thread.start()
        
    def _stop_processing(self):
        """処理を停止"""
        self.processing = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.update_status("停止しました")
        self.add_log("処理を停止しました", "WARNING")
        self.progress_widget.reset()
        
    def _process_data_async(self, url: str, sheet_name: str, ai_configs: dict):
        """非同期データ処理（モック実装）"""
        try:
            self.add_log("データ処理を開始しました")
            
            # モックデータでの処理シミュレーション
            import time
            total_items = 10
            
            for i in range(total_items):
                if not self.processing:
                    break
                
                # 進捗更新
                current_item = f"データ行 {i+1}"
                has_error = (i == 3)  # 4番目でエラーをシミュレート
                
                self.progress_widget.increment_progress(current_item, has_error)
                
                if has_error:
                    self.add_log(f"エラー: {current_item}の処理に失敗しました", "ERROR")
                else:
                    self.add_log(f"完了: {current_item}")
                
                time.sleep(1)  # 処理時間をシミュレート
            
            if self.processing:
                self.progress_widget.complete_progress("すべての処理が完了しました")
                self.add_log("データ処理が正常に完了しました")
                self.update_status("処理完了")
            
        except Exception as e:
            logger.error(f"処理中にエラーが発生しました: {e}")
            self.add_log(f"エラー: {e}", "ERROR")
            self.update_status("エラーが発生しました")
            self.progress_widget.set_error_state(str(e))
            
        finally:
            self.processing = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
    def run(self):
        """アプリケーションを起動"""
        logger.info("アプリケーションを起動します")
        self.add_log("アプリケーションが起動しました")
        self.root.mainloop()


# アプリケーションの起動用関数
def main():
    """アプリケーションのメイン関数"""
    app = MainWindowEnhanced()
    app.run()


if __name__ == "__main__":
    main()