"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from 'react-markdown';
import mermaid from 'mermaid';
import { 
  CheckCircle2, XCircle, ChevronDown, ChevronUp, Map, Code, 
  Brain, FileText, LayoutTemplate, Activity 
} from "lucide-react";
import clsx from "clsx";

function Badge({ children, variant = "default" }) {
  const styles = {
    default: "bg-surfaceHover text-textMuted border border-border",
    success: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    error: "bg-rose-500/10 text-rose-400 border border-rose-500/20",
    primary: "bg-primary/15 text-primary border border-primary/30"
  };
  
  return (
    <span className={clsx("inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider", styles[variant] || styles.default)}>
      {children}
    </span>
  );
}

// --- Specific Renderers ---

function QuizCard({ q, index }) {
  const [revealed, setRevealed] = useState(false);
  const [selectedOpt, setSelectedOpt] = useState(null);

  const diffVariant = q.difficulty === "expert" ? "error" : q.difficulty === "intermediate" ? "warning" : "success";

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="glass-card p-5 mb-4 group"
    >
      <div className="flex justify-between items-center mb-3">
        <h4 className="text-xs uppercase tracking-widest text-textFaint font-bold">
          Question {index + 1}
        </h4>
        <Badge variant={diffVariant}>{q.difficulty}</Badge>
      </div>
      
      <p className="text-[15px] font-medium text-textMain mb-4 leading-snug">
        {q.question}
      </p>
      
      {(q.type === "mcq" || q.type === "true_false") && (
        <div className="space-y-2 mb-5">
          {q.options?.map((opt, i) => {
            const isSelected = selectedOpt === opt;
            const isCorrect = revealed && opt === q.answer;
            const isWrong = revealed && isSelected && opt !== q.answer;
            
            let stateClass = "bg-white/[0.02] border-border hover:bg-surfaceHover text-textMain";
            if (isCorrect) stateClass = "bg-emerald-500/10 border-emerald-500/50 text-emerald-400";
            else if (isWrong) stateClass = "bg-rose-500/10 border-rose-500/50 text-rose-400";
            else if (isSelected) stateClass = "bg-primary/10 border-primary/50 text-primary";

            return (
              <label key={i} className={clsx(
                "flex items-center p-3 rounded-xl border transition-all cursor-pointer",
                stateClass,
                revealed && !isCorrect && !isWrong && "opacity-50 cursor-default"
              )}>
                <input 
                  type="radio" name={`q_${index}`} value={opt}
                  onChange={(e) => !revealed && setSelectedOpt(e.target.value)}
                  disabled={revealed}
                  className="mr-3 w-4 h-4 accent-primary"
                />
                <span className="text-sm font-medium">{opt}</span>
                {isCorrect && <CheckCircle2 className="ml-auto w-5 h-5 text-emerald-500" />}
                {isWrong && <XCircle className="ml-auto w-5 h-5 text-rose-500" />}
              </label>
            );
          })}
        </div>
      )}

      {q.type === "short_answer" && (
        <textarea 
          className="w-full min-h-[80px] p-3 rounded-xl bg-surface/50 border border-border text-textMain mb-4 focus:border-primary/50 outline-none resize-y transition-colors text-sm"
          placeholder="Type your answer here..."
          onChange={(e) => setSelectedOpt(e.target.value)}
          disabled={revealed}
        />
      )}

      <button 
        onClick={() => setRevealed(!revealed)}
        className={clsx(
          "px-4 py-2 rounded-lg font-medium text-sm transition-all w-full md:w-auto",
          revealed 
            ? "bg-surfaceHover text-textMuted hover:text-white" 
            : "bg-primary text-white hover:bg-primary/90 shadow-lg shadow-primary/20"
        )}
      >
        {revealed ? "Hide Explanation" : "Check Answer"}
      </button>

      <AnimatePresence>
        {revealed && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-4 p-4 rounded-xl bg-primary/5 border-l-4 border-primary">
              {selectedOpt && (q.type === "mcq" || q.type === "true_false") ? (
                selectedOpt === q.answer ? (
                  <p className="text-emerald-400 font-bold mb-2 flex items-center gap-2"><CheckCircle2 size={16}/> Outstanding!</p>
                ) : (
                  <p className="text-rose-400 font-bold mb-2 flex items-center gap-2"><XCircle size={16}/> Not quite. The correct answer is: {q.answer}</p>
                )
              ) : (
                <p className="mb-2 text-sm"><strong>Expected Answer:</strong> {q.answer}</p>
              )}
              <p className="text-textMuted text-sm leading-relaxed">
                {q.explanation}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function MermaidDiagram({ code }) {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!code) return;
    
    let cancelled = false;

    // Generate a unique ID for each render attempt
    const renderID = `mmd-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;

    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      fontFamily: 'Inter, sans-serif',
      securityLevel: 'loose',
      themeVariables: {
        primaryColor: '#3b82f6',
        primaryTextColor: '#fff',
        primaryBorderColor: '#3b82f6',
        lineColor: '#52525b',
        secondaryColor: '#1a1a1a',
        tertiaryColor: '#0d0d0d',
        background: '#0d0d0d',
        mainBkg: '#1a1a1a',
        nodeBorder: '#3b82f6',
        fontFamily: 'Inter, sans-serif',
      }
    });

    mermaid.render(renderID, code)
      .then((result) => {
        if (!cancelled) {
          setSvg(result.svg);
          setError("");
        }
      })
      .catch((err) => {
        console.error("Mermaid render error:", err);
        if (!cancelled) {
          setSvg("");
          setError(err?.message || "Failed to render diagram");
        }
        // Clean up the temp element mermaid creates on error
        const errEl = document.getElementById('d' + renderID);
        if (errEl) errEl.remove();
      });

    return () => { cancelled = true; };
  }, [code]);

  if (!code) {
    return <div className="p-6 bg-surface/30 rounded-2xl border border-border text-center text-textMuted text-sm">No diagram data received.</div>;
  }

  return (
    <div className="p-6 bg-surface/30 rounded-2xl border border-border overflow-x-auto flex flex-col items-center shadow-inner">
      {svg ? (
        <div className="w-full flex justify-center" dangerouslySetInnerHTML={{ __html: svg }} />
      ) : error ? (
        <div className="w-full">
          <p className="text-rose-400 font-medium text-sm mb-3">⚠ Diagram render error: {error}</p>
          <pre className="text-[11px] bg-black/50 p-4 rounded-lg text-left overflow-x-auto border border-border/50 text-textMuted">
            <code>{code}</code>
          </pre>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-textMuted text-sm py-4">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          Rendering diagram...
        </div>
      )}
      
      {svg && (
        <details className="mt-4 w-full cursor-pointer text-textMuted text-xs">
          <summary className="hover:text-primary transition-colors">Show raw Mermaid code</summary>
          <pre className="mt-2 p-3 bg-black/50 rounded-lg overflow-x-auto text-left border border-border/50">
            <code>{code}</code>
          </pre>
        </details>
      )}
    </div>
  );
}

export default function FeatureRenderer({ feature }) {
  if (!feature || !feature.type) return null;

  const FeatureWrapper = ({ title, icon: Icon, children }) => (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-8 mb-4 w-full"
    >
      <h3 className="flex items-center gap-2 text-white font-bold mb-4 text-lg">
        <div className="p-1.5 rounded-lg bg-surfaceHover border border-border text-primary">
          <Icon size={18} />
        </div>
        {title}
      </h3>
      {children}
    </motion.div>
  );

  if (feature.type === "quiz") {
    const questions = feature.content?.questions || [];
    if (!questions.length) return null;
    return (
      <FeatureWrapper title={feature.title} icon={LayoutTemplate}>
        {questions.map((q, i) => <QuizCard key={i} q={q} index={i} />)}
      </FeatureWrapper>
    );
  }
  
  if (feature.type === "diagram") {
    return (
      <FeatureWrapper title={feature.title} icon={Map}>
        <MermaidDiagram code={feature.content?.mermaid} />
      </FeatureWrapper>
    );
  }

  if (feature.type === "concept_graph") {
    const nodes = feature.content?.nodes || [];
    const edges = feature.content?.edges || [];
    if (!nodes.length) return null;
    return (
      <FeatureWrapper title={feature.title} icon={Brain}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="glass-card p-5">
            <h4 className="text-xs uppercase tracking-widest text-textFaint font-bold mb-4 flex items-center gap-2"><CheckCircle2 size={12}/> Concepts</h4>
            <div className="space-y-3">
              {nodes.map((n, i) => (
                <div key={i} className="pb-3 border-b border-border last:border-0 last:pb-0">
                  <strong className="text-primary text-sm">{n.label}</strong>
                  <p className="text-[13px] text-textMuted mt-1">{n.description}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="glass-card p-5">
            <h4 className="text-xs uppercase tracking-widest text-textFaint font-bold mb-4 flex items-center gap-2"><Activity size={12}/> Relationships</h4>
            <div className="space-y-2">
              {edges.map((e, i) => (
                <div key={i} className="flex items-center gap-2 flex-wrap bg-surface/50 p-2 rounded-lg border border-border">
                  <Badge variant="primary">{e.source}</Badge>
                  <span className="text-textFaint text-xs">→</span>
                  <span className="text-amber-400/80 italic text-xs font-medium">{e.relation}</span>
                  <span className="text-textFaint text-xs">→</span>
                  <Badge variant="primary">{e.target}</Badge>
                </div>
              ))}
            </div>
          </div>
        </div>
      </FeatureWrapper>
    );
  }

  if (feature.type === "code") {
    return (
      <FeatureWrapper title={feature.title} icon={Code}>
        <div className="rounded-2xl border border-border overflow-hidden shadow-lg">
          <div className="bg-surface border-b border-border px-4 py-2 flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-rose-500/80" />
            <div className="w-3 h-3 rounded-full bg-amber-500/80" />
            <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
            <span className="ml-2 text-xs font-mono text-textFaint">snippet.py</span>
          </div>
          <pre className="bg-[#0d1117] p-5 overflow-x-auto text-sm leading-relaxed text-[#c9d1d9] font-mono">
            <code>{feature.content?.code}</code>
          </pre>
        </div>
        {feature.content?.code_explanation && (
          <div className="glass-card p-5 mt-4">
            <h4 className="text-xs uppercase tracking-widest text-textFaint font-bold mb-2">Explanation</h4>
            <div className="markdown-body text-sm">
              <ReactMarkdown>{feature.content.code_explanation}</ReactMarkdown>
            </div>
          </div>
        )}
      </FeatureWrapper>
    );
  }

  if (feature.type === "study_plan") {
    const modules = Array.isArray(feature.content) ? feature.content : [];
    if (!modules.length) return null;
    return (
      <FeatureWrapper title={feature.title} icon={FileText}>
        <div className="space-y-3 relative">
          <div className="absolute left-[19px] top-4 bottom-4 w-px bg-border z-0 hidden md:block" />
          {modules.map((mod, i) => (
            <motion.div 
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              key={i} 
              className="glass-card p-5 relative z-10 flex flex-col md:flex-row gap-4 group"
            >
              <div className="hidden md:flex w-10 h-10 rounded-full bg-surface border-2 border-primary items-center justify-center text-primary font-bold shadow-lg shrink-0 group-hover:bg-primary group-hover:text-white transition-colors">
                {mod.module}
              </div>
              <div className="flex-1">
                <div className="flex flex-wrap justify-between items-start gap-2 mb-2">
                  <h4 className="text-base font-bold text-white flex items-center gap-2">
                    <span className="md:hidden text-primary">#{mod.module}</span>
                    {mod.title}
                  </h4>
                  <div className="flex gap-2">
                    <Badge variant={mod.difficulty === "hard" ? "error" : mod.difficulty === "medium" ? "warning" : "success"}>{mod.difficulty}</Badge>
                    <Badge variant="default">~{mod.estimated_hours}h</Badge>
                  </div>
                </div>
                <p className="text-sm text-textMuted mb-3">{mod.description}</p>
                {mod.subtopics?.length > 0 && (
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                    {mod.subtopics.map((s, j) => (
                      <li key={j} className="text-[13px] text-textMuted flex items-start gap-2">
                        <span className="text-primary mt-1">•</span> {s}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </FeatureWrapper>
    );
  }

  return null;
}
