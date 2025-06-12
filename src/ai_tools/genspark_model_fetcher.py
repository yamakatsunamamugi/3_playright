"""
Genspark用のモデル情報取得クラス
"""
from typing import Dict, List, Any
from .model_fetcher import ModelFetcher, ModelInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GensparkModelFetcher(ModelFetcher):
    """Gensparkのモデル情報を取得するクラス"""
    
    def __init__(self):
        super().__init__("Genspark")
        
    def fetch_models_from_source(self) -> List[ModelInfo]:
        """
        Gensparkの最新モデル情報を取得
        注: Gensparkは比較的新しいサービスのため、モデル情報は限定的
        """
        # 2024年12月時点の推定モデル情報
        models = [
            ModelInfo(
                id="genspark-default",
                name="Genspark Default",
                description="Gensparkの標準モデル。Web検索と統合された応答生成",
                capabilities=["text", "search", "reasoning"],
                max_tokens=32000,
                is_default=True
            ),
            ModelInfo(
                id="genspark-pro",
                name="Genspark Pro",
                description="高度な検索と分析機能を持つプロフェッショナルモデル",
                capabilities=["text", "search", "reasoning", "analysis"],
                max_tokens=64000
            ),
            ModelInfo(
                id="genspark-research",
                name="Genspark Research",
                description="深い調査と研究に特化したモデル",
                capabilities=["text", "search", "research", "citation"],
                max_tokens=128000
            )
        ]
        
        logger.info(f"Genspark: {len(models)}個のモデル情報を取得しました")
        return models
        
    def get_default_settings(self) -> Dict[str, Any]:
        """Gensparkのデフォルト設定を取得"""
        return {
            "search_depth": {
                "type": "select",
                "default": "medium",
                "options": ["shallow", "medium", "deep"],
                "description": "Web検索の深さ"
            },
            "response_style": {
                "type": "select",
                "default": "comprehensive",
                "options": ["concise", "balanced", "comprehensive", "academic"],
                "description": "回答スタイル"
            },
            "enable_citations": {
                "type": "checkbox",
                "default": True,
                "description": "引用元の表示を有効にする"
            },
            "enable_real_time_search": {
                "type": "checkbox",
                "default": True,
                "description": "リアルタイム検索を有効にする"
            },
            "language": {
                "type": "select",
                "default": "japanese",
                "options": ["japanese", "english", "auto"],
                "description": "言語設定"
            },
            "max_search_results": {
                "type": "number",
                "default": 10,
                "min": 5,
                "max": 50,
                "description": "検索結果の最大数"
            },
            "enable_sparkpages": {
                "type": "checkbox",
                "default": False,
                "description": "Sparkpages（詳細レポート）の生成を有効にする"
            }
        }
        
    def _get_fallback_models(self) -> List[ModelInfo]:
        """フォールバック用のデフォルトモデル情報"""
        return [
            ModelInfo(
                id="genspark-default",
                name="Genspark Default",
                description="標準的な検索統合モデル"
            )
        ]