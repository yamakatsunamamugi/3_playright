"""
Google AI Studio用のモデル情報取得クラス
"""
from typing import Dict, List, Any
from .model_fetcher import ModelFetcher, ModelInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleAIStudioModelFetcher(ModelFetcher):
    """Google AI Studioのモデル情報を取得するクラス"""
    
    def __init__(self):
        super().__init__("GoogleAIStudio")
        
    def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        Google AI Studioの最新モデル情報を取得
        注: Google AI StudioはGemini APIのWebインターフェース
        """
        # 2024年12月時点の最新モデル情報
        models = [
            ModelInfo(
                id="gemini-2.0-flash-exp",
                name="Gemini 2.0 Flash (Experimental)",
                description="最新の実験的高速モデル。マルチモーダル対応",
                capabilities=["text", "vision", "code", "reasoning", "audio"],
                max_tokens=1048576
            ),
            ModelInfo(
                id="gemini-1.5-pro-002",
                name="Gemini 1.5 Pro 002",
                description="最新版のGemini 1.5 Pro。最大2Mトークン対応",
                capabilities=["text", "vision", "code", "reasoning", "audio", "video"],
                max_tokens=2097152,
                is_default=True
            ),
            ModelInfo(
                id="gemini-1.5-pro-001",
                name="Gemini 1.5 Pro 001",
                description="安定版のGemini 1.5 Pro",
                capabilities=["text", "vision", "code", "reasoning", "audio"],
                max_tokens=2097152
            ),
            ModelInfo(
                id="gemini-1.5-flash-002",
                name="Gemini 1.5 Flash 002",
                description="最新版の高速モデル",
                capabilities=["text", "vision", "code", "reasoning"],
                max_tokens=1048576
            ),
            ModelInfo(
                id="gemini-1.5-flash-001",
                name="Gemini 1.5 Flash 001",
                description="安定版の高速モデル",
                capabilities=["text", "vision", "code", "reasoning"],
                max_tokens=1048576
            ),
            ModelInfo(
                id="gemini-1.5-flash-8b-exp-0924",
                name="Gemini 1.5 Flash-8B (Experimental)",
                description="実験的な超軽量モデル",
                capabilities=["text", "code"],
                max_tokens=1048576
            ),
            ModelInfo(
                id="gemini-1.0-pro",
                name="Gemini 1.0 Pro",
                description="従来の安定版モデル",
                capabilities=["text", "code", "reasoning"],
                max_tokens=32768
            )
        ]
        
        logger.info(f"Google AI Studio: {len(models)}個のモデル情報を取得しました")
        return models
        
    def get_default_settings(self) -> Dict[str, Any]:
        """Google AI Studioのデフォルト設定を取得"""
        return {
            "temperature": {
                "type": "slider",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "step": 0.1,
                "description": "回答の創造性（0:確定的、2:創造的）"
            },
            "max_output_tokens": {
                "type": "number",
                "default": 8192,
                "min": 1,
                "max": 8192,
                "description": "最大出力トークン数"
            },
            "top_p": {
                "type": "slider",
                "default": 0.95,
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "description": "累積確率の閾値"
            },
            "top_k": {
                "type": "number",
                "default": 64,
                "min": 1,
                "max": 100,
                "description": "考慮するトークン候補の数"
            },
            "stop_sequences": {
                "type": "text",
                "default": "",
                "description": "停止シーケンス（カンマ区切り）"
            },
            "safety_threshold": {
                "type": "select",
                "default": "block_medium_and_above",
                "options": ["block_none", "block_only_high", "block_medium_and_above", "block_low_and_above"],
                "description": "安全性フィルターの閾値"
            },
            "enable_grounding": {
                "type": "checkbox",
                "default": False,
                "description": "Google検索による情報の検証を有効にする"
            },
            "enable_code_execution": {
                "type": "checkbox",
                "default": True,
                "description": "コード実行機能を有効にする"
            },
            "system_instruction": {
                "type": "textarea",
                "default": "",
                "description": "システム指示（プロンプトの前提条件）"
            }
        }
        
    def _get_fallback_models(self) -> List[ModelInfo]:
        """フォールバック用のデフォルトモデル情報"""
        return [
            ModelInfo(
                id="gemini-1.5-pro-002",
                name="Gemini 1.5 Pro",
                description="高性能な大規模モデル"
            ),
            ModelInfo(
                id="gemini-1.5-flash-002",
                name="Gemini 1.5 Flash",
                description="高速応答モデル"
            )
        ]