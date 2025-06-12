#!/usr/bin/env python3
"""
AI自動化機能の統合テストスクリプト
GUI付きでモデル選択とChrome連携をテストします
"""
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import asyncio
import threading

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.gui.widgets.ai_config_widget import AIConfigPanel
from src.ai_tools.browser_manager import BrowserManager
from src.utils.logger import setup_logger, get_logger

# ログ設定
setup_logger("INFO", "logs/test_automation.log")
logger = get_logger(__name__)


class TestAutomationGUI:
    """AI自動化機能のテストGUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI自動化機能テスト")
        self.root.geometry("900x700")
        
        self.browser_manager = None
        self._create_widgets()
        
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="AI自動化機能テスト", font=("", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # AI設定パネル
        self.ai_config_panel = AIConfigPanel(main_frame)
        self.ai_config_panel.pack(fill=tk.X, pady=(0, 20))
        
        # Chrome設定フレーム
        chrome_frame = ttk.LabelFrame(main_frame, text="Chrome設定", padding="10")
        chrome_frame.pack(fill=tk.X, pady=(0, 20))
        
        # プロファイル選択
        profile_frame = ttk.Frame(chrome_frame)
        profile_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(profile_frame, text="Chromeプロファイル:").pack(side=tk.LEFT, padx=(0, 10))
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, 
                                         state="readonly", width=30)
        self.profile_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        self.refresh_profiles_btn = ttk.Button(profile_frame, text="プロファイル更新", 
                                              command=self._refresh_profiles)
        self.refresh_profiles_btn.pack(side=tk.LEFT)
        
        # Chrome起動ボタン
        self.launch_chrome_btn = ttk.Button(chrome_frame, text="Chrome起動（ログイン済みセッション）", 
                                           command=self._launch_chrome)
        self.launch_chrome_btn.pack()
        
        # 操作ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Button(button_frame, text="AI設定取得テスト", 
                  command=self._test_ai_configs).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="モデル情報表示", 
                  command=self._show_model_info).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Chrome統合テスト", 
                  command=self._test_chrome_integration).pack(side=tk.LEFT, padx=5)
        
        # ログ表示エリア
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 初期化
        self._refresh_profiles()
        self._log("テストアプリケーションを起動しました")
        
    def _refresh_profiles(self):
        """Chromeプロファイルリストを更新"""
        try:
            from src.ai_tools.browser_manager import BrowserManager
            temp_manager = BrowserManager()
            profiles = temp_manager.get_available_profiles_info()
            
            profile_names = []
            for profile in profiles:
                name = profile.get('name', profile.get('dir', 'Unknown'))
                dir_name = profile.get('dir', '')
                profile_names.append(f"{name} ({dir_name})")
            
            self.profile_combo['values'] = profile_names
            if profile_names:
                self.profile_combo.set(profile_names[0])
            
            self._log(f"✓ {len(profiles)}個のChromeプロファイルを検出しました")
            
        except Exception as e:
            self._log(f"✗ プロファイル取得エラー: {e}", "error")
            
    def _launch_chrome(self):
        """Chrome起動（ログイン済みセッション）"""
        if self.browser_manager:
            self._log("Chromeは既に起動しています", "warning")
            return
            
        def launch_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # プロファイルディレクトリを取得
                selected = self.profile_var.get()
                profile_dir = "Default"
                if "(" in selected and ")" in selected:
                    profile_dir = selected.split("(")[-1].rstrip(")")
                
                self._log(f"Chrome起動中... プロファイル: {profile_dir}")
                
                self.browser_manager = BrowserManager(use_profile=profile_dir)
                success = loop.run_until_complete(
                    self.browser_manager.start_browser(headless=False, 
                                                      use_existing_profile=True,
                                                      profile_dir=profile_dir)
                )
                
                if success:
                    self._log("✓ Chrome起動成功（ログイン済みセッション）", "success")
                    
                    # テストページを開く
                    page = loop.run_until_complete(
                        self.browser_manager.create_page("test", "https://www.google.com")
                    )
                    if page:
                        self._log("✓ テストページを開きました")
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
        
    def _test_ai_configs(self):
        """AI設定取得テスト"""
        self._log("\n【AI設定取得テスト】")
        configs = self.ai_config_panel.get_all_configs()
        
        for ai_name, config in configs.items():
            enabled = config.get('enabled', False)
            model = config.get('model', 'None')
            status = "有効" if enabled else "無効"
            self._log(f"  {ai_name}: {status}, モデル: {model}")
            
    def _show_model_info(self):
        """モデル情報を表示"""
        self._log("\n【モデル情報表示】")
        
        # 選択されているAIのモデル情報を表示
        configs = self.ai_config_panel.get_all_configs()
        enabled_ais = [name for name, config in configs.items() if config.get('enabled', False)]
        
        if not enabled_ais:
            self._log("有効なAIがありません", "warning")
            return
            
        for ai_name in enabled_ais:
            widget = self.ai_config_panel.ai_widgets.get(ai_name)
            if widget and widget.model_infos:
                self._log(f"\n{ai_name}のモデル:")
                for model in widget.model_infos:
                    self._log(f"  - {model.name}: {model.description}")
                    
    def _test_chrome_integration(self):
        """Chrome統合テスト"""
        if not self.browser_manager:
            self._log("Chromeが起動していません", "warning")
            return
            
        self._log("\n【Chrome統合テスト】")
        
        def test_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # ChatGPTのログイン状態をチェック
                self._log("ChatGPTのログイン状態を確認中...")
                is_logged_in = loop.run_until_complete(
                    self.browser_manager.check_login_status(
                        "https://chat.openai.com",
                        "nav"  # ナビゲーションバーの存在でログイン判定
                    )
                )
                
                if is_logged_in:
                    self._log("✓ ChatGPTにログイン済みです", "success")
                else:
                    self._log("✗ ChatGPTにログインしていません", "warning")
                    
                # スクリーンショットを撮影
                filename = loop.run_until_complete(
                    self.browser_manager.take_screenshot("test", "test_screenshot.png")
                )
                if filename:
                    self._log(f"✓ スクリーンショット保存: {filename}")
                    
            except Exception as e:
                self._log(f"✗ テストエラー: {e}", "error")
            finally:
                loop.close()
        
        thread = threading.Thread(target=test_async, daemon=True)
        thread.start()
        
    def _log(self, message: str, level: str = "info"):
        """ログメッセージを表示"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # レベルに応じて色を変更
        if level == "error":
            tag = "error"
            prefix = "✗"
        elif level == "warning":
            tag = "warning"
            prefix = "⚠"
        elif level == "success":
            tag = "success"
            prefix = "✓"
        else:
            tag = "info"
            prefix = "ℹ"
            
        self.log_text.insert(tk.END, f"[{timestamp}] {prefix} {message}\n")
        
        # タグの設定
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("info", foreground="black")
        
        # 最後の行にタグを適用
        line_start = self.log_text.index("end-2c linestart")
        line_end = self.log_text.index("end-2c lineend")
        self.log_text.tag_add(tag, line_start, line_end)
        
        # 自動スクロール
        self.log_text.see(tk.END)
        
    def run(self):
        """アプリケーションを実行"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
        
    def _on_close(self):
        """ウィンドウ終了時の処理"""
        if self.browser_manager:
            self._log("Chromeをクリーンアップ中...")
            
            def cleanup_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.browser_manager.cleanup())
                except:
                    pass
                finally:
                    loop.close()
            
            thread = threading.Thread(target=cleanup_async)
            thread.start()
            thread.join(timeout=5)
            
        self.root.destroy()


if __name__ == "__main__":
    from datetime import datetime
    
    print("=" * 60)
    print("AI自動化機能統合テスト")
    print("=" * 60)
    print()
    print("このテストアプリケーションでは以下の機能をテストできます：")
    print("1. 各AIツールのモデル選択機能")
    print("2. Chrome統合（ログイン済みセッション利用）")
    print("3. AI設定の取得と表示")
    print()
    print("テストGUIを起動しています...")
    
    app = TestAutomationGUI()
    app.run()