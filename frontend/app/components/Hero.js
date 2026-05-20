"use client";

import { motion } from "framer-motion";
import { Sparkles, ArrowRight, Zap, Code, Network } from "lucide-react";

const SUGGESTIONS = [
  { icon: Network, text: "Explain Neural Networks architecture", color: "text-blue-400", bg: "bg-blue-400/10" },
  { icon: Code, text: "Write a React component for a dashboard", color: "text-purple-400", bg: "bg-purple-400/10" },
  { icon: Zap, text: "How does backpropagation work?", color: "text-amber-400", bg: "bg-amber-400/10" },
];

export default function Hero({ onSelect }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] w-full max-w-4xl mx-auto px-6 relative">
      {/* Background glow */}
      <div className="absolute inset-0 bg-hero-glow -z-10 animate-pulse-slow" />
      
      {/* Orb Animation */}
      <motion.div 
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 1, ease: "easeOut" }}
        className="relative w-32 h-32 mb-12"
      >
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary to-secondary blur-2xl opacity-40 animate-glow" />
        <div className="absolute inset-2 rounded-full bg-gradient-to-tr from-surface to-background border border-border flex items-center justify-center">
          <Sparkles className="text-primary w-10 h-10 animate-float" />
        </div>
      </motion.div>

      {/* Typography */}
      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="text-center space-y-4 mb-16"
      >
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white">
          What do you want to <span className="text-gradient">master</span> today?
        </h1>
        <p className="text-lg text-textMuted max-w-2xl mx-auto">
          An intelligent learning environment that adapts to your level. Ask questions, generate interactive diagrams, and test your knowledge in real-time.
        </p>
      </motion.div>

      {/* Suggestion Cards */}
      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full"
      >
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelect(s.text)}
            className="group glass-card p-4 flex flex-col gap-3 text-left hover:border-primary/50 transition-all"
          >
            <div className={`w-8 h-8 rounded-lg ${s.bg} ${s.color} flex items-center justify-center`}>
              <s.icon size={16} />
            </div>
            <p className="text-sm font-medium text-textMain group-hover:text-white transition-colors">
              "{s.text}"
            </p>
            <div className="mt-auto flex items-center text-xs text-textFaint group-hover:text-primary transition-colors font-semibold uppercase tracking-wider">
              Try this <ArrowRight size={12} className="ml-1" />
            </div>
          </button>
        ))}
      </motion.div>
    </div>
  );
}
