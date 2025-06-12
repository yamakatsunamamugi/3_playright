"""
ChatGPT用のモデル情報取得クラス
"""
from typing import Dict, List, Any
from .model_fetcher import ModelFetcher, ModelInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChatGPTModelFetcher(ModelFetcher):
    """ChatGPTのモデル情報を取得するクラス"""
    
    def __init__(self):
        super().__init__("ChatGPT")
        
    def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        ChatGPTの最新モデル情報を取得
        注: OpenAI APIを使用する場合はAPIキーが必要
        現在はハードコードされた情報を返す
        """
        # 2024年12月時点の最新モデル情報
        models = [
            ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                description="最新の高性能モデル。画像認識、高度な推論、コード生成に優れる",
                capabilities=["text", "vision", "code", "reasoning"],
                max_tokens=128000,
                is_default=True
            ),
            ModelInfo(
                id="gpt-4o-mini",
                name="GPT-4o mini",
                description="高速・低コストな軽量版GPT-4o",
                capabilities=["text", "code", "reasoning"],
                max_tokens=128000
            ),
            ModelInfo(
                id="gpt-4-turbo",
                name="GPT-4 Turbo",
                description="GPT-4の高速版。128kトークンの大容量コンテキスト",
                capabilities=["text", "vision", "code", "reasoning"],
                max_tokens=128000
            ),
            ModelInfo(
                id="gpt-4",
                name="GPT-4",
                description="標準的なGPT-4モデル",
                capabilities=["text", "code", "reasoning"],
                max_tokens=8192
            ),
            ModelInfo(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                description="高速で効率的な汎用モデル",
                capabilities=["text", "code"],
                max_tokens=16385
            ),
            ModelInfo(
                id="o1-preview",
                name="o1-preview",
                description="高度な推論能力を持つ新しいモデル（プレビュー版）",
                capabilities=["text", "reasoning", "code", "math"],
                max_tokens=128000
            ),
            ModelInfo(
                id="o1-mini",
                name="o1-mini",
                description="o1の軽量版。高速な推論が可能",
                capabilities=["text", "reasoning", "code"],
                max_tokens=128000
            )
        ]
        
        logger.info(f"ChatGPT: {len(models)}個のモデル情報を取得しました")
        return models
        
    def get_default_settings(self) -> Dict[str, Any]:
        """ChatGPTのデフォルト設定を取得"""
        return {
            "temperature": {
                "type": "slider",
                "default": 0.7,
                "min": 0.0,
                "max": 2.0,
                "step": 0.1,
                "description": "回答の創造性（0:確定的、2:創造的）"
            },
            "max_tokens": {
                "type": "number",
                "default": 4096,
                "min": 1,
                "max": 128000,
                "description": "最大トークン数"
            },
            "top_p": {
                "type": "slider",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "description": "トークン選択の確率閾値"
            },
            "frequency_penalty": {
                "type": "slider",
                "default": 0.0,
                "min": -2.0,
                "max": 2.0,
                "step": 0.1,
                "description": "同じ内容の繰り返しを抑制"
            },
            "presence_penalty": {
                "type": "slider",
                "default": 0.0,
                "min": -2.0,
                "max": 2.0,
                "step": 0.1,
                "description": "新しいトピックへの移行を促進"
            },
            "search_web": {
                "type": "checkbox",
                "default": False,
                "description": "Web検索を有効にする（ChatGPT Plus必須）"
            },
            "use_custom_instructions": {
                "type": "checkbox",
                "default": True,
                "description": "カスタム指示を使用する"
            }
        }
        
    def _get_fallback_models(self) -> List[ModelInfo]:
        """フォールバック用のデフォルトモデル情報"""
        return [
            ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                description="最新の高性能モデル"
            ),
            ModelInfo(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                description="高速で効率的な汎用モデル"
            )
        ]