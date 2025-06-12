"""
プログレス表示ウィジェット

処理の進捗状況をプログレスバーとテキストで表示
処理完了予想時間、エラー率などの統計情報も提供
"""

import tkinter as tk
from tkinter import ttk
import time
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProgressWidget:
    """処理進捗表示ウィジェット"""
    
    def __init__(self, parent: tk.Widget):
        """
        ProgressWidgetを初期化
        
        Args:
            parent: 親ウィジェット
        """
        self.parent = parent
        
        # 進捗管理変数
        self.total_items = 0
        self.completed_items = 0
        self.error_items = 0
        self.start_time = None
        self.current_task = ""
        
        self._create_widgets()
        self._reset_progress()
        
        logger.debug("ProgressWidgetを初期化しました")
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        self.frame = ttk.LabelFrame(self.parent, text="処理進捗", padding="10")
        
        # 現在のタスク表示
        self.task_label = ttk.Label(self.frame, text="待機中", font=("", 10, "bold"))
        
        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.frame,
            variable=self.progress_var,
            maximum=100,
            length=400
        )
        
        # 進捗テキスト
        self.progress_text = ttk.Label(self.frame, text="0 / 0 (0%)")
        
        # 統計情報フレーム
        self.stats_frame = ttk.Frame(self.frame)
        
        # 処理時間表示
        self.time_label = ttk.Label(self.stats_frame, text="経過時間: 00:00:00")
        
        # 完了予想時間
        self.eta_label = ttk.Label(self.stats_frame, text="完了予想: --:--:--")
        
        # エラー率表示
        self.error_label = ttk.Label(self.stats_frame, text="エラー: 0件 (0%)", foreground="red")
        
        # 処理速度表示
        self.speed_label = ttk.Label(self.stats_frame, text="処理速度: -- 件/分")
        
        self._layout_widgets()
    
    def _layout_widgets(self):
        """ウィジェットのレイアウト"""
        # メイン要素
        self.task_label.pack(pady=(0, 5))
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_text.pack(pady=(0, 10))
        
        # 統計情報
        self.stats_frame.pack(fill=tk.X)
        
        # 統計情報を2列に配置
        self.time_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        self.eta_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        self.error_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 20))
        self.speed_label.grid(row=1, column=1, sticky=tk.W, padx=(0, 20))
        
        self.stats_frame.columnconfigure(0, weight=1)
        self.stats_frame.columnconfigure(1, weight=1)
    
    def start_progress(self, total_items: int, task_name: str = "処理実行中"):
        """
        進捗表示を開始
        
        Args:
            total_items: 全体のアイテム数
            task_name: タスク名
        """
        self.total_items = total_items
        self.completed_items = 0
        self.error_items = 0
        self.start_time = time.time()
        self.current_task = task_name
        
        self.task_label.config(text=task_name)
        self._update_display()
        
        logger.info(f"進捗表示を開始: {task_name} (全{total_items}件)")
    
    def update_progress(self, completed: int, current_item: str = "", has_error: bool = False):
        """
        進捗を更新
        
        Args:
            completed: 完了したアイテム数
            current_item: 現在処理中のアイテム名
            has_error: エラーが発生した場合 True
        """
        if has_error and completed > self.completed_items:
            self.error_items += 1
        
        self.completed_items = completed
        
        if current_item:
            self.task_label.config(text=f"{self.current_task}: {current_item}")
        
        self._update_display()
    
    def increment_progress(self, current_item: str = "", has_error: bool = False):
        """
        進捗を1つ進める
        
        Args:
            current_item: 現在処理中のアイテム名
            has_error: エラーが発生した場合 True
        """
        if has_error:
            self.error_items += 1
        
        self.completed_items += 1
        
        if current_item:
            self.task_label.config(text=f"{self.current_task}: {current_item}")
        
        self._update_display()
    
    def _update_display(self):
        """表示内容を更新"""
        if self.total_items > 0:
            # 進捗率計算
            progress_percent = (self.completed_items / self.total_items) * 100
            self.progress_var.set(progress_percent)
            
            # 進捗テキスト更新
            self.progress_text.config(
                text=f"{self.completed_items} / {self.total_items} ({progress_percent:.1f}%)"
            )
            
            # 統計情報更新
            self._update_statistics()
        else:
            self.progress_var.set(0)
            self.progress_text.config(text="0 / 0 (0%)")
    
    def _update_statistics(self):
        """統計情報を更新"""
        if not self.start_time:
            return
        
        elapsed_time = time.time() - self.start_time
        
        # 経過時間
        elapsed_str = self._format_time(elapsed_time)
        self.time_label.config(text=f"経過時間: {elapsed_str}")
        
        # 完了予想時間（ETA）
        if self.completed_items > 0 and self.completed_items < self.total_items:
            remaining_items = self.total_items - self.completed_items
            avg_time_per_item = elapsed_time / self.completed_items
            eta_seconds = remaining_items * avg_time_per_item
            eta_str = self._format_time(eta_seconds)
            self.eta_label.config(text=f"完了予想: {eta_str}")
        elif self.completed_items >= self.total_items:
            self.eta_label.config(text="完了予想: 完了")
        else:
            self.eta_label.config(text="完了予想: 計算中...")
        
        # エラー率
        if self.completed_items > 0:
            error_rate = (self.error_items / self.completed_items) * 100
            self.error_label.config(text=f"エラー: {self.error_items}件 ({error_rate:.1f}%)")
        else:
            self.error_label.config(text="エラー: 0件 (0%)")
        
        # 処理速度（件/分）
        if elapsed_time > 0:
            items_per_minute = (self.completed_items / elapsed_time) * 60
            self.speed_label.config(text=f"処理速度: {items_per_minute:.1f} 件/分")
        else:
            self.speed_label.config(text="処理速度: -- 件/分")
    
    def _format_time(self, seconds: float) -> str:
        """
        秒数をHH:MM:SS形式にフォーマット
        
        Args:
            seconds: 秒数
            
        Returns:
            フォーマットされた時間文字列
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def complete_progress(self, success_message: str = "処理が完了しました"):
        """
        進捗を完了状態にする
        
        Args:
            success_message: 完了メッセージ
        """
        self.completed_items = self.total_items
        self.task_label.config(text=success_message)
        self._update_display()
        
        logger.info(f"進捗完了: {success_message}")
    
    def _reset_progress(self):
        """進捗表示をリセット"""
        self.total_items = 0
        self.completed_items = 0
        self.error_items = 0
        self.start_time = None
        self.current_task = ""
        
        self.task_label.config(text="待機中")
        self.progress_var.set(0)
        self.progress_text.config(text="0 / 0 (0%)")
        self.time_label.config(text="経過時間: 00:00:00")
        self.eta_label.config(text="完了予想: --:--:--")
        self.error_label.config(text="エラー: 0件 (0%)")
        self.speed_label.config(text="処理速度: -- 件/分")
    
    def reset(self):
        """進捗表示を初期状態にリセット"""
        self._reset_progress()
        logger.debug("進捗表示をリセットしました")
    
    def set_indeterminate(self, message: str = "処理中..."):
        """
        不定期進捗モードに設定
        
        Args:
            message: 表示メッセージ
        """
        self.task_label.config(text=message)
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start()
        self.progress_text.config(text="処理中...")
        
        # 統計情報をクリア
        self.time_label.config(text="経過時間: --:--:--")
        self.eta_label.config(text="完了予想: --:--:--")
        self.error_label.config(text="エラー: --")
        self.speed_label.config(text="処理速度: --")
    
    def stop_indeterminate(self):
        """不定期進捗モードを停止"""
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate')
    
    def set_error_state(self, error_message: str):
        """
        エラー状態を表示
        
        Args:
            error_message: エラーメッセージ
        """
        self.task_label.config(text=f"エラー: {error_message}", foreground="red")
        self.stop_indeterminate()
        logger.error(f"進捗表示でエラー状態を設定: {error_message}")
    
    def get_statistics(self) -> dict:
        """
        現在の統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'error_items': self.error_items,
            'elapsed_time': elapsed_time,
            'error_rate': (self.error_items / max(self.completed_items, 1)) * 100,
            'items_per_minute': (self.completed_items / max(elapsed_time, 1)) * 60 if elapsed_time > 0 else 0
        }
    
    def grid(self, **kwargs):
        """ウィジェットをgridで配置"""
        self.frame.grid(**kwargs)
    
    def pack(self, **kwargs):
        """ウィジェットをpackで配置"""
        self.frame.pack(**kwargs)