import pytest
import asyncio
from src.orchestrator import Orchestrator
from tests.mocks.mock_sheet_processor import MockSheetProcessor, MockSheetHandler
from tests.mocks.mock_ai_tools import MockAIManager
from src.interfaces.gui_interface import IGUIController, ProcessStatus


class MockGUIController(IGUIController):
    """テスト用のGUIコントローラーモック"""
    
    def __init__(self):
        self.progress_current = 0
        self.progress_total = 0
        self.progress_message = ""
        self.logs = []
        self.status = ProcessStatus.IDLE
        self.spreadsheet_config = {
            'url': 'https://docs.google.com/spreadsheets/d/test_id/edit',
            'sheet_name': 'test_sheet'
        }
        self.ai_config = {
            'ChatGPT': {'enabled': True, 'model': 'GPT-4'},
            'Claude': {'enabled': False, 'model': 'Claude-3-opus'}
        }
        
    def update_progress(self, current: int, total: int, message: str = ""):
        self.progress_current = current
        self.progress_total = total
        self.progress_message = message
        
    def add_log(self, message: str, level: str = "INFO"):
        self.logs.append({"message": message, "level": level})
        
    def update_status(self, status: ProcessStatus):
        self.status = status
        
    def get_spreadsheet_config(self):
        return self.spreadsheet_config
        
    def get_ai_config(self):
        return self.ai_config
        
    def set_process_callback(self, callback):
        pass
        
    def set_stop_callback(self, callback):
        pass


class TestIntegration:
    """統合テストクラス"""
    
    @pytest.fixture
    def orchestrator(self):
        orch = Orchestrator()
        
        # モックコンポーネントを設定
        sheet_processor = MockSheetProcessor()
        sheet_handler = MockSheetHandler()
        ai_manager = MockAIManager()
        gui_controller = MockGUIController()
        
        orch.set_components(sheet_processor, sheet_handler, ai_manager, gui_controller)
        
        return orch, gui_controller
    
    def test_extract_sheet_id(self):
        """スプレッドシートID抽出のテスト"""
        orch = Orchestrator()
        
        # 正常なURL
        url1 = "https://docs.google.com/spreadsheets/d/1abc123def456/edit#gid=0"
        assert orch._extract_sheet_id(url1) == "1abc123def456"
        
        # gidなしのURL
        url2 = "https://docs.google.com/spreadsheets/d/1xyz789/edit"
        assert orch._extract_sheet_id(url2) == "1xyz789"
        
        # 無効なURL
        with pytest.raises(ValueError):
            orch._extract_sheet_id("https://invalid-url.com")
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, orchestrator):
        """フルワークフローのテスト"""
        orch, gui_controller = orchestrator
        
        config = {
            'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/test_id/edit',
            'sheet_name': 'test_sheet',
            'ai_tools': {
                'ChatGPT': {'enabled': True, 'model': 'GPT-4'},
                'Claude': {'enabled': False, 'model': 'Claude-3-opus'}
            }
        }
        
        # 処理実行
        result = await orch.process_spreadsheet(config)
        
        # 結果検証
        assert result is True
        assert gui_controller.status == ProcessStatus.COMPLETED
        assert len(gui_controller.logs) > 0
        assert gui_controller.progress_total > 0
        
        # ログの内容確認
        log_messages = [log['message'] for log in gui_controller.logs]
        assert any("処理を開始しました" in msg for msg in log_messages)
        assert any("完了しました" in msg for msg in log_messages)
    
    @pytest.mark.asyncio
    async def test_stop_processing(self, orchestrator):
        """処理停止のテスト"""
        orch, gui_controller = orchestrator
        
        config = {
            'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/test_id/edit',
            'sheet_name': 'test_sheet',
            'ai_tools': {'ChatGPT': {'enabled': True, 'model': 'GPT-4'}}
        }
        
        # 処理を開始して即座に停止
        task = asyncio.create_task(orch.process_spreadsheet(config))
        await asyncio.sleep(0.1)  # 少し待ってから停止
        orch.stop_processing()
        
        result = await task
        
        # 停止されたことを確認
        assert orch.should_stop is True
    
    def test_component_setting(self):
        """コンポーネント設定のテスト"""
        orch = Orchestrator()
        
        # 初期状態ではコンポーネントがNone
        assert orch.sheet_processor is None
        assert orch.sheet_handler is None
        assert orch.ai_manager is None
        assert orch.gui_controller is None
        
        # コンポーネントを設定
        sheet_processor = MockSheetProcessor()
        sheet_handler = MockSheetHandler()
        ai_manager = MockAIManager()
        gui_controller = MockGUIController()
        
        orch.set_components(sheet_processor, sheet_handler, ai_manager, gui_controller)
        
        # 設定されたことを確認
        assert orch.sheet_processor is not None
        assert orch.sheet_handler is not None
        assert orch.ai_manager is not None
        assert orch.gui_controller is not None


if __name__ == "__main__":
    # 簡単な実行テスト
    async def main():
        orch = Orchestrator()
        
        # モックコンポーネントを設定
        sheet_processor = MockSheetProcessor()
        sheet_handler = MockSheetHandler()
        ai_manager = MockAIManager()
        gui_controller = MockGUIController()
        
        orch.set_components(sheet_processor, sheet_handler, ai_manager, gui_controller)
        
        config = {
            'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/test_id/edit',
            'sheet_name': 'test_sheet',
            'ai_tools': {'ChatGPT': {'enabled': True, 'model': 'GPT-4'}}
        }
        
        result = await orch.process_spreadsheet(config)
        print(f"処理結果: {result}")
        print(f"ログ数: {len(gui_controller.logs)}")
        for log in gui_controller.logs:
            print(f"[{log['level']}] {log['message']}")
    
    asyncio.run(main())