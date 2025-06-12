"""
AI自動化統合テストスクリプト

GUI、モデル動的取得、Chrome統合の全機能をテストします。
"""

import asyncio
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from pathlib import Path

from src.gui.widgets.ai_config_widget import AIConfigPanel
from src.ai_tools.browser_manager import BrowserManager
from src.utils.logger import get_logger

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = get_logger(__name__)


class AIAutomationTestGUI:
    """AI自動化機能の統合テストGUI"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("AI自動化機能 統合テスト")
        self.root.geometry("900x700")
        
        self.browser_manager = None
        self.cache_dir = Path.home() / ".ai_tools_cache"
        
        self._create_widgets()
        self._center_window()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(
            main_frame, 
            text="AI自動化機能 統合テスト", 
            font=("", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # 説明
        desc_frame = ttk.LabelFrame(main_frame, text="テスト内容", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 20))
        
        desc_text = """このテストでは以下の機能を確認します：
1. 各AIサービスから最新モデル情報を動的に取得
2. 取得したモデル情報をGUIに反映
3. 既存のChromeプロファイルを使用したブラウザ起動
4. 各AIサービスへのアクセスとログイン状態の確認"""
        
        ttk.Label(desc_frame, text=desc_text, justify=tk.LEFT).pack()
        
        # AI設定パネル
        self.ai_config_panel = AIConfigPanel(main_frame, cache_dir=self.cache_dir)
        self.ai_config_panel.frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Chromeプロファイル選択
        chrome_frame = ttk.LabelFrame(main_frame, text="Chromeプロファイル", padding="10")
        chrome_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.profile_var = tk.StringVar(value="Default")
        self.profile_combo = ttk.Combobox(
            chrome_frame,
            textvariable=self.profile_var,
            values=["Default", "Profile 1", "Profile 2"],
            state="readonly",
            width=30
        )
        self.profile_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            chrome_frame,
            text="利用可能なプロファイルを検出",
            command=self._detect_chrome_profiles
        ).pack(side=tk.LEFT)
        
        # テストボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="1. モデル情報取得テスト",
            command=self._test_model_fetching,
            width=25
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="2. ブラウザ起動テスト",
            command=self._test_browser_launch,
            width=25
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="3. AIアクセステスト",
            command=self._test_ai_access,
            width=25
        ).pack(side=tk.LEFT, padx=5)
        
        # ログ表示エリア
        log_frame = ttk.LabelFrame(main_frame, text="実行ログ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # スクロールバー付きテキストエリア
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _center_window(self):
        """ウィンドウを画面中央に配置"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _log(self, message: str, level: str = "INFO"):
        """ログメッセージを表示"""
        timestamp = asyncio.get_event_loop().time()
        log_entry = f"[{level}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update()
    
    def _detect_chrome_profiles(self):
        """利用可能なChromeプロファイルを検出"""
        self._log("Chromeプロファイルを検出中...")
        
        try:
            manager = BrowserManager()
            profiles = manager.get_available_profiles_info()
            
            if profiles:
                profile_names = [p['name'] + f" ({p['dir']})" for p in profiles]
                self.profile_combo['values'] = profile_names
                self.profile_var.set(profile_names[0])
                self._log(f"{len(profiles)}個のプロファイルを検出しました")
                
                # プロファイル情報を表示
                for profile in profiles:
                    self._log(f"  - {profile['name']} ({profile['dir']})")
            else:
                self._log("プロファイルが見つかりませんでした", "WARNING")
                
        except Exception as e:
            self._log(f"プロファイル検出エラー: {e}", "ERROR")
    
    def _test_model_fetching(self):
        """モデル情報取得をテスト"""
        self._log("\n=== モデル情報取得テスト開始 ===")
        
        # AI設定を取得
        configs = self.ai_config_panel.get_all_configs()
        
        for ai_name, config in configs.items():
            if config.get('enabled', False):
                widget = self.ai_config_panel.ai_widgets.get(ai_name)
                if widget:
                    self._log(f"{ai_name} のモデル情報を更新中...")
                    widget._refresh_models()
                    
        self._log("モデル情報の取得を開始しました。完了まで少々お待ちください。")
    
    def _test_browser_launch(self):
        """ブラウザ起動をテスト"""
        self._log("\n=== ブラウザ起動テスト開始 ===")
        
        async def launch_browser():
            try:
                # 選択されたプロファイルを取得
                profile_text = self.profile_var.get()
                profile_dir = "Default"
                if "(" in profile_text and ")" in profile_text:
                    profile_dir = profile_text.split("(")[1].split(")")[0]
                
                self._log(f"プロファイル '{profile_dir}' でブラウザを起動中...")
                
                self.browser_manager = BrowserManager(use_profile=profile_dir)
                success = await self.browser_manager.start_browser(
                    headless=False,
                    use_existing_profile=True,
                    profile_dir=profile_dir
                )
                
                if success:
                    self._log("ブラウザ起動成功 ✓")
                    
                    # テストページを開く
                    page = await self.browser_manager.create_page("test", "https://www.google.com")
                    if page:
                        self._log("テストページ (Google) を開きました")
                        await asyncio.sleep(2)
                else:
                    self._log("ブラウザ起動失敗", "ERROR")
                    
            except Exception as e:
                self._log(f"ブラウザ起動エラー: {e}", "ERROR")
        
        # 非同期タスクを実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(launch_browser())
    
    def _test_ai_access(self):
        """各AIサービスへのアクセスをテスト"""
        self._log("\n=== AIサービスアクセステスト開始 ===")
        
        if not self.browser_manager:
            self._log("先にブラウザ起動テストを実行してください", "WARNING")
            return
        
        async def test_ai_services():
            ai_urls = {
                "ChatGPT": "https://chatgpt.com",
                "Claude": "https://claude.ai",
                "Gemini": "https://gemini.google.com",
                "Genspark": "https://www.genspark.ai",
                "Google AI Studio": "https://aistudio.google.com"
            }
            
            # 有効なAIサービスのみテスト
            configs = self.ai_config_panel.get_all_configs()
            
            for ai_name, config in configs.items():
                if config.get('enabled', False) and ai_name in ai_urls:
                    url = ai_urls[ai_name]
                    self._log(f"\n{ai_name} にアクセス中: {url}")
                    
                    try:
                        page_name = f"ai_{ai_name.lower().replace(' ', '_')}"
                        page = await self.browser_manager.create_page(page_name, url)
                        
                        if page:
                            await asyncio.sleep(3)  # ページ読み込み待機
                            
                            # ログイン状態を簡易チェック
                            # 実際にはAIごとに異なるチェックが必要
                            page_content = await page.content()
                            
                            if "sign in" in page_content.lower() or "log in" in page_content.lower():
                                self._log(f"  → ログインが必要です", "WARNING")
                            else:
                                self._log(f"  → アクセス成功 (ログイン済みの可能性)")
                            
                            # スクリーンショットを撮影
                            screenshot_path = f"test_{ai_name.lower()}.png"
                            await page.screenshot(path=screenshot_path)
                            self._log(f"  → スクリーンショット保存: {screenshot_path}")
                            
                    except Exception as e:
                        self._log(f"  → アクセスエラー: {e}", "ERROR")
            
            self._log("\nAIサービスアクセステスト完了")
        
        # 非同期タスクを実行
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_ai_services())
    
    def run(self):
        """GUIを実行"""
        self.root.mainloop()
        
        # クリーンアップ
        if self.browser_manager:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.browser_manager.cleanup())


def main():
    """メイン関数"""
    print("AI自動化機能 統合テストを開始します\n")
    
    # GUIを作成して実行
    app = AIAutomationTestGUI()
    app.run()
    
    print("\nテスト終了")


if __name__ == "__main__":
    main()