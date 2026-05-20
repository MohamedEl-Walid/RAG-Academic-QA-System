import streamlit as st
import streamlit.components.v1 as components
from pipeline import process_question
from memory.tracker import load_user
from services.prompts import MODE_PROMPTS
from services.config import VALID_LEVELS

st.set_page_config(page_title="AI Learning Platform", layout="wide")

# CSS for a polished look using Streamlit theme variables
st.markdown("""
<style>
    /* Theme Tokens for consistent Quiz Styling */
    :root {
        --quiz-card-bg: var(--secondary-background-color);
        --quiz-text-primary: var(--text-color);
        --quiz-border: var(--border-color);
    }
    
    .quiz-card {
        background-color: var(--quiz-card-bg);
        color: var(--quiz-text-primary);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid var(--quiz-border);
        margin-bottom: 24px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .quiz-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
    }
    .quiz-card h4 {
        margin-top: 0;
        margin-bottom: 12px;
        font-weight: 600;
    }
    .quiz-card p {
        font-size: 1.1em;
        line-height: 1.5;
        margin-bottom: 0;
    }
    .difficulty-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 700;
        color: white;
        margin-bottom: 16px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .diff-easy { background-color: #10B981; }
    .diff-medium { background-color: #F59E0B; }
    .diff-hard { background-color: #EF4444; }
</style>
""", unsafe_allow_html=True)

st.title("AI-Powered Learning Platform")

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    user_id = st.text_input("User ID", value="default")
    profile = load_user(user_id)

    # ── Learning Level Slider ─────────────────────────────────────────────
    st.header("Learning Level")
    level_labels = {"beginner": "🟢 Beginner", "intermediate": "🟡 Intermediate", "expert": "🔴 Expert"}
    learning_level = st.select_slider(
        "Select your level:",
        options=list(VALID_LEVELS),
        value="beginner",
        format_func=lambda x: level_labels[x],
    )
    st.caption(f"Current level: **{level_labels[learning_level]}**")

    st.info(f"Questions asked: **{len(profile['questions'])}**")

    if profile["weak_areas"]:
        st.warning(f"Weak areas: {', '.join(profile['weak_areas'])}")

    # ── Depth Mode ────────────────────────────────────────────────────────
    st.header("Depth Mode")
    depth = st.radio(
        "Select depth:",
        ["fast", "balanced", "deep"],
        index=1,
        help="fast = brief answer | balanced = standard | deep = extensive chain-of-thought",
    )

    # ── Explanation Mode ──────────────────────────────────────────────────
    st.header("Explanation Mode")
    mode = st.selectbox("Select mode:", list(MODE_PROMPTS.keys()), index=0)

    # ── Feature Toggles ──────────────────────────────────────────────────
    st.header("Features")
    enable_quiz = st.checkbox("Quiz generation", value=True)
    enable_graph = st.checkbox("Concept graph", value=True)
    enable_diagram = st.checkbox("Diagram", value=True)
    enable_code = st.checkbox("Code generation", value=False)
    enable_plan = st.checkbox("Study plan", value=False)

# ── Main input ────────────────────────────────────────────────────────────
query = st.text_input("Ask a question:")

