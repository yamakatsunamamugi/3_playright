"""
Gemini用のモデル情報取得クラス
"""
from typing import Dict, List, Any
from .model_fetcher import ModelFetcher, ModelInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiModelFetcher(ModelFetcher):
    """Geminiのモデル情報を取得するクラス"""
    
    def __init__(self):
        super().__init__("Gemini")
        
    def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        Geminiの最新モデル情報を取得
        """
        # 2024年12月時点の最新モデル情報
        models = [
            ModelInfo(
                id="gemini-2.0-flash-exp",
                name="Gemini 2.0 Flash (Experimental)",
                description="最新の実験的高速モデル。マルチモーダル対応",
                capabilities=["text", "vision", "code", "reasoning", "audio"],
                max_tokens=1048576  # 1M tokens
            ),
            ModelInfo(
                id="gemini-1.5-pro",
                name="Gemini 1.5 Pro",
                description="最大2Mトークンの超大容量コンテキスト。高度な推論能力",
                capabilities=["text", "vision", "code", "reasoning", "audio", "video"],
                max_tokens=2097152,  # 2M tokens
                is_default=True
            ),
            ModelInfo(
                id="gemini-1.5-flash",
                name="Gemini 1.5 Flash",
                description="高速応答に最適化されたモデル。1Mトークンコンテキスト",
                capabilities=["text", "vision", "code", "reasoning"],
                max_tokens=1048576  # 1M tokens
            ),
            ModelInfo(
                id="gemini-1.5-flash-8b",
                name="Gemini 1.5 Flash-8B",
                description="超軽量・高速な8Bパラメータモデル",
                capabilities=["text", "code"],
                max_tokens=1048576  # 1M tokens
            ),
            ModelInfo(
                id="gemini-pro",
                name="Gemini Pro",
                description="バランスの取れた汎用モデル",
                capabilities=["text", "code", "reasoning"],
                max_tokens=32768
            ),
            ModelInfo(
                id="gemini-pro-vision",
                name="Gemini Pro Vision",
                description="画像認識に特化したモデル",
                capabilities=["text", "vision", "reasoning"],
                max_tokens=32768
            )
        ]
        
        logger.info(f"Gemini: {len(models)}個のモデル情報を取得しました")
        return models
        
    def get_default_settings(self) -> Dict[str, Any]:
        """Geminiのデフォルト設定を取得"""
        return {
            "temperature": {
                "type": "slider",
                "default": 0.7,
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
                "description": "トークン選択の確率閾値"
            },
            "top_k": {
                "type": "number",
                "default": 40,
                "min": 1,
                "max": 100,
                "description": "考慮するトークン候補の数"
            },
            "safety_settings": {
                "type": "select",
                "default": "medium",
                "options": ["low", "medium", "high", "none"],
                "description": "安全性フィルターのレベル"
            },
            "enable_grounding": {
                "type": "checkbox",
                "default": False,
                "description": "Google検索による情報の裏付けを有効にする"
            },
            "enable_code_execution": {
                "type": "checkbox",
                "default": False,
                "description": "コード実行機能を有効にする"
            },
            "response_mime_type": {
                "type": "select",
                "default": "text/plain",
                "options": ["text/plain", "application/json", "text/html"],
                "description": "レスポンスのMIMEタイプ"
            }
        }
        
    def _get_fallback_models(self) -> List[ModelInfo]:
        """フォールバック用のデフォルトモデル情報"""
        return [
            ModelInfo(
                id="gemini-1.5-pro",
                name="Gemini 1.5 Pro",
                description="高性能な大規模モデル"
            ),
            ModelInfo(
                id="gemini-1.5-flash",
                name="Gemini 1.5 Flash",
                description="高速応答モデル"
            )
        ]