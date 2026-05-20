"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { Bot, User, Menu } from "lucide-react";
import clsx from "clsx";

import Sidebar from "./components/Sidebar";
import Hero from "./components/Hero";
import ChatInput from "./components/ChatInput";
import FeatureRenderer from "./components/FeatureRenderer";

function Loader() {
  return (
    <div className="flex items-center gap-2 p-3 text-textMuted">
      <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
      <div className="w-2 h-2 rounded-full bg-primary animate-pulse" style={{ animationDelay: "150ms" }} />
      <div className="w-2 h-2 rounded-full bg-primary animate-pulse" style={{ animationDelay: "300ms" }} />
      <span className="text-xs ml-1 font-medium tracking-wide">Synthesizing knowledge...</span>
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const bottomRef = useRef(null);

  // Settings State
  const [settings, setSettings] = useState({
    mode: "explain",
    depth: "balanced",
    level: "beginner",
    quiz: true,
    diagram: true,
    concept_graph: false,
    code: false,
    study_plan: false,
  });

  // Auto-scroll logic
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Handle mobile sidebar on mount
  useEffect(() => {
    if (window.innerWidth < 768) setSidebarOpen(false);
  }, []);

  async function handleSubmit(e, queryText = null) {
    if (e) e.preventDefault();
    const query = queryText || input.trim();
    if (!query || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          query,
          options: {
            mode: settings.mode,
            depth: settings.depth,
            learning_level: settings.level,
            quiz: settings.quiz,
            diagram: settings.diagram,
            concept_graph: settings.concept_graph,
            code: settings.code,
            study_plan: settings.study_plan,
          }
        }),
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      setMessages((prev) => [...prev, { role: "assistant", content: "", features: [] }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        for (const line of text.split("\n")) {
          if (!line.trim()) continue;
          try {
            const parsed = JSON.parse(line);
            if (parsed.chunk) {
              accumulated += parsed.chunk;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: accumulated,
                };
                return updated;
              });
            } else if (parsed.features) {
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  features: parsed.features,
                };
                return updated;
              });
            } else if (parsed.error) {
               setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: accumulated + `\n\n> ⚠️ Error: ${parsed.error}`,
                };
                return updated;
              });
            }
          } catch (e) {
             // skip malformed JSON chunks from streaming
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `> ⚠️ Connection Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden font-sans">
      
      <Sidebar settings={settings} setSettings={setSettings} open={sidebarOpen} />

      <main className="flex-1 flex flex-col relative min-w-0">
        
        {/* Header / Sidebar Toggle */}
        <div className="absolute top-0 left-0 right-0 p-4 z-20 flex justify-between items-center pointer-events-none">
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)} 
            className="p-2.5 rounded-xl bg-surface/80 backdrop-blur-md border border-border text-textMuted hover:text-white hover:bg-surfaceHover transition-colors pointer-events-auto shadow-sm"
          >
            <Menu size={20} />
          </button>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto scrollbar-hide px-4 sm:px-6 lg:px-8 pt-20 pb-40 z-10">
          <div className="max-w-4xl mx-auto w-full flex flex-col gap-8">
            
            {messages.length === 0 && (
              <Hero onSelect={(text) => handleSubmit(null, text)} />
            )}

            {messages.map((msg, i) => (
              <motion.div 
                key={i} 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={clsx(
                  "flex gap-4 md:gap-6 w-full group",
                  msg.role === "user" ? "flex-row-reverse" : "flex-row"
                )}
              >
                {/* Avatar */}
                <div className={clsx(
                  "w-8 h-8 md:w-10 md:h-10 rounded-2xl flex-shrink-0 flex items-center justify-center shadow-sm",
                  msg.role === "user" 
                    ? "bg-surface border border-border" 
                    : "bg-gradient-to-br from-primary to-secondary shadow-primary/20"
                )}>
                  {msg.role === "user" ? <User size={18} className="text-textMuted" /> : <Bot size={20} className="text-white" />}
                </div>

                {/* Content */}
                <div className={clsx(
                  "flex flex-col min-w-0 flex-1",
                  msg.role === "user" ? "items-end" : "items-start"
                )}>
                  <div className="text-xs font-semibold text-textMuted mb-2 tracking-wide uppercase">
                    {msg.role === "user" ? "You" : "NeuralLearn AI"}
                  </div>
                  
                  {msg.role === "user" ? (
                    <div className="bg-surfaceHover border border-border px-5 py-3.5 rounded-2xl rounded-tr-sm text-[15px] leading-relaxed text-white max-w-[85%]">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="w-full">
                      <div className="markdown-body">
                        {msg.content ? <ReactMarkdown>{msg.content}</ReactMarkdown> : null}
                      </div>
                      
                      {msg.features && msg.features.length > 0 && (
                        <div className="mt-8 pt-6 border-t border-border/50">
                          {msg.features.map((f, idx) => (
                            <FeatureRenderer key={idx} feature={f} />
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
            
            {loading && messages[messages.length - 1]?.role === "user" && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-4 md:gap-6 w-full"
              >
                <div className="w-8 h-8 md:w-10 md:h-10 rounded-2xl flex-shrink-0 flex items-center justify-center bg-gradient-to-br from-primary to-secondary shadow-primary/20">
                  <Bot size={20} className="text-white" />
                </div>
                <div className="flex-1">
                  <div className="text-xs font-semibold text-textMuted mb-2 tracking-wide uppercase">NeuralLearn AI</div>
                  <Loader />
                </div>
              </motion.div>
            )}
            
            <div ref={bottomRef} className="h-4" />
          </div>
        </div>

        <ChatInput 
          input={input} 
          setInput={setInput} 
          onSubmit={handleSubmit} 
          loading={loading} 
        />

      </main>
    </div>
  );
}
