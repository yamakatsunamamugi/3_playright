"""
ログ表示ウィジェット

処理ログをリアルタイムで表示し、ログレベル別のフィルタリング、
ファイル保存、検索機能を提供する
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import re
from typing import List, Optional, Callable
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LogWidget:
    """ログ表示ウィジェット"""
    
    # ログレベルの定義
    LOG_LEVELS = {
        'DEBUG': {'color': 'gray', 'priority': 0},
        'INFO': {'color': 'black', 'priority': 1},
        'WARNING': {'color': 'orange', 'priority': 2},
        'ERROR': {'color': 'red', 'priority': 3},
        'CRITICAL': {'color': 'purple', 'priority': 4}
    }
    
    def __init__(self, parent: tk.Widget, max_lines: int = 1000):
        """
        LogWidgetを初期化
        
        Args:
            parent: 親ウィジェット
            max_lines: 最大保持行数
        """
        self.parent = parent
        self.max_lines = max_lines
        self.log_entries: List[dict] = []
        self.filtered_entries: List[dict] = []
        self.current_filter_level = 'DEBUG'
        self.search_text = ""
        
        self._create_widgets()
        self._setup_tags()
        
        logger.debug(f"LogWidgetを初期化しました (最大{max_lines}行)")
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        self.frame = ttk.LabelFrame(self.parent, text="実行ログ", padding="10")
        
        # コントロールフレーム
        self.control_frame = ttk.Frame(self.frame)
        
        # ログレベルフィルター
        self.level_label = ttk.Label(self.control_frame, text="表示レベル:")
        self.level_var = tk.StringVar(value='DEBUG')
        self.level_combo = ttk.Combobox(
            self.control_frame,
            textvariable=self.level_var,
            values=list(self.LOG_LEVELS.keys()),
            state="readonly",
            width=10
        )
        self.level_combo.bind('<<ComboboxSelected>>', self._on_level_changed)
        
        # 検索機能
        self.search_label = ttk.Label(self.control_frame, text="検索:")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.control_frame, textvariable=self.search_var, width=20)
        self.search_entry.bind('<KeyRelease>', self._on_search_changed)
        
        # ボタン群
        self.clear_button = ttk.Button(
            self.control_frame,
            text="クリア",
            command=self.clear_logs,
            width=8
        )
        
        self.save_button = ttk.Button(
            self.control_frame,
            text="保存",
            command=self.save_logs,
            width=8
        )
        
        # ログ表示エリア
        self.log_frame = ttk.Frame(self.frame)
        
        # テキストウィジェット（スクロールバー付き）
        self.log_text = tk.Text(
            self.log_frame,
            height=15,
            width=80,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Courier", 9)
        )
        
        self.scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.scrollbar.set)
        
        # ステータスバー
        self.status_frame = ttk.Frame(self.frame)
        self.log_count_label = ttk.Label(self.status_frame, text="ログ: 0件")
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_check = ttk.Checkbutton(
            self.status_frame,
            text="自動スクロール",
            variable=self.auto_scroll_var
        )
        
        self._layout_widgets()
    
    def _layout_widgets(self):
        """ウィジェットのレイアウト"""
        # コントロールエリア
        self.control_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.level_label.pack(side=tk.LEFT, padx=(0, 5))
        self.level_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        self.search_label.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        self.clear_button.pack(side=tk.RIGHT, padx=(5, 0))
        self.save_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # ログ表示エリア
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ステータスバー
        self.status_frame.pack(fill=tk.X)
        self.log_count_label.pack(side=tk.LEFT)
        self.auto_scroll_check.pack(side=tk.RIGHT)
    
    def _setup_tags(self):
        """テキストウィジェットのタグを設定"""
        for level, config in self.LOG_LEVELS.items():
            self.log_text.tag_configure(level, foreground=config['color'])
        
        # 検索ハイライト用タグ
        self.log_text.tag_configure('search_highlight', background='yellow')
    
    def add_log(self, message: str, level: str = "INFO", timestamp: Optional[datetime] = None):
        """
        ログエントリを追加
        
        Args:
            message: ログメッセージ
            level: ログレベル
            timestamp: タイムスタンプ（省略時は現在時刻）
        """
        if level not in self.LOG_LEVELS:
            level = "INFO"
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # ログエントリを作成
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'formatted': f"[{timestamp.strftime('%H:%M:%S')}] [{level}] {message}"
        }
        
        # ログエントリを追加
        self.log_entries.append(log_entry)
        
        # 最大行数を超えた場合、古いエントリを削除
        if len(self.log_entries) > self.max_lines:
            self.log_entries = self.log_entries[-self.max_lines:]
        
        # フィルター更新
        self._update_filtered_entries()
        
        # 表示更新
        self._update_display()
        
        logger.debug(f"ログエントリを追加: [{level}] {message}")
    
    def _on_level_changed(self, event=None):
        """ログレベルフィルター変更時の処理"""
        self.current_filter_level = self.level_var.get()
        self._update_filtered_entries()
        self._update_display()
    
    def _on_search_changed(self, event=None):
        """検索テキスト変更時の処理"""
        self.search_text = self.search_var.get()
        self._update_filtered_entries()
        self._update_display()
    
    def _update_filtered_entries(self):
        """フィルター条件に基づいてログエントリを更新"""
        min_priority = self.LOG_LEVELS[self.current_filter_level]['priority']
        
        self.filtered_entries = []
        
        for entry in self.log_entries:
            # レベルフィルター
            if self.LOG_LEVELS[entry['level']]['priority'] < min_priority:
                continue
            
            # 検索フィルター
            if self.search_text and self.search_text.lower() not in entry['message'].lower():
                continue
            
            self.filtered_entries.append(entry)
    
    def _update_display(self):
        """ログ表示を更新"""
        # テキストウィジェットを一時的に編集可能にする
        self.log_text.config(state=tk.NORMAL)
        
        # 内容をクリア
        self.log_text.delete(1.0, tk.END)
        
        # フィルターされたエントリを表示
        for entry in self.filtered_entries:
            start_index = self.log_text.index(tk.END + "-1c")
            self.log_text.insert(tk.END, entry['formatted'] + "\\n")
            end_index = self.log_text.index(tk.END + "-1c")
            
            # ログレベルに応じてタグを適用
            self.log_text.tag_add(entry['level'], start_index, end_index)
        
        # 検索ハイライト
        self._highlight_search_text()
        
        # テキストウィジェットを読み取り専用に戻す
        self.log_text.config(state=tk.DISABLED)
        
        # 自動スクロール
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        # ステータス更新
        self._update_status()
    
    def _highlight_search_text(self):
        """検索テキストをハイライト"""
        if not self.search_text:
            return
        
        # 既存のハイライトを削除
        self.log_text.tag_remove('search_highlight', 1.0, tk.END)
        
        # 検索テキストをハイライト
        start = 1.0
        while True:
            pos = self.log_text.search(
                self.search_text,
                start,
                stopindex=tk.END,
                nocase=True
            )
            if not pos:
                break
            
            end_pos = f"{pos}+{len(self.search_text)}c"
            self.log_text.tag_add('search_highlight', pos, end_pos)
            start = end_pos
    
    def _update_status(self):
        """ステータスバーを更新"""
        total_logs = len(self.log_entries)
        filtered_logs = len(self.filtered_entries)
        
        if total_logs == filtered_logs:
            status_text = f"ログ: {total_logs}件"
        else:
            status_text = f"ログ: {filtered_logs}件 / {total_logs}件 (フィルター適用)"
        
        self.log_count_label.config(text=status_text)
    
    def clear_logs(self):
        """ログをクリア"""
        if messagebox.askyesno("確認", "すべてのログをクリアしますか？"):
            self.log_entries.clear()
            self.filtered_entries.clear()
            self._update_display()
            logger.info("ログをクリアしました")
    
    def save_logs(self):
        """ログをファイルに保存"""
        if not self.filtered_entries:
            messagebox.showinfo("情報", "保存するログがありません")
            return
        
        # ファイル保存ダイアログ
        filename = filedialog.asksaveasfilename(
            title="ログファイルを保存",
            defaultextension=".txt",
            filetypes=[
                ("テキストファイル", "*.txt"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"ログファイル - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
                    f.write("=" * 50 + "\\n\\n")
                    
                    for entry in self.filtered_entries:
                        f.write(entry['formatted'] + "\\n")
                
                messagebox.showinfo("成功", f"ログを保存しました: {filename}")
                logger.info(f"ログをファイルに保存しました: {filename}")
                
            except Exception as e:
                messagebox.showerror("エラー", f"ログの保存に失敗しました:\\n{e}")
                logger.error(f"ログ保存エラー: {e}")
    
    def get_log_statistics(self) -> dict:
        """
        ログ統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        stats = {level: 0 for level in self.LOG_LEVELS.keys()}
        stats['total'] = len(self.log_entries)
        
        for entry in self.log_entries:
            stats[entry['level']] += 1
        
        return stats
    
    def export_filtered_logs(self) -> List[str]:
        """
        フィルターされたログを文字列リストで取得
        
        Returns:
            フィルターされたログの文字列リスト
        """
        return [entry['formatted'] for entry in self.filtered_entries]
    
    def add_info(self, message: str):
        """INFOレベルのログを追加"""
        self.add_log(message, "INFO")
    
    def add_warning(self, message: str):
        """WARNINGレベルのログを追加"""
        self.add_log(message, "WARNING")
    
    def add_error(self, message: str):
        """ERRORレベルのログを追加"""
        self.add_log(message, "ERROR")
    
    def add_debug(self, message: str):
        """DEBUGレベルのログを追加"""
        self.add_log(message, "DEBUG")
    
    def grid(self, **kwargs):
        """ウィジェットをgridで配置"""
        self.frame.grid(**kwargs)
    
    def pack(self, **kwargs):
        """ウィジェットをpackで配置"""
        self.frame.pack(**kwargs)