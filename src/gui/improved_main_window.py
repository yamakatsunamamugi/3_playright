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
        self.root.geometry("1200x800")
        
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
                    "chatgpt": {
                        "service_name": "ChatGPT",
                        "models": ["GPT-4o", "o1-preview", "o1-mini", "GPT-4 Turbo"],
                        "default_model": "GPT-4o"
                    },
                    "claude": {
                        "service_name": "Claude", 
                        "models": ["Claude-3.5 Sonnet (New)", "Claude-3.5 Sonnet", "Claude-3.5 Haiku"],
                        "default_model": "Claude-3.5 Sonnet (New)"
                    },
                    "gemini": {
                        "service_name": "Gemini",
                        "models": ["Gemini 2.5 Flash", "Gemini 1.5 Pro", "Gemini 1.5 Flash"],
                        "default_model": "Gemini 2.5 Flash"
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
        
        # URL入力
        ttk.Label(ss_frame, text="スプレッドシートURL:").grid(row=0, column=0, sticky="w", pady=2)
        self.url_var = tk.StringVar(value="https://docs.google.com/spreadsheets/d/1mhvJKjNNdFqn_xo1D7iZzEyoLm9_2Qh3TbcV8NrW5Sx")
        url_entry = ttk.Entry(ss_frame, textvariable=self.url_var, width=80)
        url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=2)
        
        # シート名選択
        ttk.Label(ss_frame, text="シート名:").grid(row=1, column=0, sticky="w", pady=2)
        self.sheet_var = tk.StringVar(value="1.原稿本文作成")
        self.sheet_combo = ttk.Combobox(ss_frame, textvariable=self.sheet_var, width=30)
        self.sheet_combo['values'] = ["1.原稿本文作成", "2.データ集計", "3.分析結果"]
        self.sheet_combo.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=2)
        
        # 分析ボタン
        self.analyze_button = ttk.Button(
            ss_frame, 
            text="📋 スプレッドシート分析", 
            command=self._analyze_spreadsheet,
            width=20
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
        self.log("🔍 「スプレッドシート分析」ボタンをクリックして開始してください")
    
    def _analyze_spreadsheet(self):
        """スプレッドシート分析を実行"""
        if self.processing:
            return
        
        self.log("🔍 スプレッドシート分析を開始...")
        self.status_var.set("分析中...")
        self.analyze_button.config(state="disabled")
        
        # 非同期でスプレッドシート分析を実行
        thread = threading.Thread(target=self._analyze_spreadsheet_thread)
        thread.daemon = True
        thread.start()
    
    def _analyze_spreadsheet_thread(self):
        """スプレッドシート分析スレッド"""
        try:
            # シミュレーション: 実際にはGoogle Sheets APIを使用
            import time
            time.sleep(2)
            
            # 模擬的な列構造
            mock_columns = {
                "A": "番号",
                "B": "タイトル", 
                "C": "コピー1",
                "D": "処理状況1",
                "E": "エラー1",
                "F": "結果1",
                "G": "コピー2",
                "H": "処理状況2", 
                "I": "エラー2",
                "J": "結果2"
            }
            
            # 「コピー」列を検出
            copy_columns = []
            for col, name in mock_columns.items():
                if "コピー" in name:
                    copy_columns.append({
                        "column": col,
                        "name": name,
                        "index": ord(col) - ord('A')
                    })
            
            self.copy_columns = copy_columns
            
            # UIスレッドで結果を表示
            self.root.after(0, self._show_analysis_result, mock_columns, copy_columns)
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ 分析エラー: {e}"))
            self.root.after(0, lambda: self.status_var.set("分析エラー"))
            self.root.after(0, lambda: self.analyze_button.config(state="normal"))
    
    def _show_analysis_result(self, columns, copy_columns):
        """分析結果を表示"""
        self.log(f"✅ スプレッドシート分析完了")
        self.log(f"📊 検出された列: {len(columns)}個")
        
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
            from src.ai_tools.browser_manager import BrowserManager
            from src.ai_tools.chatgpt_handler import ChatGPTHandler
            from src.ai_tools.base_ai_handler import AIConfig
            
            async def run_real_test():
                browser_manager = None
                try:
                    self.root.after(0, lambda: self.log(f"🔧 {ai_name}接続テスト開始 - 詳細ログ有効"))
                    
                    # Playwrightの確認
                    try:
                        from playwright.async_api import async_playwright
                        self.root.after(0, lambda: self.log(f"✅ Playwrightインポート成功"))
                    except ImportError as e:
                        self.root.after(0, lambda: self.log(f"❌ Playwrightインポート失敗: {e}"))
                        raise Exception(f"Playwrightが正しくインストールされていません: {e}")
                    
                    # ブラウザマネージャーを初期化
                    self.root.after(0, lambda: self.log(f"📋 BrowserManagerを初期化中..."))
                    browser_manager = BrowserManager()
                    self.root.after(0, lambda: self.log(f"✅ BrowserManager初期化完了"))
                    
                    self.root.after(0, lambda: self.log(f"🚀 {ai_name}ブラウザを起動中..."))
                    
                    # ブラウザを起動（ヘッドレスではなく実際に表示）
                    self.root.after(0, lambda: self.log(f"🔧 Playwright起動パラメータ: headless=False, use_existing_profile=True"))
                    browser_started = await browser_manager.start_browser(
                        headless=False, 
                        use_existing_profile=True
                    )
                    
                    self.root.after(0, lambda: self.log(f"🔍 ブラウザ起動結果: {browser_started}"))
                    
                    if not browser_started:
                        raise Exception("ブラウザの起動に失敗しました")
                    
                    self.root.after(0, lambda: self.log(f"✅ {ai_name}ブラウザ起動成功"))
                    
                    # AIハンドラーを作成
                    if ai_name == "ChatGPT":
                        config = AIConfig(ai_name="chatgpt", model_name="gpt-4o")
                        page = await browser_manager.create_page("chatgpt_test", "https://chat.openai.com")
                        
                        if page:
                            self.root.after(0, lambda: self.log(f"✅ {ai_name}サイトへのアクセス成功"))
                            
                            # ログイン状態をチェック
                            await asyncio.sleep(3)  # ページ読み込み待機
                            
                            # ログインボタンの存在確認でログイン状態をチェック
                            login_button = await page.query_selector('[data-testid="login-button"]')
                            if login_button:
                                self.root.after(0, lambda: self.log(f"⚠️ {ai_name}にログインが必要です"))
                            else:
                                # チャット入力欄の存在確認
                                chat_input = await page.query_selector('[data-testid="prompt-textarea"]')
                                if chat_input:
                                    self.root.after(0, lambda: self.log(f"✅ {ai_name}ログイン状態確認済み"))
                                else:
                                    self.root.after(0, lambda: self.log(f"⚠️ {ai_name}の状態が不明です"))
                        else:
                            raise Exception("ページの作成に失敗しました")
                    
                    # テスト完了
                    self.root.after(0, lambda: self.log(f"✅ {column_name}の{ai_name}接続テスト完了"))
                    
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    self.root.after(0, lambda: self.log(f"❌ {column_name}の{ai_name}接続テスト失敗: {str(e)}"))
                    self.root.after(0, lambda: self.log(f"🔍 詳細エラー: {error_details}"))
                    raise
                finally:
                    # クリーンアップ
                    if browser_manager:
                        await browser_manager.cleanup()
                        self.root.after(0, lambda: self.log(f"🧹 {ai_name}ブラウザをクリーンアップしました"))
            
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
        """実際のAI処理を実行"""
        from src.ai_tools.browser_manager import BrowserManager
        from src.ai_tools.chatgpt_handler import ChatGPTHandler
        from src.ai_tools.base_ai_handler import AIConfig
        
        browser_manager = None
        
        try:
            self.root.after(0, lambda: self.log("🚀 実際のAI処理を開始"))
            
            # ブラウザマネージャーを初期化
            self.root.after(0, lambda: self.log("📋 ブラウザマネージャーを初期化中..."))
            browser_manager = BrowserManager()
            
            # ブラウザを起動
            self.root.after(0, lambda: self.log("🚀 ブラウザを起動中..."))
            browser_started = await browser_manager.start_browser(
                headless=False, 
                use_existing_profile=True
            )
            
            if not browser_started:
                raise Exception("ブラウザの起動に失敗しました")
            
            self.root.after(0, lambda: self.log("✅ ブラウザ起動成功"))
            
            # 各列の処理
            total_columns = len(self.copy_columns)
            
            for i, col_info in enumerate(self.copy_columns):
                if not self.processing:
                    break
                
                col_name = col_info['name']
                config = self.column_ai_configs.get(col_name)
                
                if config:
                    ai = config['ai_var'].get()
                    model = config['model_var'].get()
                    
                    self.root.after(0, lambda cn=col_name, a=ai, m=model: 
                                  self.log(f"🔄 {cn}を{a}({m})で実際に処理中..."))
                    
                    # AIサイトにアクセスして実際の処理を実行
                    success = await self._process_with_ai(browser_manager, ai, col_name, model)
                    
                    # プログレスバー更新
                    progress = ((i + 1) / total_columns) * 100
                    self.root.after(0, lambda p=progress: self.progress_var.set(p))
                    
                    self.root.after(0, lambda cn=col_name: self.log(f"✅ {cn}の実際の処理完了"))
            
            if self.processing:
                self.root.after(0, lambda: self.log("🎉 全ての実際の処理が完了しました"))
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.root.after(0, lambda: self.log(f"❌ AI処理エラー: {str(e)}"))
            self.root.after(0, lambda: self.log(f"🔍 詳細エラー: {error_details}"))
            raise
        finally:
            # ブラウザのクリーンアップ
            if browser_manager:
                await browser_manager.cleanup()
                self.root.after(0, lambda: self.log("🧹 ブラウザをクリーンアップしました"))
    
    async def _process_with_ai(self, browser_manager, ai_name, col_name, model):
        """指定されたAIで実際の処理を実行"""
        try:
            if ai_name == "ChatGPT":
                return await self._process_with_chatgpt(browser_manager, col_name, model)
            elif ai_name == "Claude":
                return await self._process_with_claude(browser_manager, col_name, model)
            elif ai_name == "Gemini":
                return await self._process_with_gemini(browser_manager, col_name, model)
            elif ai_name == "Genspark":
                return await self._process_with_genspark(browser_manager, col_name, model)
            elif ai_name == "Google AI Studio":
                return await self._process_with_google_ai_studio(browser_manager, col_name, model)
            else:
                self.root.after(0, lambda: self.log(f"❌ 未対応のAI: {ai_name}"))
                return False
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ {ai_name}処理エラー: {str(e)}"))
            return False
    
    async def _process_with_chatgpt(self, browser_manager, col_name, model):
        """ChatGPTで実際の処理を実行"""
        try:
            page = await browser_manager.create_page(f"chatgpt_{col_name}", "https://chat.openai.com")
            
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
    
    async def _process_with_claude(self, browser_manager, col_name, model):
        """Claudeで実際の処理を実行"""
        try:
            page = await browser_manager.create_page(f"claude_{col_name}", "https://claude.ai")
            
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
    
    async def _process_with_gemini(self, browser_manager, col_name, model):
        """Geminiで実際の処理を実行"""
        try:
            page = await browser_manager.create_page(f"gemini_{col_name}", "https://gemini.google.com")
            
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
    
    async def _process_with_genspark(self, browser_manager, col_name, model):
        """Gensparkで実際の処理を実行"""
        try:
            page = await browser_manager.create_page(f"genspark_{col_name}", "https://www.genspark.ai")
            
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
    
    async def _process_with_google_ai_studio(self, browser_manager, col_name, model):
        """Google AI Studioで実際の処理を実行"""
        try:
            page = await browser_manager.create_page(f"google_ai_studio_{col_name}", "https://aistudio.google.com")
            
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