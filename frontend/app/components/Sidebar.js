"use client";

import { motion } from "framer-motion";
import { Settings, Sparkles, BookOpen, Brain, Map, Code, BookMarked, Activity, CheckCircle } from "lucide-react";
import clsx from "clsx";

function Toggle({ label, checked, onToggle, icon: Icon }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex items-center justify-between w-full p-3 rounded-xl hover:bg-surfaceHover transition-colors cursor-pointer group"
    >
      <div className="flex items-center gap-3 text-textMuted group-hover:text-textMain transition-colors">
        {Icon && <Icon size={18} className={checked ? "text-primary" : ""} />}
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div className={clsx(
        "w-10 h-[22px] rounded-full transition-colors duration-300 ease-in-out relative flex items-center px-[3px]",
        checked ? "bg-primary" : "bg-surfaceHover border border-border"
      )}>
        <motion.div 
          className="bg-white w-4 h-4 rounded-full shadow-sm"
          animate={{ x: checked ? 16 : 0 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      </div>
    </button>
  );
}

export default function Sidebar({ settings, setSettings, open }) {
  return (
    <motion.aside 
      initial={false}
      animate={{ width: open ? 300 : 0, opacity: open ? 1 : 0 }}
      className="h-full flex-shrink-0 glass-panel border-r border-border overflow-hidden relative flex flex-col z-20"
    >
      <div className="p-6 border-b border-border/50 flex items-center justify-between w-[300px]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg shadow-primary/20">
            <Brain className="text-white" size={22} />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white leading-tight">Neural<span className="text-textMuted font-normal">Learn</span></h1>
            <p className="text-[10px] text-primary uppercase tracking-widest font-semibold">Pro Edition</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide p-4 w-[300px]">
        <div className="space-y-6">
          {/* Level Section */}
          <section>
            <h3 className="text-xs uppercase tracking-wider text-textFaint font-bold mb-3 px-2 flex items-center gap-2">
              <Activity size={12} /> Target Level
            </h3>
            <div className="bg-surface/50 p-1 rounded-xl border border-border flex flex-col gap-1">
              {[
                { id: "beginner", label: "Beginner", icon: BookOpen },
                { id: "intermediate", label: "Intermediate", icon: BookMarked },
                { id: "expert", label: "Expert", icon: Brain }
              ].map(level => (
                <button
                  key={level.id}
                  onClick={() => setSettings({...settings, level: level.id})}
                  className={clsx(
                    "flex items-center gap-3 w-full p-2.5 rounded-lg text-sm font-medium transition-all",
                    settings.level === level.id 
                      ? "bg-primary/10 text-primary" 
                      : "text-textMuted hover:bg-surface hover:text-textMain"
                  )}
                >
                  <level.icon size={16} />
                  {level.label}
                  {settings.level === level.id && (
                    <motion.div layoutId="level-check" className="ml-auto text-primary">
                      <CheckCircle size={14} />
                    </motion.div>
                  )}
                </button>
              ))}
            </div>
          </section>

          {/* Depth Section */}
          <section>
            <h3 className="text-xs uppercase tracking-wider text-textFaint font-bold mb-3 px-2">Analysis Depth</h3>
            <div className="flex bg-surface/50 p-1 rounded-xl border border-border">
              {["fast", "balanced", "deep"].map(d => (
                <button
                  key={d}
                  onClick={() => setSettings({...settings, depth: d})}
                  className={clsx(
                    "flex-1 py-2 text-xs font-semibold rounded-lg capitalize transition-all relative z-10",
                    settings.depth === d ? "text-white" : "text-textMuted hover:text-white"
                  )}
                >
                  {settings.depth === d && (
                    <motion.div layoutId="depth-bg" className="absolute inset-0 bg-surfaceHover border border-border rounded-lg -z-10 shadow-sm" />
                  )}
                  {d}
                </button>
              ))}
            </div>
          </section>

          {/* Features Section */}
          <section>
            <h3 className="text-xs uppercase tracking-wider text-textFaint font-bold mb-3 px-2 flex items-center gap-2">
              <Sparkles size={12} /> Smart Features
            </h3>
            <div className="space-y-1 bg-surface/30 rounded-xl border border-border/50 p-2">
              <Toggle label="Interactive Quizzes" icon={CheckCircle} checked={settings.quiz} onToggle={() => setSettings({...settings, quiz: !settings.quiz})} />
              <Toggle label="Architecture Diagrams" icon={Map} checked={settings.diagram} onToggle={() => setSettings({...settings, diagram: !settings.diagram})} />
              <Toggle label="Concept Graphs" icon={Brain} checked={settings.concept_graph} onToggle={() => setSettings({...settings, concept_graph: !settings.concept_graph})} />
              <Toggle label="Code Examples" icon={Code} checked={settings.code} onToggle={() => setSettings({...settings, code: !settings.code})} />
              <Toggle label="Study Roadmaps" icon={Activity} checked={settings.study_plan} onToggle={() => setSettings({...settings, study_plan: !settings.study_plan})} />
            </div>
          </section>
        </div>
      </div>

      <div className="p-4 border-t border-border/50 bg-surface/30 w-[300px]">
        <button className="flex items-center gap-3 w-full p-3 rounded-xl hover:bg-surface transition-colors text-textMuted hover:text-white text-sm font-medium">
          <Settings size={18} />
          <span>Advanced Settings</span>
        </button>
      </div>
    </motion.aside>
  );
}
