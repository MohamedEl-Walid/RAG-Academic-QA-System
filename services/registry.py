"""Strategy and registry patterns for config-driven pipeline execution."""

from typing import Callable, Dict, List
from services.config import RequestConfig, PipelineContext, FeatureResult


class DepthStrategy:
    """Modifies RequestConfig based on depth_mode."""

    @staticmethod
    def apply(config: RequestConfig):
        if config.depth_mode == "fast":
            config.retrieval_top_k = 3
            # Disable heavy features in fast mode
            config.enabled_features["code"] = False
            config.enabled_features["study_plan"] = False
        elif config.depth_mode == "balanced":
            config.retrieval_top_k = 6
        elif config.depth_mode == "deep":
            config.retrieval_top_k = 10
            # Auto-enable concept_graph when diagram is on (they complement each other)
            if config.enabled_features.get("diagram"):
                config.enabled_features["concept_graph"] = True


class LevelStrategy:
    """Adjusts retrieval and generation parameters based on learning_level.

    Level acts as a multiplier on top of the depth strategy:
      - beginner  → fewer, simpler chunks; lower token budget
      - expert    → richer context; higher token budget
    """

    @staticmethod
    def apply(config: RequestConfig):
        level = config.learning_level

        if level == "beginner":
            # Slightly reduce retrieval — less noise for beginners
            config.retrieval_top_k = max(2, config.retrieval_top_k - 1)
        elif level == "expert":
            # Experts benefit from richer context
            config.retrieval_top_k = config.retrieval_top_k + 2


class FeatureRegistry:
    """Decorator-based registry for feature execution functions."""

    def __init__(self):
        self._registry: Dict[str, Callable[[PipelineContext], FeatureResult]] = {}

    def register(self, feature_name: str):
        def decorator(func: Callable[[PipelineContext], FeatureResult]):
            self._registry[feature_name] = func
            return func
        return decorator

    def execute(self, feature_name: str, context: PipelineContext) -> FeatureResult:
        if feature_name in self._registry:
            return self._registry[feature_name](context)
        return None

    def get_all_registered(self) -> List[str]:
        return list(self._registry.keys())


feature_registry = FeatureRegistry()