if query:
    # Invalidate cache when any selection changes
    cache_key = (query, depth, mode, learning_level,
                 enable_quiz, enable_graph, enable_diagram, enable_code, enable_plan)
    if query != st.session_state.get("last_query"):
        st.session_state.pop("last_result", None)
        st.session_state.pop("last_query_opts", None)
        st.session_state["last_query"] = query

    options = {
        "quiz": enable_quiz,
        "concept_graph": enable_graph,
        "diagram": enable_diagram,
        "code": enable_code,
        "study_plan": enable_plan,
        "mode": mode,
        "depth": depth,
        "learning_level": learning_level,
    }

    if "last_result" not in st.session_state or st.session_state.get("last_query_opts") != cache_key:
        with st.spinner("Processing (this may take longer depending on depth and features)..."):
            result = process_question(query, user_id=user_id, options=options)
        st.session_state["last_result"] = result
        st.session_state["last_query_opts"] = cache_key
    else:
        result = st.session_state["last_result"]

    # ── Assembled Text Answer ─────────────────────────────────────────────
    st.markdown(result.get("answer", ""))

    # ── Render Visual Features ────────────────────────────────────────────
    for feature in result.get("feature_results", []):
        f_type = feature.get("type")
        f_title = feature.get("title")
        f_content = feature.get("content")

        if f_type == "diagram":
            st.markdown(f"## {f_title}")
            mermaid_code = f_content.get("mermaid", "")
            if mermaid_code:
                # Render mermaid using HTML component with dark mode detection
                html_code = f"""
                <style>
                    body {{ margin: 0; padding: 0; background: transparent; }}
                    .diagram-container {{
                        display: flex;
                        justify-content: center;
                        padding: 24px;
                        background-color: transparent;
                        border-radius: 12px;
                        border: 1px solid rgba(128, 128, 128, 0.2);
                        overflow-x: auto;
                    }}
                </style>
                <div class="diagram-container">
                    <div class="mermaid">
                        {mermaid_code}
                    </div>
                </div>
                <script type="module">
                    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                    const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                    mermaid.initialize({{ 
                        startOnLoad: true, 
                        theme: isDark ? 'dark' : 'default',
                        fontFamily: 'inherit'
                    }});
                </script>
                """
                components.html(html_code, height=500, scrolling=True)
            else:
                st.warning("Diagram could not be generated.")

        elif f_type == "quiz":
            st.markdown(f"## {f_title}")
            questions = f_content.get("questions", [])
            if not questions:
                st.warning("No questions generated.")
                continue

            for i, q in enumerate(questions):
                diff = q.get("difficulty", "medium")
                diff_class = f"diff-{diff}"
                
                with st.container():
                    st.markdown(f"""
                        <div class="quiz-card">
                            <span class="difficulty-badge {diff_class}">{diff.upper()}</span>
                            <h4>Question {i+1}</h4>
                            <p><b>{q.get("question", "")}</b></p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    q_type = q.get("type")
                    user_ans = None
                    if q_type == "mcq":
                        opts = q.get("options", [])
                        user_ans = st.radio("Select your answer:", opts, key=f"radio_mcq_{i}", index=None)
                    elif q_type == "true_false":
                        user_ans = st.radio("Select your answer:", ["True", "False"], key=f"radio_tf_{i}", index=None)
                    elif q_type == "short_answer":
                        user_ans = st.text_area("Your answer:", key=f"text_sa_{i}")
                        
                    # Reveal Answer button logic
                    reveal_key = f"reveal_q_{i}"
                    if st.button("Check Answer", key=f"btn_{i}"):
                        st.session_state[reveal_key] = True
                        
                    if st.session_state.get(reveal_key, False):
                        correct_ans = str(q.get('answer', '')).strip()
                        if q_type in ["mcq", "true_false"] and user_ans:
                            if str(user_ans).lower() == correct_ans.lower():
                                st.success("✅ Correct!")
                            else:
                                st.error(f"❌ Incorrect. The correct answer is: **{correct_ans}**")
                        else:
                            st.success(f"**Expected Answer:** {correct_ans}")
                            
                        st.info(f"**Explanation:** {q.get('explanation', '')}")
                    st.markdown("<hr/>", unsafe_allow_html=True)

        elif f_type == "concept_graph":
            st.markdown(f"## {f_title}")
            nodes = f_content.get("nodes", [])
            edges = f_content.get("edges", [])
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### Concepts")
                for n in nodes:
                    st.markdown(f"**{n.get('label')}**: {n.get('description')}")
            with col2:
                st.markdown("### Relationships")
                for e in edges:
                    st.markdown(f"- `{e.get('source')}` ➡️ *{e.get('relation')}* ➡️ `{e.get('target')}`")


    # ── Debug / Dev panels ────────────────────────────────────────────────
    st.divider()
    st.subheader("Developer & Debug Panel")

    with st.expander("Orchestrator Metadata & Timing"):
        st.json(result.get("meta", {}))

    with st.expander("Raw Feature Outputs"):
        st.json(result.get("feature_results", []))

    if "memory_update" in result:
        with st.expander("Your Progress"):
            st.json(result["memory_update"])

