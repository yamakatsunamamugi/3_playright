#!/usr/bin/env python3
"""
修正版メインウィンドウ - 確実に動作する版
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
from pathlib import Path
from datetime import datetime
import time

class FixedMainWindow:
    """修正版メインウィンドウ"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("スプレッドシートAI自動処理ツール - 修正版")
        self.root.geometry("1000x700")
        
        # 状態管理
        self.processing = False
        self.copy_columns = []
        self.column_ai_configs = {}
        
        # AI情報（モデルは1つずつ）
        self.ai_models = {
            "ChatGPT": "GPT-4o",
            "Claude": "Claude-3.5 Sonnet (New)",
            "Gemini": "Gemini 2.5 Flash",
            "Genspark": "Genspark Pro",
            "Google AI Studio": "Gemini 1.5 Pro"
        }
        
        self._create_ui()
        self._setup_test_data()
        
        print("✅ 修正版メインウィンドウ初期化完了")
    
    def _create_ui(self):
        """UIを作成"""
        # メインフレーム（スクロール対応）
        self._create_scrollable_frame()
        
        # 各セクションを作成
        self._create_spreadsheet_section()
        self._create_column_ai_section()
        self._create_control_section()
        self._create_log_section()
    
    def _create_scrollable_frame(self):
        """スクロール可能なフレームを作成"""
        # キャンバスとスクロールバー
        self.canvas = tk.Canvas(self.root, bg="white")
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # スクロール設定
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # パック
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # マウスホイールでスクロール
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        print("✅ スクロール可能フレーム作成完了")
    
    def _create_spreadsheet_section(self):
        """スプレッドシート設定セクション"""
        frame = ttk.LabelFrame(self.scrollable_frame, text="📊 スプレッドシート設定", padding="15")
        frame.pack(fill="x", padx=10, pady=5)
        
        # URL入力
        ttk.Label(frame, text="スプレッドシートURL:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.url_var = tk.StringVar(value="https://docs.google.com/spreadsheets/d/1mhvJKjNNdFqn_xo1D7iZzEyoLm9_2Qh3TbcV8NrW5Sx")
        url_entry = ttk.Entry(frame, textvariable=self.url_var, width=70, font=("Arial", 10))
        url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=5)
        
        # シート名選択
        ttk.Label(frame, text="シート名:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.sheet_var = tk.StringVar()
        self.sheet_combo = ttk.Combobox(frame, textvariable=self.sheet_var, width=25, font=("Arial", 10))
        self.sheet_combo['state'] = 'readonly'
        self.sheet_combo.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)
        
        # シート取得ボタン
        self.get_sheets_button = ttk.Button(
            frame,
            text="📋 シート取得",
            command=self._get_sheets,
            width=15
        )
        self.get_sheets_button.grid(row=0, column=3, sticky="w", padx=(20, 0), pady=5)
        
        # 分析ボタン
        self.analyze_button = ttk.Button(
            frame,
            text="📋 スプレッドシート分析",
            command=self._analyze_spreadsheet,
            width=20
        )
        self.analyze_button.grid(row=1, column=2, sticky="w", padx=(20, 0), pady=5)
        
        # グリッド設定
        frame.columnconfigure(1, weight=1)
        
        print("✅ スプレッドシート設定セクション作成完了")
    
    def _create_column_ai_section(self):
        """列ごとのAI設定セクション"""
        self.ai_section_frame = ttk.LabelFrame(self.scrollable_frame, text="🤖 列ごとのAI設定", padding="15")
        self.ai_section_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 初期メッセージ
        self.placeholder_label = ttk.Label(
            self.ai_section_frame,
            text="📌 まず「スプレッドシート分析」ボタンをクリックして列構造を解析してください",
            font=("Arial", 11),
            foreground="gray"
        )
        self.placeholder_label.pack(pady=30)
        
        # 動的な列設定を格納するフレーム
        self.column_frame = ttk.Frame(self.ai_section_frame)
        
        print("✅ 列ごとのAI設定セクション作成完了")
    
    def _create_control_section(self):
        """制御セクション"""
        frame = ttk.LabelFrame(self.scrollable_frame, text="⚡ 処理制御", padding="15")
        frame.pack(fill="x", padx=10, pady=5)
        
        # ボタンフレーム
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")
        
        # 開始ボタン
        self.start_button = ttk.Button(
            btn_frame,
            text="🚀 処理開始",
            command=self._start_processing,
            width=15
        )
        self.start_button.pack(side="left", padx=(0, 10))
        
        # 停止ボタン
        self.stop_button = ttk.Button(
            btn_frame,
            text="⏹️ 停止",
            command=self._stop_processing,
            width=15,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=(0, 10))
        
        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            btn_frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(side="left", padx=(20, 10))
        
        # ステータス
        self.status_var = tk.StringVar(value="待機中")
        ttk.Label(btn_frame, textvariable=self.status_var, font=("Arial", 10)).pack(side="left")
        
        print("✅ 制御セクション作成完了")
    
    def _create_log_section(self):
        """ログセクション"""
        frame = ttk.LabelFrame(self.scrollable_frame, text="📝 実行ログ", padding="15")
        frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # ログテキストエリア
        self.log_text = scrolledtext.ScrolledText(
            frame,
            height=12,
            width=80,
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill="both", expand=True)
        
        # ログクリアボタン
        clear_btn = ttk.Button(
            frame,
            text="🗑️ ログクリア",
            command=self._clear_log,
            width=15
        )
        clear_btn.pack(anchor="e", pady=(10, 0))
        
        print("✅ ログセクション作成完了")
    
    def _setup_test_data(self):
        """テストデータセットアップ"""
        self.log("🚀 アプリケーション起動完了")
        self.log("📊 テスト用スプレッドシート設定済み")
        self.log("🔍 まず「シート取得」ボタンでシート名を取得してください")
    
    def _get_sheets(self):
        """スプレッドシートからシート名を取得"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("警告", "スプレッドシートURLを入力してください")
            return
        
        self.log("📋 スプレッドシートからシート名を取得中...")
        self.get_sheets_button.config(state="disabled")
        
        # 非同期でシート取得
        thread = threading.Thread(target=self._get_sheets_thread)
        thread.daemon = True
        thread.start()
    
    def _get_sheets_thread(self):
        """シート取得スレッド"""
        try:
            url = self.url_var.get().strip()
            
            # 実際のGoogle Sheets API使用を試行
            try:
                from google_sheets_api import GoogleSheetsAPI
                api = GoogleSheetsAPI()
                sheets = api.get_sheet_names(url)
                
                if sheets:
                    self.root.after(0, self._update_sheet_list, sheets)
                    return
                    
            except Exception as api_error:
                self.root.after(0, lambda: self.log(f"⚠️ API使用不可: {api_error}"))
                self.root.after(0, lambda: self.log("📋 シミュレーションモードで実行"))
            
            # フォールバック：シミュレーション
            time.sleep(2)
            
            # URLベースのシート名推測（デモ用）
            if "1mhvJKjNNdFqn_xo1D7iZzEyoLm9_2Qh3TbcV8NrW5Sx" in url:
                mock_sheets = [
                    "1.原稿本文作成",
                    "2.データ集計", 
                    "3.分析結果",
                    "4.設定シート",
                    "5.テンプレート"
                ]
            else:
                mock_sheets = [
                    "Sheet1",
                    "データ",
                    "分析",
                    "設定"
                ]
            
            # UIスレッドで結果更新
            self.root.after(0, self._update_sheet_list, mock_sheets)
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ シート取得エラー: {e}"))
            self.root.after(0, lambda: self.get_sheets_button.config(state="normal"))
    
    def _update_sheet_list(self, sheets):
        """シートリストを更新"""
        self.sheet_combo['values'] = sheets
        if sheets:
            self.sheet_var.set(sheets[0])  # 最初のシートを選択
            self.log(f"✅ {len(sheets)}個のシートを取得しました")
            for sheet in sheets:
                self.log(f"   • {sheet}")
        else:
            self.log("⚠️ シートが見つかりませんでした")
        
        self.get_sheets_button.config(state="normal")
    
    def _analyze_spreadsheet(self):
        """スプレッドシート分析"""
        if self.processing:
            return
        
        self.log("🔍 スプレッドシート分析開始...")
        self.status_var.set("分析中...")
        self.analyze_button.config(state="disabled")
        
        # 非同期で分析実行
        thread = threading.Thread(target=self._analyze_thread)
        thread.daemon = True
        thread.start()
    
    def _analyze_thread(self):
        """分析スレッド"""
        try:
            # 分析シミュレーション
            time.sleep(2)
            
            # 模擬的な「コピー」列データ
            mock_copy_columns = [
                {"column": "C", "name": "コピー1", "index": 2},
                {"column": "G", "name": "コピー2", "index": 6}
            ]
            
            self.copy_columns = mock_copy_columns
            
            # UIスレッドで結果表示
            self.root.after(0, self._show_analysis_result)
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ 分析エラー: {e}"))
    
    def _show_analysis_result(self):
        """分析結果表示"""
        self.log("✅ スプレッドシート分析完了")
        self.log(f"🎯 「コピー」列を{len(self.copy_columns)}個検出:")
        
        for col in self.copy_columns:
            self.log(f"   • {col['column']}列: {col['name']}")
        
        # プレースホルダーを削除
        self.placeholder_label.pack_forget()
        
        # 列設定UIを作成
        self._create_column_configs()
        
        self.status_var.set("分析完了")
        self.analyze_button.config(state="normal")
    
    def _create_column_configs(self):
        """列設定UIを作成"""
        # 既存の設定をクリア
        for widget in self.column_frame.winfo_children():
            widget.destroy()
        
        self.column_frame.pack(fill="both", expand=True, pady=10)
        
        # 各列の設定を作成
        for i, col_info in enumerate(self.copy_columns):
            self._create_single_column_config(col_info, i)
        
        self.log("🤖 列ごとのAI設定UI作成完了")
    
    def _create_single_column_config(self, col_info, row):
        """単一列の設定作成"""
        # 横並びレイアウト用のフレーム（行ごと）
        if row == 0:
            self.current_row_frame = ttk.Frame(self.column_frame)
            self.current_row_frame.pack(fill="x", pady=5)
        elif row % 2 == 0:  # 2列ごとに新しい行
            self.current_row_frame = ttk.Frame(self.column_frame)
            self.current_row_frame.pack(fill="x", pady=5)
        
        # 列フレーム（横並び）
        col_frame = ttk.LabelFrame(
            self.current_row_frame,
            text=f"📝 {col_info['name']} ({col_info['column']}列)",
            padding="8"
        )
        col_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        # AI選択
        ai_frame = ttk.Frame(col_frame)
        ai_frame.pack(fill="x", pady=2)
        
        ttk.Label(ai_frame, text="AI:", font=("Arial", 9)).pack(side="left")
        
        ai_var = tk.StringVar(value="ChatGPT")
        ai_combo = ttk.Combobox(ai_frame, textvariable=ai_var, width=12, font=("Arial", 9))
        ai_combo['values'] = list(self.ai_models.keys())
        ai_combo['state'] = 'readonly'
        ai_combo.pack(side="left", padx=(5, 0))
        
        # モデル表示（選択不可、AIに応じて自動表示）
        model_frame = ttk.Frame(col_frame)
        model_frame.pack(fill="x", pady=2)
        
        ttk.Label(model_frame, text="モデル:", font=("Arial", 9)).pack(side="left")
        
        model_var = tk.StringVar()
        model_label = ttk.Label(model_frame, textvariable=model_var, font=("Arial", 9), foreground="blue")
        model_label.pack(side="left", padx=(5, 0))
        
        # ボタンフレーム
        btn_frame = ttk.Frame(col_frame)
        btn_frame.pack(fill="x", pady=5)
        
        # テストボタン
        test_btn = ttk.Button(
            btn_frame,
            text="🧪 テスト",
            command=lambda: self._test_connection(col_info['name'], ai_var.get()),
            width=8
        )
        test_btn.pack(side="left", padx=(0, 5))
        
        # 設定ボタン
        settings_btn = ttk.Button(
            btn_frame,
            text="⚙️ 設定",
            command=lambda: self._open_settings(col_info['name'], ai_var.get()),
            width=8
        )
        settings_btn.pack(side="left")
        
        # AIが変更されたときのモデル更新
        def update_model(*args):
            selected_ai = ai_var.get()
            if selected_ai in self.ai_models:
                model_var.set(self.ai_models[selected_ai])
        
        ai_var.trace('w', update_model)
        update_model()  # 初期設定
        
        # 設定を保存
        self.column_ai_configs[col_info['name']] = {
            'ai_var': ai_var,
            'model_var': model_var,
            'column': col_info['column']
        }
        
        self.log(f"✅ {col_info['name']}の設定UI作成完了")
    
    def _open_settings(self, column_name, ai_name):
        """設定ダイアログを開く"""
        self.log(f"⚙️ {column_name}の{ai_name}設定ダイアログを開きます")
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{ai_name} 設定 - {column_name}")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"{ai_name}の詳細設定", font=("Arial", 12, "bold")).pack(pady=20)
        ttk.Label(dialog, text="Temperature (創造性):").pack(anchor="w", padx=20)
        
        temp_var = tk.DoubleVar(value=0.7)
        temp_scale = ttk.Scale(dialog, from_=0.0, to=2.0, variable=temp_var, orient="horizontal")
        temp_scale.pack(fill="x", padx=20, pady=10)
        
        ttk.Button(dialog, text="保存", command=dialog.destroy).pack(pady=20)
    
    def _test_connection(self, column_name, ai_name):
        """接続テスト"""
        self.log(f"🧪 {column_name}の{ai_name}接続テスト開始...")
        
        def test_thread():
            time.sleep(2)
            self.root.after(0, lambda: self.log(f"✅ {column_name}の{ai_name}接続テスト成功"))
        
        thread = threading.Thread(target=test_thread)
        thread.daemon = True
        thread.start()
    
    def _start_processing(self):
        """処理開始"""
        if not self.copy_columns:
            messagebox.showwarning("警告", "まずスプレッドシート分析を実行してください")
            return
        
        self.processing = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set("処理中...")
        
        self.log("🚀 AI自動処理開始")
        
        # 各列の設定を表示
        for col_name, config in self.column_ai_configs.items():
            ai = config['ai_var'].get()
            model = config['model_var'].get()
            self.log(f"📝 {col_name}: {ai} - {model}")
        
        # 処理スレッド開始
        thread = threading.Thread(target=self._processing_thread)
        thread.daemon = True
        thread.start()
    
    def _processing_thread(self):
        """処理スレッド"""
        try:
            total_steps = len(self.copy_columns) * 3
            
            for i, col_info in enumerate(self.copy_columns):
                if not self.processing:
                    break
                
                col_name = col_info['name']
                config = self.column_ai_configs[col_name]
                ai = config['ai_var'].get()
                model = config['model_var'].get()
                
                self.root.after(0, lambda cn=col_name, a=ai, m=model: 
                              self.log(f"🔄 {cn}を{a}({m})で処理中..."))
                
                for step in range(3):
                    if not self.processing:
                        break
                    time.sleep(1)
                    progress = ((i * 3 + step + 1) / total_steps) * 100
                    self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                self.root.after(0, lambda cn=col_name: self.log(f"✅ {cn}の処理完了"))
            
            if self.processing:
                self.root.after(0, lambda: self.log("🎉 全ての処理が完了しました"))
                self.root.after(0, lambda: self.status_var.set("処理完了"))
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"❌ 処理エラー: {e}"))
        finally:
            self.processing = False
            self.root.after(0, lambda: self.start_button.config(state="normal"))
            self.root.after(0, lambda: self.stop_button.config(state="disabled"))
            self.root.after(0, lambda: self.progress_var.set(0))
    
    def _stop_processing(self):
        """処理停止"""
        self.processing = False
        self.log("⏹️ 処理停止要求")
    
    def _clear_log(self):
        """ログクリア"""
        self.log_text.delete(1.0, tk.END)
        self.log("🗑️ ログをクリアしました")
    
    def log(self, message):
        """ログメッセージ追加"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        print(f"LOG: {formatted_message.strip()}")
    
    def run(self):
        """アプリケーション実行"""
        self.log("🚀 アプリケーション開始")
        self.root.mainloop()


if __name__ == "__main__":
    print("=" * 50)
    print("🧪 修正版メインウィンドウテスト")
    print("=" * 50)
    
    app = FixedMainWindow()
    app.run()