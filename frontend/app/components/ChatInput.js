"use client";

import { motion } from "framer-motion";
import { ArrowUp, Paperclip, Mic } from "lucide-react";
import clsx from "clsx";

export default function ChatInput({ input, setInput, onSubmit, loading }) {
  return (
    <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-background via-background to-transparent z-10 flex justify-center pb-8">
      <motion.form 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        onSubmit={onSubmit} 
        className="w-full max-w-4xl relative"
      >
        <div className="relative group">
          {/* Subtle glow border effect */}
          <div className="absolute -inset-0.5 bg-gradient-to-r from-primary to-secondary rounded-2xl opacity-20 group-hover:opacity-40 transition duration-500 blur" />
          
          <div className="relative flex items-center bg-surface/80 backdrop-blur-xl border border-border rounded-2xl px-4 py-3 shadow-2xl transition-colors focus-within:border-primary/50 focus-within:bg-surface">
            
            {/* Action Buttons Left */}
            <div className="flex items-center gap-2 mr-3">
              <button type="button" className="p-2 text-textFaint hover:text-white transition-colors rounded-lg hover:bg-white/5">
                <Paperclip size={20} />
              </button>
            </div>

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message NeuralLearn..."
              disabled={loading}
              className="flex-1 bg-transparent border-none outline-none text-textMain placeholder-textFaint resize-none max-h-48 min-h-[24px] py-2 overflow-y-auto"
              rows={1}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  onSubmit(e);
                }
              }}
            />

            {/* Action Buttons Right */}
            <div className="flex items-center gap-2 ml-3">
              <button type="button" className="p-2 text-textFaint hover:text-white transition-colors rounded-lg hover:bg-white/5 hidden sm:block">
                <Mic size={20} />
              </button>
              
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className={clsx(
                  "p-2.5 rounded-xl flex items-center justify-center transition-all",
                  input.trim() && !loading
                    ? "bg-white text-black hover:bg-gray-200 hover:scale-105 active:scale-95 shadow-lg shadow-white/10"
                    : "bg-surfaceHover text-textFaint cursor-not-allowed border border-border"
                )}
              >
                <ArrowUp size={18} strokeWidth={3} />
              </button>
            </div>
          </div>
        </div>
        
        <div className="text-center mt-3">
          <p className="text-[10px] text-textFaint">
            NeuralLearn can make mistakes. Consider verifying important academic information.
          </p>
        </div>
      </motion.form>
    </div>
  );
}
