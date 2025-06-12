"""
拡張版メインウィンドウ
コピー列ごとのAI選択機能を含む
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import asyncio
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

from config.settings import settings
from src.utils.logger import get_logger
from src.gui.widgets import (
    SpreadsheetWidget,
    AIConfigPanel,
    ProgressWidget,
    LogWidget
)
from src.main_orchestrator import MainOrchestrator
from src.interfaces.gui_interface import IGUIController, ProcessStatus

logger = get_logger(__name__)


class CopyColumnAISelector(ttk.Frame):
    """コピー列ごとのAI選択ウィジェット"""
    
    def __init__(self, parent, copy_columns: List[int], ai_tools: List[str]):
        super().__init__(parent)
        self.copy_columns = copy_columns
        self.ai_tools = ai_tools
        self.column_ai_mapping = {}
        
        self._create_widgets()
        
    def _create_widgets(self):
        """ウィジェットを作成"""
        # ヘッダー
        ttk.Label(self, text="各コピー列で使用するAIを選択:", font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(0, 10), sticky=tk.W
        )
        
        # 列ごとの選択UI
        for i, col_idx in enumerate(self.copy_columns):
            row = i + 1
            
            # 列番号
            ttk.Label(self, text=f"列 {col_idx + 1}:").grid(
                row=row, column=0, padx=(0, 10), pady=2, sticky=tk.W
            )
            
            # AI選択コンボボックス
            ai_var = tk.StringVar(value=self.ai_tools[0] if self.ai_tools else "")
            combo = ttk.Combobox(self, textvariable=ai_var, values=self.ai_tools,
                               state="readonly", width=20)
            combo.grid(row=row, column=1, pady=2)
            
            self.column_ai_mapping[col_idx] = ai_var
            
        # デフォルト設定ボタン
        ttk.Button(self, text="全て同じAIに設定", 
                  command=self._set_all_same).grid(
            row=len(self.copy_columns) + 1, column=0, columnspan=2, pady=10
        )
        
    def _set_all_same(self):
        """全列を同じAIに設定"""
        if not self.ai_tools:
            return
            
        # ダイアログで選択
        dialog = tk.Toplevel(self)
        dialog.title("AIを選択")
        dialog.geometry("300x150")
        dialog.transient(self.master)
        dialog.grab_set()
        
        ttk.Label(dialog, text="全列で使用するAI:").pack(pady=10)
        
        selected_ai = tk.StringVar(value=self.ai_tools[0])
        combo = ttk.Combobox(dialog, textvariable=selected_ai, 
                           values=self.ai_tools, state="readonly")
        combo.pack(pady=10)
        
        def apply():
            ai = selected_ai.get()
            for var in self.column_ai_mapping.values():
                var.set(ai)
            dialog.destroy()
            
        ttk.Button(dialog, text="適用", command=apply).pack(pady=10)
        
    def get_mapping(self) -> Dict[int, str]:
        """列とAIのマッピングを取得"""
        return {col: var.get() for col, var in self.column_ai_mapping.items()}


class EnhancedMainWindow(IGUIController):
    """拡張版メインウィンドウ"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{settings.WINDOW_TITLE} - 拡張版")
        self.root.geometry(f"{settings.WINDOW_WIDTH + 200}x{settings.WINDOW_HEIGHT + 100}")
        
        # オーケストレーター
        self.orchestrator = MainOrchestrator(self)
        
        # 処理状態
        self.processing = False
        self.current_status = ProcessStatus.IDLE
        
        # コピー列情報
        self.detected_copy_columns = []
        self.column_ai_selector = None
        
        # ウィジェット作成
        self._create_widgets()
        self._layout_widgets()
        
        # ウィンドウクローズ時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        logger.info("拡張版メインウィンドウを初期化しました")
        
    def _create_widgets(self):
        """ウィジェットを作成"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        
        # タブコントロール
        self.notebook = ttk.Notebook(self.main_frame)
        
        # 基本設定タブ
        self.basic_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_tab, text="基本設定")
        
        # スプレッドシート設定
        self.spreadsheet_widget = SpreadsheetWidget(
            self.basic_tab,
            on_sheet_selected=self._on_sheet_selected
        )
        
        # AI設定パネル
        self.ai_config_panel = AIConfigPanel(
            self.basic_tab,
            on_config_changed=self._on_ai_config_changed
        )
        
        # 詳細設定タブ
        self.advanced_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.advanced_tab, text="詳細設定")
        
        # Chrome設定フレーム
        self.chrome_frame = ttk.LabelFrame(self.advanced_tab, text="Chrome設定", padding="10")
        
        # プロファイル選択
        profile_frame = ttk.Frame(self.chrome_frame)
        ttk.Label(profile_frame, text="Chromeプロファイル:").pack(side=tk.LEFT, padx=(0, 10))
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var,
                                         state="readonly", width=30)
        self.profile_combo.pack(side=tk.LEFT)
        profile_frame.pack(fill=tk.X, pady=(0, 10))
        
        # コピー列設定フレーム
        self.column_frame = ttk.LabelFrame(self.advanced_tab, text="コピー列とAIの設定", padding="10")
        self.column_info_label = ttk.Label(self.column_frame, text="シートを選択すると、コピー列が表示されます")
        self.column_info_label.pack()
        
        # 処理タブ
        self.process_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.process_tab, text="処理実行")
        
        # 進捗表示
        self.progress_widget = ProgressWidget(self.process_tab)
        
        # ログ表示
        self.log_widget = LogWidget(self.process_tab, max_lines=1000)
        
        # 制御ボタン
        self.button_frame = ttk.Frame(self.process_tab)
        
        self.detect_button = ttk.Button(
            self.button_frame,
            text="列を検出",
            command=self._detect_columns,
            width=12
        )
        
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
        
        # Chromeプロファイルを更新
        self._refresh_chrome_profiles()
        
    def _layout_widgets(self):
        """ウィジェットのレイアウト"""
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 基本設定タブのレイアウト
        self.spreadsheet_widget.pack(fill=tk.X, pady=(0, 10))
        self.ai_config_panel.pack(fill=tk.X, pady=(0, 10))
        
        # 詳細設定タブのレイアウト
        self.chrome_frame.pack(fill=tk.X, pady=(0, 10))
        self.column_frame.pack(fill=tk.BOTH, expand=True)
        
        # 処理タブのレイアウト
        self.progress_widget.pack(fill=tk.X, pady=(0, 10))
        self.log_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.button_frame.pack(fill=tk.X)
        self.detect_button.pack(side=tk.LEFT, padx=5)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # ノートブックとステータスバー
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.status_label.pack(fill=tk.X)
        
        # グリッドの重み設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        
    def _refresh_chrome_profiles(self):
        """Chromeプロファイルリストを更新"""
        try:
            from src.ai_tools.browser_manager import BrowserManager
            temp_manager = BrowserManager()
            profiles = temp_manager.get_available_profiles_info()
            
            profile_names = []
            for profile in profiles:
                name = profile.get('name', profile.get('dir', 'Unknown'))
                dir_name = profile.get('dir', '')
                profile_names.append(dir_name)
                
            self.profile_combo['values'] = profile_names
            if profile_names:
                self.profile_combo.set(profile_names[0])
                
        except Exception as e:
            logger.error(f"プロファイル取得エラー: {e}")
            
    def _detect_columns(self):
        """コピー列を検出"""
        url, sheet_name = self.spreadsheet_widget.get_values()
        if not url or not sheet_name:
            messagebox.showwarning("警告", "スプレッドシートとシートを選択してください")
            return
            
        # 非同期で列検出を実行
        def detect_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # シートデータを取得して列を検出
                from src.sheets.client import GoogleSheetsClient
                client = GoogleSheetsClient()
                
                if not client.authenticate():
                    self.add_log("Google Sheets認証に失敗しました", "ERROR")
                    return
                    
                sheet_id = self.orchestrator._extract_sheet_id(url)
                sheet_data = client.get_sheet_data(sheet_id, sheet_name)
                
                if not sheet_data:
                    self.add_log("シートデータの取得に失敗しました", "ERROR")
                    return
                    
                # 作業指示行を検出
                work_row_idx = self.orchestrator._find_work_instruction_row(sheet_data)
                if work_row_idx == -1:
                    self.add_log("作業指示行が見つかりません", "ERROR")
                    return
                    
                # コピー列を検出
                header_row = sheet_data[work_row_idx]
                copy_columns = self.orchestrator._find_copy_columns(header_row)
                
                if not copy_columns:
                    self.add_log("コピー列が見つかりません", "WARNING")
                    return
                    
                self.detected_copy_columns = copy_columns
                self.add_log(f"{len(copy_columns)}個のコピー列を検出しました: 列 {[c+1 for c in copy_columns]}")
                
                # UIスレッドでセレクターを更新
                self.root.after(0, self._update_column_selector)
                
            except Exception as e:
                logger.error(f"列検出エラー: {e}")
                self.add_log(f"列検出エラー: {e}", "ERROR")
            finally:
                loop.close()
                
        thread = threading.Thread(target=detect_async, daemon=True)
        thread.start()
        
    def _update_column_selector(self):
        """コピー列セレクターを更新"""
        # 既存のセレクターを削除
        if self.column_ai_selector:
            self.column_ai_selector.destroy()
            
        # 有効なAIツールを取得
        ai_configs = self.ai_config_panel.get_all_configs()
        enabled_ais = [name for name, config in ai_configs.items() 
                      if config.get('enabled', False)]
        
        if not enabled_ais:
            self.column_info_label.config(text="有効なAIツールがありません")
            return
            
        if not self.detected_copy_columns:
            self.column_info_label.config(text="コピー列が検出されていません")
            return
            
        self.column_info_label.pack_forget()
        
        # 新しいセレクターを作成
        self.column_ai_selector = CopyColumnAISelector(
            self.column_frame,
            self.detected_copy_columns,
            enabled_ais
        )
        self.column_ai_selector.pack(fill=tk.BOTH, expand=True)
        
    def _start_processing(self):
        """処理を開始"""
        # 入力検証
        url, sheet_name = self.spreadsheet_widget.get_values()
        if not url or not sheet_name:
            messagebox.showwarning("警告", "スプレッドシートとシートを選択してください")
            return
            
        ai_configs = self.ai_config_panel.get_all_configs()
        enabled_ais = [name for name, config in ai_configs.items() 
                      if config.get('enabled', False)]
        
        if not enabled_ais:
            messagebox.showwarning("警告", "少なくとも1つのAIを有効にしてください")
            return
            
        if not self.detected_copy_columns:
            messagebox.showwarning("警告", "先に「列を検出」を実行してください")
            return
            
        # コピー列とAIのマッピングを取得
        if self.column_ai_selector:
            column_mapping = self.column_ai_selector.get_mapping()
            self.orchestrator.set_column_ai_mapping(column_mapping)
            
        self.processing = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.detect_button.config(state=tk.DISABLED)
        self.update_status(ProcessStatus.PROCESSING)
        
        # 設定を準備
        config = {
            'spreadsheet_url': url,
            'sheet_name': sheet_name,
            'ai_tools': ai_configs,
            'chrome_profile': self.profile_var.get()
        }
        
        # 非同期で処理を実行
        def process_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 初期化
                if not loop.run_until_complete(self.orchestrator.initialize(config['chrome_profile'])):
                    self.add_log("初期化に失敗しました", "ERROR")
                    return
                    
                # 処理実行
                loop.run_until_complete(self.orchestrator.process_spreadsheet(config))
                
            except Exception as e:
                logger.error(f"処理エラー: {e}")
                self.add_log(f"処理エラー: {e}", "ERROR")
                
            finally:
                # クリーンアップ
                loop.run_until_complete(self.orchestrator.cleanup())
                loop.close()
                
                # UIを更新
                self.root.after(0, self._processing_finished)
                
        thread = threading.Thread(target=process_async, daemon=True)
        thread.start()
        
    def _stop_processing(self):
        """処理を停止"""
        self.orchestrator.stop_processing()
        self.stop_button.config(state=tk.DISABLED)
        self.update_status(ProcessStatus.PAUSED)
        self.add_log("停止を要求しました...")
        
    def _processing_finished(self):
        """処理終了時の処理"""
        self.processing = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.detect_button.config(state=tk.NORMAL)
        
        if self.current_status == ProcessStatus.PROCESSING:
            self.update_status(ProcessStatus.COMPLETED)
            
    def _on_sheet_selected(self, url: str, sheet_name: str):
        """シート選択時の処理"""
        self.add_log(f"シートが選択されました: {sheet_name}")
        self.update_status(ProcessStatus.IDLE, f"シート選択: {sheet_name}")
        
        # コピー列情報をリセット
        self.detected_copy_columns = []
        if self.column_ai_selector:
            self.column_ai_selector.destroy()
            self.column_ai_selector = None
        self.column_info_label.config(text="「列を検出」ボタンをクリックしてコピー列を検出してください")
        self.column_info_label.pack()
        
    def _on_ai_config_changed(self):
        """AI設定変更時の処理"""
        configs = self.ai_config_panel.get_all_configs()
        enabled_ais = [name for name, config in configs.items() 
                      if config.get('enabled', False)]
        self.add_log(f"AI設定が変更されました: {len(enabled_ais)}個のAIが有効")
        
        # コピー列セレクターを更新
        if self.detected_copy_columns:
            self._update_column_selector()
            
    def _on_window_close(self):
        """ウィンドウクローズ時の処理"""
        if self.processing:
            result = messagebox.askyesno("確認", "処理中です。終了しますか？")
            if not result:
                return
                
        # クリーンアップ
        if hasattr(self, 'orchestrator'):
            def cleanup_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.orchestrator.cleanup())
                except:
                    pass
                finally:
                    loop.close()
                    
            thread = threading.Thread(target=cleanup_async)
            thread.start()
            thread.join(timeout=5)
            
        self.root.destroy()
        
    # IGUIControllerインターフェースの実装
    def update_status(self, status: ProcessStatus, message: str = ""):
        """ステータスを更新"""
        self.current_status = status
        status_text = {
            ProcessStatus.IDLE: "待機中",
            ProcessStatus.PROCESSING: "処理中",
            ProcessStatus.PAUSED: "一時停止",
            ProcessStatus.COMPLETED: "完了",
            ProcessStatus.ERROR: "エラー"
        }.get(status, "不明")
        
        if message:
            status_text = f"{status_text} - {message}"
            
        self.status_label.config(text=status_text)
        
    def update_progress(self, current: int, total: int, message: str = ""):
        """進捗を更新"""
        self.progress_widget.update_progress(current, total, message)
        
    def add_log(self, message: str, level: str = "INFO"):
        """ログを追加"""
        self.log_widget.add_log(message, level)
        
    def show_error(self, title: str, message: str):
        """エラーダイアログを表示"""
        messagebox.showerror(title, message)
        
    def show_info(self, title: str, message: str):
        """情報ダイアログを表示"""
        messagebox.showinfo(title, message)
        
    def ask_confirmation(self, title: str, message: str) -> bool:
        """確認ダイアログを表示"""
        return messagebox.askyesno(title, message)
        
    def run(self):
        """アプリケーションを実行"""
        logger.info("拡張版アプリケーションを起動します")
        self.root.mainloop()