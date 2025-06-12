#!/usr/bin/env python3
"""
統合テストスクリプト
スプレッドシート処理とAI操作の統合をテスト
"""
import sys
import asyncio
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from datetime import datetime

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logger, get_logger
from src.sheets.client import GoogleSheetsClient
from src.ai_tools.browser_manager import BrowserManager

# ログ設定
setup_logger("INFO", "logs/test_integration.log")
logger = get_logger(__name__)


class IntegrationTestGUI:
    """統合テスト用GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("統合テスト - スプレッドシートAI自動処理")
        self.root.geometry("1000x700")
        
        self.browser_manager = None
        self.sheet_client = GoogleSheetsClient()
        
        self._create_widgets()
        
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="スプレッドシートAI自動処理 - 統合テスト", 
                               font=("", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # テストシート作成セクション
        sheet_frame = ttk.LabelFrame(main_frame, text="1. テストシート作成", padding="10")
        sheet_frame.pack(fill=tk.X, pady=(0, 20))
        
        # スプレッドシートURL入力
        url_frame = ttk.Frame(sheet_frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(url_frame, text="スプレッドシートURL:").pack(side=tk.LEFT, padx=(0, 10))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=60)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # ボタン
        button_frame = ttk.Frame(sheet_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Google認証", 
                  command=self._authenticate_google).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="テストデータ作成", 
                  command=self._create_test_data).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="シート内容確認", 
                  command=self._check_sheet_content).pack(side=tk.LEFT, padx=5)
        
        # Chrome起動セクション
        chrome_frame = ttk.LabelFrame(main_frame, text="2. Chrome起動", padding="10")
        chrome_frame.pack(fill=tk.X, pady=(0, 20))
        
        # プロファイル選択
        profile_frame = ttk.Frame(chrome_frame)
        profile_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(profile_frame, text="Chromeプロファイル:").pack(side=tk.LEFT, padx=(0, 10))
        self.profile_var = tk.StringVar(value="Default")
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var,
                                         values=["Default"], state="readonly", width=30)
        self.profile_combo.pack(side=tk.LEFT)
        
        ttk.Button(chrome_frame, text="Chrome起動（ログイン済みセッション）",
                  command=self._launch_chrome).pack(pady=10)
        
        # AI操作テストセクション
        ai_frame = ttk.LabelFrame(main_frame, text="3. AI操作テスト", padding="10")
        ai_frame.pack(fill=tk.X, pady=(0, 20))
        
        # AIツール選択
        ai_select_frame = ttk.Frame(ai_frame)
        ai_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(ai_select_frame, text="AIツール:").pack(side=tk.LEFT, padx=(0, 10))
        self.ai_var = tk.StringVar(value="ChatGPT")
        self.ai_combo = ttk.Combobox(ai_select_frame, textvariable=self.ai_var,
                                    values=["ChatGPT", "Claude", "Gemini", "Genspark", "Google AI Studio"],
                                    state="readonly", width=20)
        self.ai_combo.pack(side=tk.LEFT)
        
        # テストプロンプト
        prompt_frame = ttk.Frame(ai_frame)
        prompt_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(prompt_frame, text="テストプロンプト:").pack(side=tk.LEFT, padx=(0, 10))
        self.prompt_var = tk.StringVar(value="こんにちは！今日の日付を教えてください。")
        self.prompt_entry = ttk.Entry(prompt_frame, textvariable=self.prompt_var, width=60)
        self.prompt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(ai_frame, text="AI操作テスト実行",
                  command=self._test_ai_operation).pack(pady=10)
        
        # 統合テストセクション
        integration_frame = ttk.LabelFrame(main_frame, text="4. 統合テスト", padding="10")
        integration_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Button(integration_frame, text="統合テスト実行（拡張版GUI起動）",
                  command=self._run_integration_test,
                  style="Accent.TButton").pack(pady=10)
        
        # ログ表示
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 初期メッセージ
        self._log("統合テストツールを起動しました")
        self._log("1. まずGoogle認証を行ってください")
        self._log("2. テストデータを作成してスプレッドシートを準備します")
        self._log("3. Chromeを起動して各AIにログインしてください")
        self._log("4. 最後に統合テストを実行します")
        
    def _log(self, message: str, level: str = "info"):
        """ログメッセージを表示"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # タグに応じて色を設定
        tag_config = {
            "info": ("black", "ℹ"),
            "success": ("green", "✓"),
            "warning": ("orange", "⚠"),
            "error": ("red", "✗")
        }
        
        color, prefix = tag_config.get(level, ("black", "ℹ"))
        
        self.log_text.insert(tk.END, f"[{timestamp}] {prefix} {message}\n")
        self.log_text.tag_config(level, foreground=color)
        
        # 最後の行にタグを適用
        line_start = self.log_text.index("end-2c linestart")
        line_end = self.log_text.index("end-2c lineend")
        self.log_text.tag_add(level, line_start, line_end)
        
        # 自動スクロール
        self.log_text.see(tk.END)
        
    def _authenticate_google(self):
        """Google認証"""
        try:
            if self.sheet_client.authenticate():
                self._log("✓ Google Sheets認証成功", "success")
            else:
                self._log("✗ Google Sheets認証失敗", "error")
        except Exception as e:
            self._log(f"✗ 認証エラー: {e}", "error")
            
    def _create_test_data(self):
        """テストデータを作成"""
        url = self.url_var.get()
        if not url:
            self._log("スプレッドシートURLを入力してください", "warning")
            return
            
        try:
            # シートIDを抽出
            sheet_id = self._extract_sheet_id(url)
            sheet_name = "テストシート"
            
            # テストデータ
            test_data = [
                ["", "", "", "", ""],  # 1行目（空白）
                ["", "", "", "", ""],  # 2行目（空白）
                ["", "", "", "", ""],  # 3行目（空白）
                ["", "", "", "", ""],  # 4行目（空白）
                ["作業指示行", "処理", "エラー", "コピー", "貼り付け"],  # 5行目（ヘッダー）
                ["1", "未処理", "", "今日の天気は？", ""],
                ["2", "未処理", "", "明日の予定を教えて", ""],
                ["3", "未処理", "", "おすすめのレシピは？", ""],
                ["", "", "", "", ""]  # 空白行（終了マーカー）
            ]
            
            # データを書き込み
            range_name = f"{sheet_name}!A1:E9"
            success = self.sheet_client.write_range(sheet_id, range_name, test_data)
            
            if success:
                self._log(f"✓ テストデータを作成しました（シート: {sheet_name}）", "success")
                self._log("  - 作業指示行: 5行目", "info")
                self._log("  - コピー列: D列", "info")
                self._log("  - 処理対象: 3行", "info")
            else:
                self._log("✗ テストデータの作成に失敗しました", "error")
                
        except Exception as e:
            self._log(f"✗ エラー: {e}", "error")
            
    def _check_sheet_content(self):
        """シート内容を確認"""
        url = self.url_var.get()
        if not url:
            self._log("スプレッドシートURLを入力してください", "warning")
            return
            
        try:
            sheet_id = self._extract_sheet_id(url)
            sheet_name = "テストシート"
            
            # データを読み込み
            sheet_data = self.sheet_client.get_sheet_data(sheet_id, sheet_name)
            
            if sheet_data:
                self._log(f"✓ シートデータを読み込みました（{len(sheet_data)}行）", "success")
                
                # 作業指示行を検出
                work_row = -1
                for i, row in enumerate(sheet_data):
                    if row and str(row[0]).strip() == "作業指示行":
                        work_row = i
                        break
                        
                if work_row >= 0:
                    self._log(f"  - 作業指示行: {work_row + 1}行目", "info")
                    
                    # コピー列を検出
                    header_row = sheet_data[work_row]
                    copy_cols = []
                    for j, cell in enumerate(header_row):
                        if str(cell).strip() == "コピー":
                            copy_cols.append(j)
                            
                    if copy_cols:
                        self._log(f"  - コピー列: {[chr(65 + c) for c in copy_cols]}", "info")
                        
                        # 処理対象行をカウント
                        process_count = 0
                        for i in range(work_row + 1, len(sheet_data)):
                            if i < len(sheet_data) and sheet_data[i] and sheet_data[i][0]:
                                try:
                                    int(str(sheet_data[i][0]))
                                    process_count += 1
                                except:
                                    break
                                    
                        self._log(f"  - 処理対象行: {process_count}行", "info")
                    else:
                        self._log("  - コピー列が見つかりません", "warning")
                else:
                    self._log("  - 作業指示行が見つかりません", "warning")
            else:
                self._log("✗ シートデータの読み込みに失敗しました", "error")
                
        except Exception as e:
            self._log(f"✗ エラー: {e}", "error")
            
    def _launch_chrome(self):
        """Chrome起動"""
        if self.browser_manager:
            self._log("Chromeは既に起動しています", "warning")
            return
            
        def launch_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                self._log("Chrome起動中...")
                self.browser_manager = BrowserManager(use_profile=self.profile_var.get())
                
                success = loop.run_until_complete(
                    self.browser_manager.start_browser(
                        headless=False,
                        use_existing_profile=True
                    )
                )
                
                if success:
                    self._log("✓ Chrome起動成功（ログイン済みセッション）", "success")
                    self._log("各AIツールにアクセスしてログインしてください", "info")
                    
                    # 各AIのURLを開く
                    ai_urls = {
                        "ChatGPT": "https://chat.openai.com",
                        "Claude": "https://claude.ai",
                        "Gemini": "https://gemini.google.com",
                        "Genspark": "https://www.genspark.ai",
                        "Google AI Studio": "https://makersuite.google.com"
                    }
                    
                    for ai_name, url in ai_urls.items():
                        page = loop.run_until_complete(
                            self.browser_manager.create_page(ai_name, url)
                        )
                        if page:
                            self._log(f"  - {ai_name}のページを開きました", "info")
                            
                else:
                    self._log("✗ Chrome起動失敗", "error")
                    self.browser_manager = None
                    
            except Exception as e:
                self._log(f"✗ Chrome起動エラー: {e}", "error")
                import traceback
                self._log(traceback.format_exc(), "error")
            finally:
                loop.close()
                
        thread = threading.Thread(target=launch_async, daemon=True)
        thread.start()
        
    def _test_ai_operation(self):
        """AI操作テスト"""
        if not self.browser_manager:
            self._log("先にChromeを起動してください", "warning")
            return
            
        ai_tool = self.ai_var.get()
        prompt = self.prompt_var.get()
        
        def test_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                self._log(f"{ai_tool}でテストを実行中...")
                
                # AIハンドラーを作成
                handler_class = {
                    "ChatGPT": "src.ai_tools.chatgpt_handler.ChatGPTHandler",
                    "Claude": "src.ai_tools.claude.ClaudeHandler",
                    "Gemini": "src.ai_tools.gemini.GeminiHandler",
                    "Genspark": "src.ai_tools.genspark.GensparkHandler",
                    "Google AI Studio": "src.ai_tools.google_ai_studio.GoogleAIStudioHandler"
                }.get(ai_tool)
                
                if handler_class:
                    # 動的インポート
                    module_name, class_name = handler_class.rsplit('.', 1)
                    module = __import__(module_name, fromlist=[class_name])
                    handler_cls = getattr(module, class_name)
                    
                    # ハンドラーのインスタンスを作成
                    handler = handler_cls(self.browser_manager)
                    
                    # ログイン状態を確認
                    is_logged_in = loop.run_until_complete(handler.is_logged_in())
                    if is_logged_in:
                        self._log(f"✓ {ai_tool}にログイン済み", "success")
                        
                        # プロンプトを送信
                        self._log(f"プロンプト送信中: {prompt}")
                        response = loop.run_until_complete(
                            handler.send_prompt_async(prompt, timeout=60)
                        )
                        
                        self._log(f"✓ 応答を受信しました", "success")
                        self._log(f"応答: {response[:200]}..." if len(response) > 200 else f"応答: {response}", "info")
                    else:
                        self._log(f"✗ {ai_tool}にログインしていません", "error")
                        self._log("ブラウザでログインしてから再試行してください", "warning")
                        
            except Exception as e:
                self._log(f"✗ テストエラー: {e}", "error")
                import traceback
                self._log(traceback.format_exc(), "error")
            finally:
                loop.close()
                
        thread = threading.Thread(target=test_async, daemon=True)
        thread.start()
        
    def _run_integration_test(self):
        """統合テスト実行"""
        url = self.url_var.get()
        if not url:
            self._log("スプレッドシートURLを入力してください", "warning")
            return
            
        # 拡張版GUIを起動
        self._log("拡張版GUIを起動します...", "info")
        
        import subprocess
        try:
            # 新しいプロセスで拡張版を起動
            subprocess.Popen([sys.executable, "main.py", "--enhanced"])
            self._log("✓ 拡張版GUIを起動しました", "success")
            self._log("拡張版GUIで以下の手順を実行してください:", "info")
            self._log("1. スプレッドシートURLを入力", "info")
            self._log("2. AIツールを有効化", "info")
            self._log("3. 「列を検出」をクリック", "info")
            self._log("4. 各コピー列で使用するAIを選択", "info")
            self._log("5. 「処理開始」をクリック", "info")
            
        except Exception as e:
            self._log(f"✗ 起動エラー: {e}", "error")
            
    def _extract_sheet_id(self, url: str) -> str:
        """スプレッドシートURLからIDを抽出"""
        if '/spreadsheets/d/' in url:
            start = url.find('/spreadsheets/d/') + len('/spreadsheets/d/')
            end = url.find('/', start)
            if end == -1:
                end = url.find('#', start) if '#' in url[start:] else len(url)
            return url[start:end]
        raise ValueError("無効なスプレッドシートURLです")
        
    def run(self):
        """アプリケーションを実行"""
        # ウィンドウ終了時の処理
        def on_close():
            if self.browser_manager:
                def cleanup():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self.browser_manager.cleanup())
                    except:
                        pass
                    finally:
                        loop.close()
                        
                thread = threading.Thread(target=cleanup)
                thread.start()
                thread.join(timeout=5)
                
            self.root.destroy()
            
        self.root.protocol("WM_DELETE_WINDOW", on_close)
        self.root.mainloop()


if __name__ == "__main__":
    print("=" * 60)
    print("スプレッドシートAI自動処理 - 統合テスト")
    print("=" * 60)
    print()
    print("このテストツールでは以下の機能をテストできます：")
    print("1. Googleスプレッドシートの認証とデータ操作")
    print("2. Chrome統合（ログイン済みセッション利用）")
    print("3. 各AIツールの操作テスト")
    print("4. 統合動作の確認")
    print()
    
    app = IntegrationTestGUI()
    app.run()