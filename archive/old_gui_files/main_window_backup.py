import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from src.utils.logger import get_logger
from config.settings import settings


logger = get_logger(__name__)


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(settings.WINDOW_TITLE)
        self.root.geometry(f"{settings.WINDOW_WIDTH}x{settings.WINDOW_HEIGHT}")
        
        self.spreadsheet_url_var = tk.StringVar()
        self.selected_sheet_var = tk.StringVar()
        self.ai_selections = {}
        self.model_selections = {}
        self.processing = False
        
        self._create_widgets()
        self._layout_widgets()
        
        logger.info("メインウィンドウを初期化しました")
        
    def _create_widgets(self):
        self.main_frame = ttk.Frame(self.root, padding="10")
        
        self.url_label = ttk.Label(self.main_frame, text="スプレッドシートURL:")
        self.url_entry = ttk.Entry(self.main_frame, textvariable=self.spreadsheet_url_var, width=50)
        self.load_button = ttk.Button(self.main_frame, text="読み込み", command=self._load_spreadsheet)
        
        self.sheet_label = ttk.Label(self.main_frame, text="シート選択:")
        self.sheet_combo = ttk.Combobox(self.main_frame, textvariable=self.selected_sheet_var, state="readonly")
        
        self.ai_frame = ttk.LabelFrame(self.main_frame, text="AI設定", padding="10")
        
        self.log_frame = ttk.LabelFrame(self.main_frame, text="実行ログ", padding="10")
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=10, width=70)
        self.log_text.config(state=tk.DISABLED)
        
        self.button_frame = ttk.Frame(self.main_frame)
        self.start_button = ttk.Button(self.button_frame, text="処理開始", command=self._start_processing)
        self.stop_button = ttk.Button(self.button_frame, text="停止", command=self._stop_processing, state=tk.DISABLED)
        
        self.status_label = ttk.Label(self.main_frame, text="待機中", relief=tk.SUNKEN)
        
    def _layout_widgets(self):
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        row = 0
        self.url_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.url_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        self.load_button.grid(row=row, column=2, pady=5)
        
        row += 1
        self.sheet_label.grid(row=row, column=0, sticky=tk.W, pady=5)
        self.sheet_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        row += 1
        self.ai_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        row += 1
        self.log_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        row += 1
        self.button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        row += 1
        self.status_label.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(3, weight=1)
        
    def add_log(self, message: str, level: str = "INFO"):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{level}] {message}\\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def update_status(self, status: str):
        self.status_label.config(text=status)
        
    def _load_spreadsheet(self):
        url = self.spreadsheet_url_var.get()
        if not url:
            messagebox.showwarning("警告", "スプレッドシートURLを入力してください")
            return
            
        self.add_log(f"スプレッドシートを読み込み中: {url}")
        
    def _start_processing(self):
        if not self.selected_sheet_var.get():
            messagebox.showwarning("警告", "シートを選択してください")
            return
            
        self.processing = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.update_status("処理中...")
        
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
            
    def create_ai_selection_widgets(self):
        for i, ai_tool in enumerate(settings.SUPPORTED_AI_TOOLS):
            frame = ttk.Frame(self.ai_frame)
            frame.grid(row=i, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
            
            label = ttk.Label(frame, text=f"{ai_tool}:", width=15)
            label.pack(side=tk.LEFT, padx=5)
            
            use_var = tk.BooleanVar()
            checkbox = ttk.Checkbutton(frame, text="使用", variable=use_var)
            checkbox.pack(side=tk.LEFT, padx=5)
            
            model_var = tk.StringVar()
            model_combo = ttk.Combobox(frame, textvariable=model_var, state="readonly", width=20)
            model_combo.pack(side=tk.LEFT, padx=5)
            
            self.ai_selections[ai_tool] = use_var
            self.model_selections[ai_tool] = (model_var, model_combo)
            
    def run(self):
        self.create_ai_selection_widgets()
        logger.info("アプリケーションを起動します")
        self.root.mainloop()