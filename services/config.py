import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

# Valid learning levels for type-hinting and validation
VALID_LEVELS = ("beginner", "intermediate", "expert")

@dataclass
class RequestConfig:
    depth_mode: str = "balanced"  # fast, balanced, deep
    explanation_mode: str = "explain"  # explain, summarize, teach, revise
    learning_level: str = "beginner"  # beginner, intermediate, expert
    enabled_features: Dict[str, bool] = field(default_factory=dict)
    user_query: str = ""
    user_id: str = "default"
    subject: str = "general"

    # Derived from depth_mode / learning_level during strategy application
    retrieval_top_k: int = 5
    reasoning_level: str = "moderate"
    response_style: str = "detailed"
    generation_flags: Dict[str, bool] = field(default_factory=dict)

@dataclass
class FeatureResult:
    type: str
    title: str
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionState:
    start_time: float = field(default_factory=time.time)
    executed_modules: List[str] = field(default_factory=list)
    skipped_modules: Dict[str, str] = field(default_factory=dict)
    tokens_used: int = 0
    retrieval_stats: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

@dataclass
class PipelineContext:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config: RequestConfig = field(default_factory=RequestConfig)
    state: ExecutionState = field(default_factory=ExecutionState)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    context_text: str = ""
    main_response: str = ""
    feature_results: List[FeatureResult] = field(default_factory=list)
    history: List[Dict[str, str]] = field(default_factory=list)

