"""Dynamic pipeline orchestrator — routes every request through
retrieval → generation → feature dispatch → assembly.

Improvements:
- Features run concurrently via ThreadPoolExecutor (each is an LLM call)
- Per-feature timing is logged and included in meta
- Guardrail validation on query input and LLM output
- Mermaid output sanitized before returning to frontend
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.config import RequestConfig, PipelineContext, FeatureResult
from services.registry import DepthStrategy, LevelStrategy, feature_registry
from retrieval.retriever import search
from llm.generator import generate_answer
from services.assembler import assemble_response
from guardrails.validators import validate_question, sanitize_mermaid_output

# Feature module imports (triggers @feature_registry.register)
from quiz.generator import generate_quiz
from concept_graph.extractor import extract_concept_graph
from diagrams.builder import generate_diagram
from coding.generator import generate_code, explain_code
from planner.roadmap import generate_study_plan

logger = logging.getLogger(__name__)

# Thread pool for parallel feature execution
_feature_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="feature")

# ── helpers ───────────────────────────────────────────────────────────────

def _extract_explanation(raw: str) -> str:
    """Pull the explanation section out of the formatted LLM response."""
    if "=== EXPLANATION ===" in raw:
        return raw.split("=== EXPLANATION ===")[-1].strip()
    return raw

# ── Feature registrations ─────────────────────────────────────────────────

@feature_registry.register("quiz")
def run_quiz(ctx: PipelineContext) -> FeatureResult:
    explanation = _extract_explanation(ctx.main_response)
    level = ctx.config.learning_level
    content = generate_quiz(explanation, level=level)
    return FeatureResult(type="quiz", title="Interactive Quiz", content=content)


@feature_registry.register("concept_graph")
def run_concept_graph(ctx: PipelineContext) -> FeatureResult:
    explanation = _extract_explanation(ctx.main_response)
    level = ctx.config.learning_level
    content = extract_concept_graph(explanation, level=level)
    return FeatureResult(type="concept_graph", title="Concept Graph", content=content)


@feature_registry.register("diagram")
def run_diagram(ctx: PipelineContext) -> FeatureResult:
    explanation = _extract_explanation(ctx.main_response)
    level = ctx.config.learning_level
    content = generate_diagram(explanation, level=level)
    # Sanitize mermaid output to prevent injection
    if isinstance(content, dict) and "mermaid" in content:
        content["mermaid"] = sanitize_mermaid_output(content["mermaid"])
    return FeatureResult(type="diagram", title="Diagram", content=content)


@feature_registry.register("code")
def run_code(ctx: PipelineContext) -> FeatureResult:
    level = ctx.config.learning_level
    code = generate_code(ctx.config.user_query, level=level)
    code_explanation = explain_code(code, level=level)
    return FeatureResult(
        type="code", title="Code Example",
        content={"code": code, "code_explanation": code_explanation},
    )


@feature_registry.register("study_plan")
def run_study_plan(ctx: PipelineContext) -> FeatureResult:
    level = ctx.config.learning_level
    content = generate_study_plan(ctx.config.user_query, level=level)
    return FeatureResult(type="study_plan", title="Study Roadmap", content=content)


# ── Main orchestration entry-point ────────────────────────────────────────

def process_pipeline(config: RequestConfig, history: list = None) -> dict:
    start_time = time.time()

    # 0. Validate query through guardrails
    is_valid, err_msg = validate_question(config.user_query)
    if not is_valid:
        logger.warning("Query rejected by guardrails: %s", err_msg)
        return {
            "answer": f"⚠️ {err_msg}",
            "raw_main_response": "",
            "feature_results": [],
            "meta": {
                "execution_time": round(time.time() - start_time, 2),
                "executed_modules": ["guardrail_reject"],
                "skipped_modules": {},
                "errors": [err_msg],
                "retrieval": {},
                "depth_mode": config.depth_mode,
                "explanation_mode": config.explanation_mode,
                "learning_level": config.learning_level,
            },
        }

    # 1. Apply strategies (depth first, then level refines)
    DepthStrategy.apply(config)
    LevelStrategy.apply(config)

    logger.info(
        "Pipeline config — depth=%s  level=%s  mode=%s  top_k=%d  features=%s",
        config.depth_mode, config.learning_level, config.explanation_mode,
        config.retrieval_top_k, config.enabled_features,
    )

    ctx = PipelineContext(config=config, history=history or [])
    feature_timings: dict[str, float] = {}

    try:
        # 2. Retrieval
        t_ret = time.time()
        logger.info("Starting retrieval with top_k=%d", config.retrieval_top_k)
        chunks = search(config.user_query, top_k=config.retrieval_top_k)
        ctx.chunks = chunks
        ctx.context_text = "\n\n".join(
            f"[{i}] {c['content']}" for i, c in enumerate(chunks, 1)
        )
        ctx.state.retrieval_stats = {
            "top_k": config.retrieval_top_k,
            "chunks_retrieved": len(chunks),
            "retrieval_time": round(time.time() - t_ret, 2),
        }

        if not chunks:
            ctx.main_response = "No relevant academic materials found for this query."
            ctx.state.executed_modules.append("retrieval (no results)")
        else:
            ctx.state.executed_modules.append("retrieval")

            # 3. Main LLM generation
            t_gen = time.time()
            logger.info("Generating main response...")
            ctx.main_response = generate_answer(
                query=config.user_query,
                chunks=chunks,
                config=config,
                history=history,
            )
            gen_time = round(time.time() - t_gen, 2)
            ctx.state.executed_modules.append("llm_generator")
            feature_timings["llm_generator"] = gen_time
            logger.info("Main generation completed in %.2fs", gen_time)

            # 4. Feature augmentation — run concurrently
            enabled = [
                name for name, on in config.enabled_features.items() if on
            ]
            disabled = [
                name for name, on in config.enabled_features.items() if not on
            ]
            for d in disabled:
                ctx.state.skipped_modules[d] = "Disabled by user or strategy"

            if enabled:
                logger.info("Running %d features concurrently: %s", len(enabled), enabled)
                futures = {}
                for feature_name in enabled:
                    fut = _feature_pool.submit(_run_feature_safe, feature_name, ctx)
                    futures[fut] = feature_name

                for fut in as_completed(futures):
                    fname = futures[fut]
                    try:
                        result, elapsed = fut.result()
                        if result:
                            ctx.feature_results.append(result)
                            ctx.state.executed_modules.append(f"feature:{fname}")
                            feature_timings[fname] = elapsed
                            logger.info("Feature %s completed in %.2fs", fname, elapsed)
                    except Exception as exc:
                        logger.error("Feature %s failed: %s", fname, exc)
                        ctx.state.errors.append(f"{fname}: {exc}")
                        ctx.state.skipped_modules[fname] = str(exc)

        # 5. Response assembly
        final_markdown = assemble_response(ctx)

    except Exception as exc:
        logger.error("Pipeline error: %s", exc, exc_info=True)
        final_markdown = f"An error occurred during processing: {exc}"
        ctx.state.errors.append(str(exc))

    duration = time.time() - start_time

    return {
        "answer": final_markdown,
        "raw_main_response": ctx.main_response,
        "feature_results": [
            {"type": fr.type, "title": fr.title, "content": fr.content}
            for fr in ctx.feature_results
        ],
        "meta": {
            "execution_time": round(duration, 2),
            "executed_modules": ctx.state.executed_modules,
            "skipped_modules": ctx.state.skipped_modules,
            "errors": ctx.state.errors,
            "retrieval": ctx.state.retrieval_stats,
            "depth_mode": config.depth_mode,
            "explanation_mode": config.explanation_mode,
            "learning_level": config.learning_level,
            "feature_timings": feature_timings,
        },
    }


def _run_feature_safe(feature_name: str, ctx: PipelineContext) -> tuple[FeatureResult | None, float]:
    """Execute a single feature with timing. Returns (result, elapsed_seconds)."""
    t0 = time.time()
    result = feature_registry.execute(feature_name, ctx)
    elapsed = round(time.time() - t0, 2)
    return result, elapsed
