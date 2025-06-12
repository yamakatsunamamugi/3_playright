#!/usr/bin/env python3
"""
改善されたメインウィンドウ
- 全体スクロール機能
- 列ごとのAI選択機能
- ログ画面表示
- スプレッドシート分析機能
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio

from src.utils.logger import get_logger
from config.settings import settings
from src.config_manager import get_config_manager

logger = get_logger(__name__)


class ImprovedMainWindow:
    """改善されたメインウィンドウクラス"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("スプレッドシートAI自動処理ツール - 改善版")
        self.root.geometry("1400x900")
        
        # 画面の中央に配置
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # 設定マネージャー
        self.config_manager = get_config_manager()
        
        # 状態管理
        self.processing = False
        self.spreadsheet_structure = None
        self.copy_columns = []
        self.column_ai_configs = {}
        
        # 最新モデル情報を読み込み
        self._load_latest_models()
        
        # UIを作成
        self._create_main_layout()
        self._create_widgets()
        self._load_test_data()
        
        # ウィンドウクローズ時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        logger.info("改善されたメインウィンドウを初期化しました")
    
    def _load_latest_models(self):
        """最新モデル情報を読み込み"""
        try:
            config_file = Path("latest_models_config.json")
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.latest_models = json.load(f)
                logger.info("最新モデル設定を読み込みました")
            else:
                # デフォルトモデル設定
                self.latest_models = {
                    "ChatGPT": {
                        "service_name": "ChatGPT",
                        "models": ["GPT-4o", "o1-preview", "o1-mini", "GPT-4 Turbo"],
                        "default_model": "GPT-4o"
                    },
                    "Claude": {
                        "service_name": "Claude", 
                        "models": ["Claude-3.5 Sonnet (New)", "Claude-3.5 Sonnet", "Claude-3.5 Haiku"],
                        "default_model": "Claude-3.5 Sonnet (New)"
                    },
                    "Gemini": {
                        "service_name": "Gemini",
                        "models": ["Gemini 2.5 Flash", "Gemini 1.5 Pro", "Gemini 1.5 Flash"],
                        "default_model": "Gemini 2.5 Flash"
                    },
                    "Genspark": {
                        "service_name": "Genspark",
                        "models": ["Genspark Pro", "Genspark Standard"],
                        "default_model": "Genspark Pro"
                    },
                    "Google AI Studio": {
                        "service_name": "Google AI Studio",
                        "models": ["Gemini Pro", "Gemini Ultra"],
                        "default_model": "Gemini Pro"
                    }
                }
                logger.info("デフォルトモデル設定を使用します")
        except Exception as e:
            logger.error(f"モデル設定読み込みエラー: {e}")
            self.latest_models = {}
    
    def _create_main_layout(self):
        """メインレイアウトを作成（スクロール対応）"""
        # メインキャンバスとスクロールバー
        self.main_canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)
        
        # スクロール設定
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # レイアウト配置
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # マウスホイールでスクロール
        def _on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        self.main_frame = ttk.Frame(self.scrollable_frame, padding="20")
        self.main_frame.pack(fill="both", expand=True)
        
        # 1. スプレッドシート設定セクション
        self._create_spreadsheet_section()
        
        # 2. 列ごとのAI設定セクション
        self._create_column_ai_section()
        
        # 3. 制御ボタンセクション
        self._create_control_section()
        
        # 4. ログセクション
        self._create_log_section()
    
    def _create_spreadsheet_section(self):
        """スプレッドシート設定セクションを作成"""
        # セクションフレーム
        ss_frame = ttk.LabelFrame(self.main_frame, text="📊 スプレッドシート設定", padding="10")
        ss_frame.pack(fill="x", pady=(0, 10))
        
        # URL入力（横幅を60に縮小）
        ttk.Label(ss_frame, text="スプレッドシートURL:").grid(row=0, column=0, sticky="w", pady=2)
        self.url_var = tk.StringVar(value="https://docs.google.com/spreadsheets/d/1C5aOSyyCBXf7HwF-BGGu-cz5jdRwNBaoW4G4ivIRrRg/edit?gid=1633283608#gid=1633283608")
        url_entry = ttk.Entry(ss_frame, textvariable=self.url_var, width=60)
        url_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # シート名取得ボタン（URL欄の右隣）
        self.get_sheets_button = ttk.Button(
            ss_frame, 
            text="📋 シート名取得", 
            command=self._get_sheet_names,
            width=15
        )
        self.get_sheets_button.grid(row=0, column=2, sticky="w", padx=(10, 0), pady=2)
        
        # シート名選択（2行目）
        ttk.Label(ss_frame, text="シート名:").grid(row=1, column=0, sticky="w", pady=2)
        self.sheet_var = tk.StringVar(value="1.原稿本文作成")
        self.sheet_combo = ttk.Combobox(ss_frame, textvariable=self.sheet_var, width=30)
        self.sheet_combo['values'] = ["1.原稿本文作成", "2.データ集計", "3.分析結果"]
        self.sheet_combo.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=2)
        
        # 分析ボタン（シート名の右隣）
        self.analyze_button = ttk.Button(
            ss_frame, 
            text="🔍 スプレッドシート分析", 
            command=self._analyze_spreadsheet,
            width=20,
            state="disabled"  # 初期は無効
        )
        self.analyze_button.grid(row=1, column=2, sticky="w", padx=(10, 0), pady=2)
        
        # グリッド設定
        ss_frame.columnconfigure(1, weight=1)
    
    def _create_column_ai_section(self):
        """列ごとのAI設定セクションを作成"""
        # セクションフレーム
        self.ai_section_frame = ttk.LabelFrame(self.main_frame, text="🤖 列ごとのAI設定", padding="10")
        self.ai_section_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 初期メッセージ
        self.ai_config_placeholder = ttk.Label(
            self.ai_section_frame, 
            text="📌 まず「スプレッドシート分析」ボタンをクリックして列構造を解析してください",
            foreground="gray"
        )
        self.ai_config_placeholder.pack(pady=20)
        
        # 列設定を格納するフレーム
        self.column_configs_frame = ttk.Frame(self.ai_section_frame)
    
    def _create_control_section(self):
        """制御ボタンセクションを作成"""
        control_frame = ttk.LabelFrame(self.main_frame, text="⚡ 処理制御", padding="10")
        control_frame.pack(fill="x", pady=(0, 10))
        
        # ボタンフレーム
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill="x")
        
        # 開始ボタン
        self.start_button = ttk.Button(
            button_frame,
            text="🚀 処理開始",
            command=self._start_processing,
            width=15
        )
        self.start_button.pack(side="left", padx=(0, 10))
        
        # 停止ボタン
        self.stop_button = ttk.Button(
            button_frame,
            text="⏹️ 停止",
            command=self._stop_processing,
            width=15,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=(0, 10))
        
        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            button_frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(side="left", padx=(20, 0))
        
        # ステータスラベル
        self.status_var = tk.StringVar(value="待機中")
        status_label = ttk.Label(button_frame, textvariable=self.status_var)
        status_label.pack(side="left", padx=(10, 0))
    
    def _create_log_section(self):
        """ログセクションを作成"""
        log_frame = ttk.LabelFrame(self.main_frame, text="📝 実行ログ", padding="10")
        log_frame.pack(fill="both", expand=True)
        
        # ログテキストエリア（編集不可）
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            width=100,
            font=("Consolas", 10),
            state="disabled",  # 編集不可にする
            wrap="word"
        )
        self.log_text.pack(fill="both", expand=True)
        
        # ログクリアボタン
        clear_button = ttk.Button(
            log_frame,
            text="🗑️ ログクリア",
            command=self._clear_log,
            width=15
        )
        clear_button.pack(anchor="e", pady=(5, 0))
    
    def _load_test_data(self):
        """テスト用データを読み込み"""
        self.log("💡 テスト用設定が読み込まれています")
        self.log(f"📊 スプレッドシートURL: {self.url_var.get()}")
        self.log(f"📋 シート名: {self.sheet_var.get()}")
        self.log("📋 まず「シート名取得」ボタンをクリックしてシートを選択してください")
    
    def _get_sheet_names(self):
        """シート名を取得してドロップダウンを更新"""
        if self.processing:
            return
        
        if not self.url_var.get().strip():
            messagebox.showwarning("警告", "スプレッドシートURLを入力してください")
            return
        
        self.log("📋 シート名を取得中...")
        self.get_sheets_button.config(state="disabled")
        
        # 非同期でシート名取得を実行
        thread = threading.Thread(target=self._get_sheet_names_thread)
        thread.daemon = True
        thread.start()
    
    def _get_sheet_names_thread(self):
        """シート名取得スレッド"""
        try:
            from src.ai_tools.sheets_handler import SheetsHandler
            
            # Google Sheets認証
            sheets_handler = SheetsHandler()
            
            if not sheets_handler.authenticate():
                raise Exception("Google Sheets API認証に失敗しました")
            
            if not sheets_handler.set_spreadsheet(self.url_var.get(), ""):
                raise Exception("スプレッドシート設定に失敗しました")
            
            # シート名を取得
            sheet_names = sheets_handler.get_sheet_names()
            
            if not sheet_names:
                raise Exception("シートが見つかりませんでした")
            
            # UIスレッドで結果を表示
            self.root.after(0, self._show_sheet_names_result, sheet_names)
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ シート名取得エラー: {e}"))
            self.root.after(0, lambda: self.get_sheets_button.config(state="normal"))
    
    def _show_sheet_names_result(self, sheet_names):
        """シート名取得結果を表示"""
        self.log(f"✅ シート名取得完了: {len(sheet_names)}個のシート")
        for name in sheet_names:
            self.log(f"   📄 {name}")
        
        # ドロップダウンを更新
        self.sheet_combo['values'] = sheet_names
        
        # 最初のシートを選択
        if sheet_names:
            self.sheet_var.set(sheet_names[0])
            self.log(f"📌 デフォルトシート選択: {sheet_names[0]}")
        
        # 分析ボタンを有効化
        self.analyze_button.config(state="normal")
        self.get_sheets_button.config(state="normal")
        
        self.log("🔍 シートを選択して「スプレッドシート分析」ボタンをクリックしてください")

    def _analyze_spreadsheet(self):
        """スプレッドシート分析を実行"""
        if self.processing:
            return
        
        if not self.url_var.get().strip():
            messagebox.showwarning("警告", "スプレッドシートURLを入力してください")
            return
        
        if not self.sheet_var.get().strip():
            messagebox.showwarning("警告", "シート名を選択してください")
            return
        
        self.log("🔍 スプレッドシート分析を開始...")
        self.status_var.set("分析中...")
        self.analyze_button.config(state="disabled")
        
        # 非同期でスプレッドシート分析を実行
        thread = threading.Thread(target=self._analyze_spreadsheet_thread)
        thread.daemon = True
        thread.start()
    
    def _analyze_spreadsheet_thread(self):
        """スプレッドシート分析スレッド（実際のGoogle Sheets API使用）"""
        try:
            from src.ai_tools.sheets_handler import SheetsHandler
            
            # Google Sheets認証と分析
            sheets_handler = SheetsHandler()
            
            if not sheets_handler.authenticate():
                raise Exception("Google Sheets API認証に失敗しました")
            
            if not sheets_handler.set_spreadsheet(self.url_var.get(), self.sheet_var.get()):
                raise Exception("スプレッドシート設定に失敗しました")
            
            # 実際のシート構造を分析
            sheet_structure = sheets_handler.analyze_sheet_structure()
            
            # copy_columnsを更新
            copy_columns = []
            for col_info in sheet_structure['copy_columns']:
                copy_columns.append({
                    "column": col_info['column_letter'],
                    "name": f"コピー列_{col_info['column_letter']}",
                    "index": col_info['column_index'] - 1,
                    "process_column": col_info['process_column'],
                    "error_column": col_info['error_column'],
                    "paste_column": col_info['paste_column']
                })
            
            self.copy_columns = copy_columns
            
            # UIスレッドで結果を表示
            self.root.after(0, self._show_analysis_result, sheet_structure, copy_columns)
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ 分析エラー: {e}"))
            self.root.after(0, lambda: self.status_var.set("分析エラー"))
            self.root.after(0, lambda: self.analyze_button.config(state="normal"))
    
    def _show_analysis_result(self, sheet_structure, copy_columns):
        """分析結果を表示"""
        self.log(f"✅ スプレッドシート分析完了")
        self.log(f"📊 コピー列: {sheet_structure['total_copy_columns']}個")
        self.log(f"📋 処理対象行: {sheet_structure['total_target_rows']}行")
        
        if copy_columns:
            self.log(f"🎯 「コピー」列を検出: {len(copy_columns)}個")
            for col_info in copy_columns:
                self.log(f"   • {col_info['column']}列: {col_info['name']}")
            
            # 列ごとのAI設定UIを作成
            self._create_column_ai_configs(copy_columns)
        else:
            self.log("⚠️ 「コピー」列が見つかりませんでした")
        
        self.status_var.set("分析完了")
        self.analyze_button.config(state="normal")
    
    def _create_column_ai_configs(self, copy_columns):
        """列ごとのAI設定UIを作成"""
        # プレースホルダーを削除
        self.ai_config_placeholder.pack_forget()
        
        # 既存の設定をクリア
        for widget in self.column_configs_frame.winfo_children():
            widget.destroy()
        
        self.column_configs_frame.pack(fill="both", expand=True)
        
        # 各コピー列に対してAI設定を作成
        for i, col_info in enumerate(copy_columns):
            self._create_single_column_config(col_info, i)
        
        self.log("🤖 列ごとのAI設定UIを作成しました")
    
    def _create_single_column_config(self, col_info, row_index):
        """単一列のAI設定を作成"""
        # 列設定フレーム
        col_frame = ttk.LabelFrame(
            self.column_configs_frame,
            text=f"📝 {col_info['name']} ({col_info['column']}列)",
            padding="10"
        )
        col_frame.pack(fill="x", pady=5)
        
        # AI選択
        ttk.Label(col_frame, text="AI:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        
        ai_var = tk.StringVar(value="ChatGPT")
        ai_combo = ttk.Combobox(col_frame, textvariable=ai_var, width=15)
        ai_combo['values'] = list(self.latest_models.keys())
        ai_combo['state'] = 'readonly'
        ai_combo.grid(row=0, column=1, sticky="w", padx=(0, 10))
        
        # モデル選択
        ttk.Label(col_frame, text="モデル:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        
        model_var = tk.StringVar()
        model_combo = ttk.Combobox(col_frame, textvariable=model_var, width=25)
        model_combo['state'] = 'readonly'
        model_combo.grid(row=0, column=3, sticky="w", padx=(0, 10))
        
        # 設定ボタン
        settings_button = ttk.Button(
            col_frame,
            text="⚙️ 設定",
            command=lambda: self._open_ai_settings(col_info['name'], ai_var.get()),
            width=10
        )
        settings_button.grid(row=0, column=4, sticky="w", padx=(0, 5))
        
        # テストボタン
        test_button = ttk.Button(
            col_frame,
            text="🧪 テスト",
            command=lambda: self._test_ai_connection(col_info['name'], ai_var.get()),
            width=10
        )
        test_button.grid(row=0, column=5, sticky="w")
        
        # 初期モデルを設定
        def update_models(*args):
            selected_ai = ai_var.get()
            if selected_ai in self.latest_models:
                models = self.latest_models[selected_ai].get("models", [])
                model_combo['values'] = models
                if models:
                    model_var.set(models[0])  # 最初のモデルを選択
        
        ai_var.trace('w', update_models)
        update_models()  # 初期設定
        
        # 設定を保存
        self.column_ai_configs[col_info['name']] = {
            'column': col_info['column'],
            'ai_var': ai_var,
            'model_var': model_var,
            'ai_combo': ai_combo,
            'model_combo': model_combo
        }
    
    def _open_ai_settings(self, column_name, ai_name):
        """AI詳細設定ダイアログを開く"""
        self.log(f"⚙️ {column_name}の{ai_name}設定を開きます")
        
        # 設定ダイアログ（簡易版）
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{ai_name} 設定 - {column_name}")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 設定内容
        ttk.Label(dialog, text=f"{ai_name}の詳細設定", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Temperature設定
        ttk.Label(dialog, text="Temperature (創造性):").pack(anchor="w", padx=20)
        temp_var = tk.DoubleVar(value=0.7)
        temp_scale = ttk.Scale(dialog, from_=0.0, to=2.0, variable=temp_var, orient="horizontal")
        temp_scale.pack(fill="x", padx=20, pady=5)
        
        # Max tokens設定
        ttk.Label(dialog, text="Max Tokens (最大文字数):").pack(anchor="w", padx=20, pady=(10, 0))
        tokens_var = tk.IntVar(value=4096)
        tokens_spin = ttk.Spinbox(dialog, from_=100, to=32000, textvariable=tokens_var, width=10)
        tokens_spin.pack(anchor="w", padx=20, pady=5)
        
        # ボタン
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="保存", command=dialog.destroy).pack(side="left", padx=5)
        ttk.Button(button_frame, text="キャンセル", command=dialog.destroy).pack(side="left", padx=5)
    
    def _test_ai_connection(self, column_name, ai_name):
        """AI接続テスト"""
        self.log(f"🧪 {column_name}の{ai_name}接続をテスト中...")
        
        # テストメッセージ
        test_thread = threading.Thread(
            target=self._test_ai_connection_thread,
            args=(column_name, ai_name)
        )
        test_thread.daemon = True
        test_thread.start()
    
    def _test_ai_connection_thread(self, column_name, ai_name):
        """AI接続テストスレッド"""
        try:
            # 実際のAI接続テストを実行
            import asyncio
            from src.browser.cloudflare_bypass_manager import CloudflareBypassManager
            from src.ai_tools.chatgpt_handler import ChatGPTHandler
            from src.ai_tools.base_ai_handler import AIConfig
            
            async def run_real_test():
                bypass_manager = None
                try:
                    self.root.after(0, lambda: self.log(f"🔧 {ai_name}接続テスト開始 - Cloudflare回避機能有効"))
                    
                    # Playwrightの確認
                    try:
                        from playwright.async_api import async_playwright
                        self.root.after(0, lambda: self.log(f"✅ Playwrightインポート成功"))
                    except ImportError as e:
                        self.root.after(0, lambda: self.log(f"❌ Playwrightインポート失敗: {e}"))
                        raise Exception(f"Playwrightが正しくインストールされていません: {e}")
                    
                    # CloudflareBypassManagerを初期化
                    self.root.after(0, lambda: self.log(f"🛡️ Cloudflare回避マネージャーを初期化中..."))
                    bypass_manager = CloudflareBypassManager(
                        headless=False, 
                        use_existing_profile=True,
                        debug_mode=True
                    )
                    
                    # ブラウザを初期化
                    if not await bypass_manager.initialize():
                        raise Exception("Cloudflare回避マネージャーの初期化に失敗しました")
                    
                    self.root.after(0, lambda: self.log(f"✅ Cloudflare回避マネージャー初期化完了"))
                    self.root.after(0, lambda: self.log(f"🚀 {ai_name}ブラウザを起動中..."))
                    
                    # AIサイトにアクセス
                    if ai_name.lower() == "chatgpt":
                        # ステルスページを作成
                        page = await bypass_manager.create_page_with_stealth(
                            "chatgpt_connection", 
                            "https://chat.openai.com"
                        )
                        
                        if page:
                            self.root.after(0, lambda: self.log(f"✅ {ai_name}サイトへのアクセス成功"))
                            self.root.after(0, lambda: self.log(f"🌐 ChatGPTブラウザが開きました - Cloudflare回避機能有効"))
                            
                            # ページ読み込み待機
                            await asyncio.sleep(3)
                            
                            # ログイン状態をチェック
                            login_button = await page.query_selector('[data-testid="login-button"]')
                            if login_button:
                                self.root.after(0, lambda: self.log(f"⚠️ {ai_name}にログインしてください"))
                                self.root.after(0, lambda: self.log(f"💡 ブラウザでログイン後、処理を開始できます"))
                            else:
                                # チャット入力欄の確認
                                chat_input = await page.query_selector('[data-testid="prompt-textarea"]')
                                if chat_input:
                                    self.root.after(0, lambda: self.log(f"✅ {ai_name}ログイン済み - 準備完了"))
                                    # セッションを保存
                                    await bypass_manager.save_session("chatgpt_connection")
                                    self.root.after(0, lambda: self.log(f"💾 ChatGPTセッションを保存しました"))
                                else:
                                    self.root.after(0, lambda: self.log(f"⚠️ {ai_name}の状態確認中..."))
                        else:
                            raise Exception("ChatGPTページの作成に失敗しました")
                    
                    elif ai_name.lower() == "claude":
                        # ステルスページを作成
                        page = await bypass_manager.create_page_with_stealth(
                            "claude_connection", 
                            "https://claude.ai"
                        )
                        
                        if page:
                            self.root.after(0, lambda: self.log(f"✅ Claudeサイトへのアクセス成功"))
                            self.root.after(0, lambda: self.log(f"🌐 Claudeブラウザが開きました - Cloudflare回避機能有効"))
                            
                            # ページ読み込み待機
                            await asyncio.sleep(3)
                            
                            # Claude の入力欄をチェック
                            chat_input = await page.query_selector('div[contenteditable="true"]')
                            if chat_input:
                                self.root.after(0, lambda: self.log(f"✅ Claudeログイン済み - 準備完了"))
                                # セッションを保存
                                await bypass_manager.save_session("claude_connection")
                                self.root.after(0, lambda: self.log(f"💾 Claudeセッションを保存しました"))
                            else:
                                self.root.after(0, lambda: self.log(f"⚠️ Claudeにログインしてください"))
                                self.root.after(0, lambda: self.log(f"💡 ブラウザでログイン後、処理を開始できます"))
                        else:
                            raise Exception("Claudeページの作成に失敗しました")
                    
                    else:
                        # その他のAI（将来の拡張用）
                        self.root.after(0, lambda: self.log(f"⚠️ {ai_name}は接続テスト対象外です"))
                    
                    # テスト完了
                    self.root.after(0, lambda: self.log(f"✅ {column_name}の{ai_name}接続テスト完了"))
                    
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    self.root.after(0, lambda: self.log(f"❌ {column_name}の{ai_name}接続テスト失敗: {str(e)}"))
                    self.root.after(0, lambda: self.log(f"🔍 詳細エラー: {error_details}"))
                    raise
                finally:
                    # 接続テストではクリーンアップしない（ブラウザを開いたまま）
                    self.root.after(0, lambda: self.log(f"🌐 {ai_name}ブラウザは開いたままにします（手動で操作可能）"))
                    # bypass_manager.cleanup() をコメントアウト - ブラウザを閉じない
            
            # 非同期テストを実行
            asyncio.run(run_real_test())
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ {column_name}の{ai_name}接続テスト失敗: {str(e)}"))
    
    def _start_processing(self):
        """処理開始"""
        if not self.copy_columns:
            messagebox.showwarning("警告", "まずスプレッドシート分析を実行してください")
            return
        
        self.processing = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set("処理中...")
        
        self.log("🚀 AI自動処理を開始します")
        
        # 設定確認
        for col_name, config in self.column_ai_configs.items():
            ai = config['ai_var'].get()
            model = config['model_var'].get()
            self.log(f"📝 {col_name}: {ai} - {model}")
        
        # 処理スレッド開始
        process_thread = threading.Thread(target=self._processing_thread)
        process_thread.daemon = True
        process_thread.start()
    
    def _processing_thread(self):
        """処理実行スレッド - 実際のAI処理"""
        try:
            import asyncio
            
            # 非同期処理を実行
            asyncio.run(self._run_real_processing())
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.root.after(0, lambda: self.log(f"❌ 処理中にエラーが発生: {str(e)}"))
            self.root.after(0, lambda: self.log(f"🔍 詳細エラー: {error_details}"))
        finally:
            # 処理完了時の状態リセット
            self.root.after(0, self._reset_processing_state)
    
    async def _run_real_processing(self):
        """実際のAI処理を実行（CLAUDE.md要件に基づく）"""
        from src.browser.cloudflare_bypass_manager import CloudflareBypassManager
        from src.ai_tools.sheets_handler import SheetsHandler
        
        bypass_manager = None
        sheets_handler = None
        
        try:
            self.root.after(0, lambda: self.log("🚀 実際のAI処理を開始"))
            
            # Google Sheets認証
            self.root.after(0, lambda: self.log("📊 Google Sheets APIに接続中..."))
            sheets_handler = SheetsHandler()
            
            if not sheets_handler.authenticate():
                raise Exception("Google Sheets API認証に失敗しました")
            
            if not sheets_handler.set_spreadsheet(self.url_var.get(), self.sheet_var.get()):
                raise Exception("スプレッドシート設定に失敗しました")
            
            # シート構造分析
            self.root.after(0, lambda: self.log("🔍 シート構造を分析中..."))
            sheet_structure = sheets_handler.analyze_sheet_structure()
            
            self.root.after(0, lambda: self.log(f"✅ 分析完了: {sheet_structure['total_copy_columns']}列, {sheet_structure['total_target_rows']}行"))
            
            # Cloudflare回避マネージャーを初期化
            self.root.after(0, lambda: self.log("🛡️ Cloudflare回避マネージャーを初期化中..."))
            bypass_manager = CloudflareBypassManager(
                headless=False, 
                use_existing_profile=True,
                debug_mode=False  # 本番処理ではデバッグ無効
            )
            
            # ブラウザを初期化
            self.root.after(0, lambda: self.log("🚀 ブラウザを起動中..."))
            if not await bypass_manager.initialize():
                raise Exception("Cloudflare回避マネージャーの初期化に失敗しました")
            
            self.root.after(0, lambda: self.log("✅ Cloudflare回避機能付きブラウザ起動成功"))
            
            # 実際の処理開始
            total_tasks = len(sheet_structure['copy_columns']) * len(sheet_structure['target_rows'])
            completed_tasks = 0
            
            # 各コピー列の処理
            for copy_column_info in sheet_structure['copy_columns']:
                if not self.processing:
                    break
                
                col_name = f"コピー列_{copy_column_info['column_letter']}"
                config = self.column_ai_configs.get(col_name)
                
                if not config:
                    self.root.after(0, lambda cn=col_name: self.log(f"⚠️ {cn}の設定が見つかりません"))
                    continue
                
                ai = config['ai_var'].get()
                model = config['model_var'].get()
                
                self.root.after(0, lambda cn=col_name, a=ai: self.log(f"🔄 {cn}を{a}で処理開始"))
                
                # 各行の処理
                for row in sheet_structure['target_rows']:
                    if not self.processing:
                        break
                    
                    try:
                        # 処理状況をチェック
                        process_status = sheets_handler.get_process_status(copy_column_info, row)
                        
                        if process_status not in ['', '未処理']:
                            self.root.after(0, lambda r=row: self.log(f"⏭️ 行{r}は既に処理済み（{process_status}）"))
                            completed_tasks += 1
                            continue
                        
                        # 処理中に変更
                        sheets_handler.set_process_status(copy_column_info, row, "処理中")
                        
                        # コピー列からテキストを取得
                        copy_text = sheets_handler.get_copy_text(copy_column_info, row)
                        
                        if not copy_text.strip():
                            self.root.after(0, lambda r=row: self.log(f"⚠️ 行{r}のコピー列が空です"))
                            sheets_handler.set_process_status(copy_column_info, row, "未処理")
                            completed_tasks += 1
                            continue
                        
                        self.root.after(0, lambda r=row, t=copy_text[:30]: self.log(f"📝 行{r}処理中: {t}..."))
                        
                        # AIで処理
                        ai_result = await self._process_single_text_with_ai(
                            bypass_manager, ai, copy_text, model
                        )
                        
                        if ai_result:
                            # 結果を貼り付け列に書き込み
                            sheets_handler.set_paste_result(copy_column_info, row, ai_result)
                            sheets_handler.set_process_status(copy_column_info, row, "処理済み")
                            sheets_handler.set_error_message(copy_column_info, row, "")  # エラーをクリア
                            
                            self.root.after(0, lambda r=row: self.log(f"✅ 行{r}処理完了"))
                        else:
                            # エラー処理
                            error_msg = "AI処理に失敗しました"
                            sheets_handler.set_error_message(copy_column_info, row, error_msg)
                            sheets_handler.set_process_status(copy_column_info, row, "未処理")
                            
                            self.root.after(0, lambda r=row: self.log(f"❌ 行{r}処理失敗"))
                        
                        completed_tasks += 1
                        
                        # プログレスバー更新
                        progress = (completed_tasks / total_tasks) * 100
                        self.root.after(0, lambda p=progress: self.progress_var.set(p))
                        
                    except Exception as e:
                        # エラー処理
                        error_msg = f"処理エラー: {str(e)}"
                        sheets_handler.set_error_message(copy_column_info, row, error_msg)
                        sheets_handler.set_process_status(copy_column_info, row, "未処理")
                        
                        self.root.after(0, lambda r=row, err=str(e): self.log(f"❌ 行{r}エラー: {err}"))
                        completed_tasks += 1
            
            if self.processing:
                self.root.after(0, lambda: self.log("🎉 全ての処理が完了しました"))
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.root.after(0, lambda: self.log(f"❌ 処理エラー: {str(e)}"))
            self.root.after(0, lambda: self.log(f"🔍 詳細エラー: {error_details}"))
            raise
        finally:
            # リソースのクリーンアップ
            if bypass_manager:
                # ブラウザは接続テスト時と同様に開いたままにする
                self.root.after(0, lambda: self.log("🌐 ブラウザは開いたままにします（手動で操作可能）"))
    
    async def _process_single_text_with_ai(self, bypass_manager, ai_name: str, text: str, model: str) -> Optional[str]:
        """
        単一テキストをAIで処理
        
        Args:
            bypass_manager: Cloudflare回避マネージャー
            ai_name: AI名
            text: 処理するテキスト
            model: 使用モデル
            
        Returns:
            Optional[str]: AI処理結果（失敗時None）
        """
        try:
            if ai_name == "ChatGPT" or ai_name == "chatgpt":
                return await self._process_text_with_chatgpt(bypass_manager, text, model)
            elif ai_name == "Claude" or ai_name == "claude":
                return await self._process_text_with_claude(bypass_manager, text, model)
            elif ai_name == "Gemini" or ai_name == "gemini":
                return await self._process_text_with_gemini(bypass_manager, text, model)
            elif ai_name == "Genspark" or ai_name == "genspark":
                return await self._process_text_with_genspark(bypass_manager, text, model)
            elif ai_name == "Google AI Studio":
                return await self._process_text_with_google_ai_studio(bypass_manager, text, model)
            else:
                self.root.after(0, lambda: self.log(f"❌ 未対応のAI: {ai_name}"))
                return None
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ {ai_name}テキスト処理エラー: {str(e)}"))
            return None
    
    async def _process_text_with_chatgpt(self, bypass_manager, text: str, model: str) -> Optional[str]:
        """ChatGPTでテキストを処理"""
        try:
            page = await bypass_manager.create_page_with_stealth("chatgpt_process", "https://chat.openai.com")
            
            if not page:
                return None
            
            await asyncio.sleep(3)
            
            # チャット入力欄を探す
            chat_input = await page.query_selector('[data-testid="prompt-textarea"]')
            if not chat_input:
                return None
            
            # テキストを入力
            await chat_input.fill(text)
            await asyncio.sleep(1)
            
            # 送信
            send_button = await page.query_selector('[data-testid="send-button"]')
            if send_button:
                await send_button.click()
            else:
                await page.keyboard.press('Enter')
            
            # 回答を待機（最大2分）
            await asyncio.sleep(5)  # 初期待機
            
            # 回答完了を待機
            for _ in range(24):  # 2分間待機
                if not self.processing:
                    return None
                
                # 送信ボタンが再び有効になったかチェック
                send_button = await page.query_selector('[data-testid="send-button"]:not([disabled])')
                if send_button:
                    break
                await asyncio.sleep(5)
            
            # 最新の回答を取得
            response_elements = await page.query_selector_all('[data-message-author-role="assistant"]')
            if response_elements:
                last_response = response_elements[-1]
                response_text = await last_response.inner_text()
                return response_text.strip()
            
            return None
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ ChatGPTテキスト処理エラー: {str(e)}"))
            return None
    
    async def _process_text_with_claude(self, bypass_manager, text: str, model: str) -> Optional[str]:
        """Claudeでテキストを処理"""
        try:
            page = await bypass_manager.create_page_with_stealth("claude_process", "https://claude.ai")
            
            if not page:
                return None
            
            await asyncio.sleep(3)
            
            # チャット入力欄を探す
            chat_input = await page.query_selector('div[contenteditable="true"]')
            if not chat_input:
                return None
            
            # テキストを入力
            await chat_input.fill(text)
            await asyncio.sleep(1)
            
            # 送信
            await page.keyboard.press('Enter')
            
            # 回答を待機
            await asyncio.sleep(5)
            
            # 回答完了を待機
            for _ in range(24):  # 2分間待機
                if not self.processing:
                    return None
                
                # 入力欄が再び有効になったかチェック
                input_enabled = await page.query_selector('div[contenteditable="true"]:not([disabled])')
                if input_enabled:
                    break
                await asyncio.sleep(5)
            
            # 最新の回答を取得
            messages = await page.query_selector_all('[data-is-streaming="false"]')
            if messages:
                last_message = messages[-1]
                response_text = await last_message.inner_text()
                return response_text.strip()
            
            return None
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Claudeテキスト処理エラー: {str(e)}"))
            return None
    
    async def _process_text_with_gemini(self, bypass_manager, text: str, model: str) -> Optional[str]:
        """Geminiでテキストを処理"""
        try:
            page = await bypass_manager.create_page_with_stealth("gemini_process", "https://gemini.google.com")
            
            if not page:
                return None
            
            await asyncio.sleep(3)
            
            # チャット入力欄を探す
            chat_input = await page.query_selector('rich-textarea textarea')
            if not chat_input:
                chat_input = await page.query_selector('textarea[placeholder*="Enter"]')
            
            if not chat_input:
                return None
            
            # テキストを入力
            await chat_input.fill(text)
            await asyncio.sleep(1)
            
            # 送信
            send_button = await page.query_selector('button[aria-label*="Send"]')
            if send_button:
                await send_button.click()
            else:
                await page.keyboard.press('Enter')
            
            # 回答を待機
            await asyncio.sleep(10)
            
            # 回答を取得
            response_elements = await page.query_selector_all('[data-response-id]')
            if response_elements:
                last_response = response_elements[-1]
                response_text = await last_response.inner_text()
                return response_text.strip()
            
            return None
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Geminiテキスト処理エラー: {str(e)}"))
            return None
    
    async def _process_text_with_genspark(self, bypass_manager, text: str, model: str) -> Optional[str]:
        """Gensparkでテキストを処理"""
        try:
            page = await bypass_manager.create_page_with_stealth("genspark_process", "https://www.genspark.ai")
            
            if not page:
                return None
            
            await asyncio.sleep(3)
            
            # チャット入力欄を探す
            chat_input = await page.query_selector('textarea[placeholder*="Ask"]')
            if not chat_input:
                chat_input = await page.query_selector('input[type="text"]')
            
            if not chat_input:
                return None
            
            # テキストを入力
            await chat_input.fill(text)
            await asyncio.sleep(1)
            
            # 送信
            await page.keyboard.press('Enter')
            
            # 回答を待機
            await asyncio.sleep(15)
            
            # 回答を取得（Gensparkの具体的なセレクターは要調整）
            response_elements = await page.query_selector_all('.response-content')
            if response_elements:
                last_response = response_elements[-1]
                response_text = await last_response.inner_text()
                return response_text.strip()
            
            return None
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Gensparkテキスト処理エラー: {str(e)}"))
            return None
    
    async def _process_text_with_google_ai_studio(self, bypass_manager, text: str, model: str) -> Optional[str]:
        """Google AI Studioでテキストを処理"""
        try:
            page = await bypass_manager.create_page_with_stealth("google_ai_studio_process", "https://aistudio.google.com")
            
            if not page:
                return None
            
            await asyncio.sleep(3)
            
            # チャット入力欄を探す
            chat_input = await page.query_selector('textarea[placeholder*="Enter"]')
            if not chat_input:
                chat_input = await page.query_selector('div[contenteditable="true"]')
            
            if not chat_input:
                return None
            
            # テキストを入力
            await chat_input.fill(text)
            await asyncio.sleep(1)
            
            # 送信
            await page.keyboard.press('Enter')
            
            # 回答を待機
            await asyncio.sleep(10)
            
            # 回答を取得（Google AI Studioの具体的なセレクターは要調整）
            response_elements = await page.query_selector_all('.response-container')
            if response_elements:
                last_response = response_elements[-1]
                response_text = await last_response.inner_text()
                return response_text.strip()
            
            return None
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Google AI Studioテキスト処理エラー: {str(e)}"))
            return None

    async def _process_with_ai(self, bypass_manager, ai_name, col_name, model):
        """指定されたAIで実際の処理を実行"""
        try:
            if ai_name == "ChatGPT":
                return await self._process_with_chatgpt(bypass_manager, col_name, model)
            elif ai_name == "Claude":
                return await self._process_with_claude(bypass_manager, col_name, model)
            elif ai_name == "Gemini":
                return await self._process_with_gemini(bypass_manager, col_name, model)
            elif ai_name == "Genspark":
                return await self._process_with_genspark(bypass_manager, col_name, model)
            elif ai_name == "Google AI Studio":
                return await self._process_with_google_ai_studio(bypass_manager, col_name, model)
            else:
                self.root.after(0, lambda: self.log(f"❌ 未対応のAI: {ai_name}"))
                return False
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ {ai_name}処理エラー: {str(e)}"))
            return False
    
    async def _process_with_chatgpt(self, bypass_manager, col_name, model):
        """ChatGPTで実際の処理を実行"""
        try:
            page = await bypass_manager.create_page_with_stealth(f"chatgpt_{col_name}", "https://chat.openai.com")
            
            if not page:
                raise Exception("ChatGPTページの作成に失敗")
            
            self.root.after(0, lambda: self.log(f"✅ ChatGPTサイトにアクセス成功"))
            
            # ページ読み込み待機
            await asyncio.sleep(3)
            
            # ログイン状態確認
            login_button = await page.query_selector('[data-testid="login-button"]')
            
            if login_button:
                self.root.after(0, lambda: self.log(f"⚠️ ChatGPTにログインしてください（手動）"))
                # ユーザーのログインを最大5分待機
                for wait_time in range(30):
                    if not self.processing:
                        return False
                    await asyncio.sleep(10)
                    login_button = await page.query_selector('[data-testid="login-button"]')
                    if not login_button:
                        self.root.after(0, lambda: self.log(f"✅ ログイン完了を確認"))
                        break
                    self.root.after(0, lambda w=wait_time: self.log(f"⏳ ログイン待機中 ({w+1}/30)"))
                else:
                    self.root.after(0, lambda: self.log(f"❌ ログインタイムアウト"))
                    return False
            
            # チャット入力欄の確認
            chat_input = await page.query_selector('[data-testid="prompt-textarea"]')
            if not chat_input:
                self.root.after(0, lambda: self.log(f"❌ チャット入力欄が見つかりません"))
                return False
            
            self.root.after(0, lambda: self.log(f"✅ ChatGPT準備完了"))
            
            # テストメッセージ送信
            test_message = "こんにちは、テストメッセージです。"
            await chat_input.fill(test_message)
            await asyncio.sleep(1)
            
            # 送信ボタンをクリック
            send_button = await page.query_selector('[data-testid="send-button"]')
            if not send_button:
                # Enterキーで送信を試行
                await page.keyboard.press('Enter')
                self.root.after(0, lambda: self.log(f"📤 Enterキーでメッセージ送信: {test_message}"))
            else:
                await send_button.click()
                self.root.after(0, lambda: self.log(f"📤 メッセージ送信: {test_message}"))
            
            # 回答を待機
            await asyncio.sleep(10)
            self.root.after(0, lambda: self.log(f"✅ ChatGPT処理完了"))
            return True
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ ChatGPT処理エラー: {str(e)}"))
            return False
    
    async def _process_with_claude(self, bypass_manager, col_name, model):
        """Claudeで実際の処理を実行"""
        try:
            page = await bypass_manager.create_page_with_stealth(f"claude_{col_name}", "https://claude.ai")
            
            if not page:
                raise Exception("Claudeページの作成に失敗")
            
            self.root.after(0, lambda: self.log(f"✅ Claudeサイトにアクセス成功"))
            await asyncio.sleep(3)
            
            # ログイン状態確認（Claudeの場合）
            # 実際の実装では、Claudeのログイン状態を確認する適切なセレクターを使用
            chat_input = await page.query_selector('div[contenteditable="true"]')
            if not chat_input:
                self.root.after(0, lambda: self.log(f"⚠️ Claudeにログインまたはページ読み込みが必要です"))
                await asyncio.sleep(10)  # 追加待機
                chat_input = await page.query_selector('div[contenteditable="true"]')
            
            if chat_input:
                self.root.after(0, lambda: self.log(f"✅ Claude準備完了"))
                
                # テストメッセージ送信
                test_message = "こんにちは、テストメッセージです。"
                await chat_input.fill(test_message)
                await asyncio.sleep(1)
                
                # 送信（Enterキー）
                await page.keyboard.press('Enter')
                self.root.after(0, lambda: self.log(f"📤 Claudeメッセージ送信: {test_message}"))
                
                # 回答を待機
                await asyncio.sleep(10)
                self.root.after(0, lambda: self.log(f"✅ Claude処理完了"))
                return True
            else:
                self.root.after(0, lambda: self.log(f"❌ Claude入力欄が見つかりません"))
                return False
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Claude処理エラー: {str(e)}"))
            return False
    
    async def _process_with_gemini(self, bypass_manager, col_name, model):
        """Geminiで実際の処理を実行"""
        try:
            page = await bypass_manager.create_page_with_stealth(f"gemini_{col_name}", "https://gemini.google.com")
            
            if not page:
                raise Exception("Geminiページの作成に失敗")
            
            self.root.after(0, lambda: self.log(f"✅ Geminiサイトにアクセス成功"))
            await asyncio.sleep(3)
            
            # Geminiのチャット入力欄を検索
            chat_input = await page.query_selector('rich-textarea textarea')
            if not chat_input:
                # 代替セレクター
                chat_input = await page.query_selector('textarea[placeholder*="Enter"]')
            
            if chat_input:
                self.root.after(0, lambda: self.log(f"✅ Gemini準備完了"))
                
                # テストメッセージ送信
                test_message = "こんにちは、テストメッセージです。"
                await chat_input.fill(test_message)
                await asyncio.sleep(1)
                
                # 送信ボタンまたはEnterキー
                send_button = await page.query_selector('button[aria-label*="Send"]')
                if send_button:
                    await send_button.click()
                else:
                    await page.keyboard.press('Enter')
                
                self.root.after(0, lambda: self.log(f"📤 Geminiメッセージ送信: {test_message}"))
                
                # 回答を待機
                await asyncio.sleep(10)
                self.root.after(0, lambda: self.log(f"✅ Gemini処理完了"))
                return True
            else:
                self.root.after(0, lambda: self.log(f"❌ Gemini入力欄が見つかりません"))
                return False
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Gemini処理エラー: {str(e)}"))
            return False
    
    async def _process_with_genspark(self, bypass_manager, col_name, model):
        """Gensparkで実際の処理を実行"""
        try:
            page = await bypass_manager.create_page_with_stealth(f"genspark_{col_name}", "https://www.genspark.ai")
            
            if not page:
                raise Exception("Gensparkページの作成に失敗")
            
            self.root.after(0, lambda: self.log(f"✅ Gensparkサイトにアクセス成功"))
            await asyncio.sleep(3)
            
            # Gensparkのチャット入力欄を検索
            chat_input = await page.query_selector('textarea[placeholder*="Ask"]')
            if not chat_input:
                # 代替セレクター
                chat_input = await page.query_selector('input[type="text"]')
            
            if chat_input:
                self.root.after(0, lambda: self.log(f"✅ Genspark準備完了"))
                
                # テストメッセージ送信
                test_message = "こんにちは、テストメッセージです。"
                await chat_input.fill(test_message)
                await asyncio.sleep(1)
                
                # 送信
                await page.keyboard.press('Enter')
                self.root.after(0, lambda: self.log(f"📤 Gensparkメッセージ送信: {test_message}"))
                
                # 回答を待機
                await asyncio.sleep(10)
                self.root.after(0, lambda: self.log(f"✅ Genspark処理完了"))
                return True
            else:
                self.root.after(0, lambda: self.log(f"❌ Genspark入力欄が見つかりません"))
                return False
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Genspark処理エラー: {str(e)}"))
            return False
    
    async def _process_with_google_ai_studio(self, bypass_manager, col_name, model):
        """Google AI Studioで実際の処理を実行"""
        try:
            page = await bypass_manager.create_page_with_stealth(f"google_ai_studio_{col_name}", "https://aistudio.google.com")
            
            if not page:
                raise Exception("Google AI Studioページの作成に失敗")
            
            self.root.after(0, lambda: self.log(f"✅ Google AI Studioサイトにアクセス成功"))
            await asyncio.sleep(3)
            
            # Google AI Studioのチャット入力欄を検索
            chat_input = await page.query_selector('textarea[placeholder*="Enter"]')
            if not chat_input:
                # 代替セレクター
                chat_input = await page.query_selector('div[contenteditable="true"]')
            
            if chat_input:
                self.root.after(0, lambda: self.log(f"✅ Google AI Studio準備完了"))
                
                # テストメッセージ送信
                test_message = "こんにちは、テストメッセージです。"
                await chat_input.fill(test_message)
                await asyncio.sleep(1)
                
                # 送信
                await page.keyboard.press('Enter')
                self.root.after(0, lambda: self.log(f"📤 Google AI Studioメッセージ送信: {test_message}"))
                
                # 回答を待機
                await asyncio.sleep(10)
                self.root.after(0, lambda: self.log(f"✅ Google AI Studio処理完了"))
                return True
            else:
                self.root.after(0, lambda: self.log(f"❌ Google AI Studio入力欄が見つかりません"))
                return False
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ Google AI Studio処理エラー: {str(e)}"))
            return False
    
    def _reset_processing_state(self):
        """処理状態をリセット"""
        self.processing = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("待機中")
        self.progress_var.set(0)
    
    def _stop_processing(self):
        """処理停止"""
        self.processing = False
        self.log("⏹️ 処理停止が要求されました")
    
    def _clear_log(self):
        """ログをクリア"""
        self.log_text.config(state="normal")  # 一時的に編集可能にする
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")  # 再度編集不可にする
    
    def log(self, message):
        """ログにメッセージを追加"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # 一時的に編集可能にしてメッセージを追加
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")  # 再度編集不可にする
        
        # コンソールにも出力
        print(formatted_message.strip())
    
    def _on_window_close(self):
        """ウィンドウクローズ時の処理"""
        if self.processing:
            if messagebox.askokcancel("確認", "処理中です。終了しますか？"):
                self.processing = False
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """アプリケーションを実行"""
        self.log("🚀 アプリケーション開始")
        self.root.mainloop()


if __name__ == "__main__":
    app = ImprovedMainWindow()
    app.run()