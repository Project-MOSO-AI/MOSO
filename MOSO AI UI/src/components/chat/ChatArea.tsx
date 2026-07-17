import { useRef, useEffect } from 'react';
import { Send, Paperclip, Mic, Sparkles } from 'lucide-react';

const messages = [
  {
    role: 'user',
    content: 'Can you analyze the performance bottleneck in the authentication module?',
  },
  {
    role: 'assistant',
    content: "I've identified the bottleneck. The JWT validation middleware is making redundant database calls on every request. Here's my analysis:",
    tools: [
      { name: 'code_analysis', status: 'complete' as const, result: 'Found N+1 query pattern' },
      { name: 'file_read', status: 'complete' as const, result: 'auth/middleware.ts' },
      { name: 'memory_search', status: 'complete' as const, result: 'Cached validation patterns' },
    ],
  },
  {
    role: 'assistant',
    content: "**Root Cause:** The `validateToken` function queries the database for each request instead of using the Redis cache that's already configured.\n\n**Recommendation:** Add cache-first lookup with a 5-minute TTL before falling back to the database. This should reduce DB load by ~80%.",
  },
];

export function ChatArea() {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-moso-purple to-moso-blue text-white'
                  : 'glass border border-moso-border text-moso-text'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-1.5 mb-2">
                  <Sparkles size={12} className="text-moso-purple" />
                  <span className="text-[10px] text-moso-purple font-medium">MOSO</span>
                </div>
              )}
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>

              {msg.tools && (
                <div className="mt-3 flex flex-col gap-1.5">
                  {msg.tools.map((tool) => (
                    <div key={tool.name} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-moso-bg/50 border border-moso-border">
                      <div className="w-1.5 h-1.5 rounded-full bg-moso-success" />
                      <span className="text-[10px] text-moso-text-muted">{tool.name}</span>
                      <span className="text-[10px] text-moso-text-dim ml-auto">{tool.result}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        <div className="flex justify-start">
          <div className="glass border border-moso-border rounded-2xl px-4 py-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Sparkles size={12} className="text-moso-purple" />
              <span className="text-[10px] text-moso-purple font-medium">MOSO</span>
            </div>
            <div className="flex items-center gap-2">
              <ThinkingDots />
              <span className="text-xs text-moso-text-dim">Thinking...</span>
            </div>
          </div>
        </div>
      </div>

      <VoiceWaveform />

      <div className="px-6 pb-4">
        <div className="glass rounded-2xl border border-moso-border p-3 flex items-center gap-3">
          <button className="p-2 rounded-xl hover:bg-moso-surface-2 transition-colors">
            <Paperclip size={16} className="text-moso-text-muted" />
          </button>
          <input
            type="text"
            placeholder="Ask MOSO anything..."
            className="flex-1 bg-transparent text-sm text-moso-text placeholder:text-moso-text-muted outline-none"
          />
          <button className="p-2 rounded-xl hover:bg-moso-surface-2 transition-colors">
            <Mic size={16} className="text-moso-text-muted" />
          </button>
          <button className="p-2 rounded-xl bg-gradient-to-r from-moso-purple to-moso-blue text-white hover:opacity-90 transition-opacity">
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-moso-purple"
          style={{
            animation: 'wave 1.2s ease-in-out infinite',
            animationDelay: `${i * 0.15}s`,
          }}
        />
      ))}
    </div>
  );
}

function VoiceWaveform() {
  return (
    <div className="px-6 py-2">
      <div className="flex items-center gap-1 h-8 justify-center">
        {Array.from({ length: 32 }).map((_, i) => (
          <div
            key={i}
            className="w-1 rounded-full bg-gradient-to-t from-moso-purple/20 to-moso-purple/60"
            style={{
              animation: `wave ${0.8 + Math.random() * 0.8}s ease-in-out infinite`,
              animationDelay: `${i * 0.05}s`,
              height: `${4 + Math.random() * 20}px`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
