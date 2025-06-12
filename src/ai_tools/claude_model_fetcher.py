"""
Claude用のモデル情報取得クラス
"""
from typing import Dict, List, Any
from .model_fetcher import ModelFetcher, ModelInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeModelFetcher(ModelFetcher):
    """Claudeのモデル情報を取得するクラス"""
    
    def __init__(self):
        super().__init__("Claude")
        
    def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        Claudeの最新モデル情報を取得
        """
        # 2024年12月時点の最新モデル情報
        models = [
            ModelInfo(
                id="claude-3-5-sonnet",
                name="Claude 3.5 Sonnet",
                description="最新の高性能モデル。高度な推論と分析能力を持つ",
                capabilities=["text", "vision", "code", "reasoning", "analysis"],
                max_tokens=200000,
                is_default=True
            ),
            ModelInfo(
                id="claude-3-5-haiku", 
                name="Claude 3.5 Haiku",
                description="高速で効率的な軽量モデル",
                capabilities=["text", "code", "reasoning"],
                max_tokens=200000
            ),
            ModelInfo(
                id="claude-3-opus",
                name="Claude 3 Opus",
                description="最も高性能な大規模モデル。複雑なタスクに最適",
                capabilities=["text", "vision", "code", "reasoning", "analysis"],
                max_tokens=200000
            ),
            ModelInfo(
                id="claude-3-sonnet",
                name="Claude 3 Sonnet",
                description="バランスの取れた中規模モデル",
                capabilities=["text", "vision", "code", "reasoning"],
                max_tokens=200000
            ),
            ModelInfo(
                id="claude-3-haiku",
                name="Claude 3 Haiku",
                description="高速応答が可能な軽量モデル",
                capabilities=["text", "code"],
                max_tokens=200000
            )
        ]
        
        logger.info(f"Claude: {len(models)}個のモデル情報を取得しました")
        return models
        
    def get_default_settings(self) -> Dict[str, Any]:
        """Claudeのデフォルト設定を取得"""
        return {
            "temperature": {
                "type": "slider",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "step": 0.1,
                "description": "回答の創造性（0:確定的、1:創造的）"
            },
            "max_tokens": {
                "type": "number",
                "default": 4096,
                "min": 1,
                "max": 200000,
                "description": "最大トークン数"
            },
            "enable_artifacts": {
                "type": "checkbox",
                "default": True,
                "description": "Artifacts（コード・文書の独立表示）を有効にする"
            },
            "enable_deep_thinking": {
                "type": "checkbox",
                "default": False,
                "description": "Deep Thinking（深い思考モード）を有効にする"
            },
            "enable_vision": {
                "type": "checkbox",
                "default": True,
                "description": "画像認識機能を有効にする"
            },
            "output_format": {
                "type": "select",
                "default": "markdown",
                "options": ["markdown", "plain", "code"],
                "description": "出力フォーマット"
            },
            "language_preference": {
                "type": "select",
                "default": "japanese",
                "options": ["japanese", "english", "auto"],
                "description": "言語設定"
            }
        }
        
    def _get_fallback_models(self) -> List[ModelInfo]:
        """フォールバック用のデフォルトモデル情報"""
        return [
            ModelInfo(
                id="claude-3-5-sonnet",
                name="Claude 3.5 Sonnet",
                description="最新の高性能モデル"
            ),
            ModelInfo(
                id="claude-3-haiku",
                name="Claude 3 Haiku",
                description="高速応答が可能な軽量モデル"
            )
        ]