import time
import random
from typing import List, Dict, Optional
from src.interfaces.ai_interface import IAITool, IAIManager, AIToolStatus


class MockAITool(IAITool):
    """チームAとBが使用するAIツールのモック"""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.status = AIToolStatus.DISCONNECTED
        self.models = {
            'ChatGPT': ['GPT-4', 'GPT-3.5-turbo', 'GPT-4-turbo'],
            'Claude': ['Claude-3-opus', 'Claude-3-sonnet', 'Claude-3-haiku'],
            'Gemini': ['Gemini-Pro', 'Gemini-Pro-Vision', 'Gemini-Ultra'],
            'Genspark': ['Genspark-1', 'Genspark-2'],
            'Google AI Studio': ['PaLM-2', 'Gemini-Pro']
        }
        self.current_model = None
        
    def initialize(self, profile_path: Optional[str] = None) -> bool:
        time.sleep(0.5)  # 初期化のシミュレート
        self.status = AIToolStatus.CONNECTED
        return True
    
    def get_status(self) -> AIToolStatus:
        return self.status
    
    def login(self) -> bool:
        time.sleep(1)  # ログイン処理のシミュレート
        self.status = AIToolStatus.CONNECTED
        return True
    
    def get_available_models(self) -> List[str]:
        return self.models.get(self.tool_name, ['Default-Model'])
    
    def select_model(self, model_name: str) -> bool:
        available_models = self.get_available_models()
        if model_name in available_models:
            self.current_model = model_name
            return True
        return False
    
    def send_prompt(self, text: str, timeout: int = 300) -> str:
        self.status = AIToolStatus.PROCESSING
        
        # 処理時間をシミュレート（1-5秒）
        processing_time = random.uniform(1, 5)
        time.sleep(processing_time)
        
        # モックレスポンスを生成
        responses = [
            f"これは{self.tool_name}からのモックレスポンスです。\\n\\n入力されたプロンプト: {text[:50]}{'...' if len(text) > 50 else ''}",
            f"{self.tool_name}で処理しました。\\n\\n結果: モックデータとして生成された応答です。",
            f"【{self.tool_name}応答】\\n\\n{text}について分析した結果をお伝えします。\\n\\nこれはテスト用のモックレスポンスです。",
        ]
        
        response = random.choice(responses)
        
        # ランダムでエラーを発生（10%の確率）
        if random.random() < 0.1:
            self.status = AIToolStatus.ERROR
            raise ConnectionError(f"{self.tool_name}との接続でエラーが発生しました")
        
        self.status = AIToolStatus.CONNECTED
        return response
    
    def close(self):
        self.status = AIToolStatus.DISCONNECTED


class MockAIManager(IAIManager):
    """チームAとBが使用するAIマネージャーのモック"""
    
    def __init__(self):
        self.tools = {}
        self.supported_tools = ['ChatGPT', 'Claude', 'Gemini', 'Genspark', 'Google AI Studio']
        
    def get_tool(self, tool_name: str) -> IAITool:
        if tool_name not in self.tools:
            self.tools[tool_name] = MockAITool(tool_name)
        return self.tools[tool_name]
    
    def get_supported_tools(self) -> List[str]:
        return self.supported_tools.copy()
    
    def initialize_all_tools(self, config: Dict[str, Dict]) -> Dict[str, bool]:
        results = {}
        for tool_name, tool_config in config.items():
            if tool_config.get('enabled', False):
                try:
                    tool = self.get_tool(tool_name)
                    success = tool.initialize()
                    if success:
                        tool.login()
                        model = tool_config.get('model')
                        if model:
                            tool.select_model(model)
                    results[tool_name] = success
                except Exception:
                    results[tool_name] = False
            else:
                results[tool_name] = True  # 無効なツールは成功扱い
        
        return results