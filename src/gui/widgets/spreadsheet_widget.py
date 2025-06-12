"""
スプレッドシート選択・管理ウィジェット

スプレッドシートURLの入力、シート一覧の取得・選択機能を提供する
Google Sheets APIと連携してシート情報を動的に取得
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Optional
import threading
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SpreadsheetWidget:
    """スプレッドシート操作ウィジェット"""
    
    def __init__(self, parent: tk.Widget, on_sheet_selected: Optional[Callable[[str, str], None]] = None):
        """
        SpreadsheetWidgetを初期化
        
        Args:
            parent: 親ウィジェット
            on_sheet_selected: シート選択時のコールバック関数 callback(url, sheet_name)
        """
        self.parent = parent
        self.on_sheet_selected = on_sheet_selected
        
        # 変数の初期化
        self.url_var = tk.StringVar(value="https://docs.google.com/spreadsheets/d/1C5aOSyyCBXf7HwF-BGGu-cz5jdRwNBaoW4G4ivIRrRg/edit")
        self.selected_sheet_var = tk.StringVar(value="1.原稿本文作成")
        self.loading = False
        
        # ウィジェット作成
        self._create_widgets()
        self._setup_callbacks()
        
        logger.debug("SpreadsheetWidgetを初期化しました")
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        self.frame = ttk.LabelFrame(self.parent, text="スプレッドシート設定", padding="10")
        
        # URL入力エリア
        self.url_label = ttk.Label(self.frame, text="スプレッドシートURL:")
        self.url_entry = ttk.Entry(self.frame, textvariable=self.url_var, width=60)
        self.load_button = ttk.Button(
            self.frame, 
            text="シート一覧取得", 
            command=self._load_sheets_async
        )
        
        # シート選択エリア
        self.sheet_label = ttk.Label(self.frame, text="シート選択:")
        self.sheet_combo = ttk.Combobox(
            self.frame, 
            textvariable=self.selected_sheet_var, 
            state="readonly",
            width=40
        )
        
        # ステータス表示
        self.status_label = ttk.Label(self.frame, text="URLを入力してください", foreground="gray")
        
        # プログレスバー（読み込み中のみ表示）
        self.progress = ttk.Progressbar(
            self.frame, 
            mode='indeterminate',
            length=200
        )
        
        self._layout_widgets()
    
    def _layout_widgets(self):
        """ウィジェットのレイアウト"""
        # URL入力行
        self.url_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        self.load_button.grid(row=0, column=2, pady=5)
        
        # シート選択行
        self.sheet_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.sheet_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # ステータス・プログレス行
        self.status_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        # プログレスバーは最初は非表示
        
        # 列の重み設定
        self.frame.columnconfigure(1, weight=1)
    
    def _setup_callbacks(self):
        """コールバック設定"""
        # URL変更時の処理
        self.url_var.trace('w', self._on_url_changed)
        
        # シート選択時の処理
        self.selected_sheet_var.trace('w', self._on_sheet_selected)
    
    def _on_url_changed(self, *args):
        """URL入力フィールド変更時の処理"""
        url = self.url_var.get().strip()
        
        if url:
            self.load_button.config(state=tk.NORMAL)
            self.status_label.config(text="「シート一覧取得」ボタンをクリックしてください", foreground="blue")
        else:
            self.load_button.config(state=tk.DISABLED)
            self.status_label.config(text="URLを入力してください", foreground="gray")
        
        # シート選択をクリア
        self.sheet_combo['values'] = ()
        self.selected_sheet_var.set('')
    
    def _on_sheet_selected(self, *args):
        """シート選択時の処理"""
        sheet_name = self.selected_sheet_var.get()
        url = self.url_var.get().strip()
        
        if sheet_name and url and self.on_sheet_selected:
            logger.info(f"シートが選択されました: {sheet_name}")
            self.on_sheet_selected(url, sheet_name)
    
    def _load_sheets_async(self):
        """非同期でシート一覧を取得"""
        if self.loading:
            return
        
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("警告", "スプレッドシートURLを入力してください")
            return
        
        # 非同期実行
        thread = threading.Thread(target=self._load_sheets_worker, args=(url,))
        thread.daemon = True
        thread.start()
    
    def _load_sheets_worker(self, url: str):
        """シート一覧取得のワーカー関数"""
        try:
            self.loading = True
            self._set_loading_state(True)
            
            # TODO: 実際のGoogle Sheets API呼び出し
            # 現在はモックデータを使用
            sheets = self._mock_get_sheet_names(url)
            
            # UIの更新は メインスレッドで実行
            self.parent.after(0, self._update_sheet_list, sheets)
            
        except Exception as e:
            logger.error(f"シート一覧の取得に失敗しました: {e}")
            self.parent.after(0, self._show_error, str(e))
        finally:
            self.loading = False
            self.parent.after(0, self._set_loading_state, False)
    
    def _mock_get_sheet_names(self, url: str) -> List[str]:
        """
        モック: シート名一覧を取得
        実際の実装では Google Sheets API を使用
        """
        import time
        time.sleep(1)  # API呼び出しをシミュレート
        
        # モックデータ
        return ["メインシート", "データ入力", "処理結果", "設定", "ログ"]
    
    def _update_sheet_list(self, sheets: List[str]):
        """シート一覧をUIに反映"""
        if sheets:
            self.sheet_combo['values'] = sheets
            self.sheet_combo.config(state="readonly")
            self.status_label.config(
                text=f"{len(sheets)}個のシートが見つかりました。シートを選択してください", 
                foreground="green"
            )
            logger.info(f"{len(sheets)}個のシートを取得しました")
        else:
            self.sheet_combo['values'] = ()
            self.status_label.config(text="シートが見つかりませんでした", foreground="red")
            logger.warning("シートが見つかりませんでした")
    
    def _show_error(self, error_message: str):
        """エラーメッセージ表示"""
        self.status_label.config(text="エラーが発生しました", foreground="red")
        messagebox.showerror("エラー", f"シート一覧の取得に失敗しました:\\n{error_message}")
    
    def _set_loading_state(self, loading: bool):
        """ローディング状態の設定"""
        if loading:
            self.load_button.config(state=tk.DISABLED, text="読み込み中...")
            self.url_entry.config(state=tk.DISABLED)
            self.progress.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
            self.progress.start()
            self.status_label.config(text="シート一覧を取得中...", foreground="orange")
        else:
            self.load_button.config(state=tk.NORMAL, text="シート一覧取得")
            self.url_entry.config(state=tk.NORMAL)
            self.progress.stop()
            self.progress.grid_remove()  # 非表示
    
    def set_values(self, url: str, sheet_name: str = ""):
        """
        外部から値を設定
        
        Args:
            url: スプレッドシートURL
            sheet_name: シート名（省略可能）
        """
        self.url_var.set(url)
        if sheet_name:
            self.selected_sheet_var.set(sheet_name)
    
    def get_values(self) -> tuple[str, str]:
        """
        現在の設定値を取得
        
        Returns:
            (url, sheet_name) のタプル
        """
        return self.url_var.get().strip(), self.selected_sheet_var.get()
    
    def grid(self, **kwargs):
        """ウィジェットをgridで配置"""
        self.frame.grid(**kwargs)
    
    def pack(self, **kwargs):
        """ウィジェットをpackで配置"""
        self.frame.pack(**kwargs)