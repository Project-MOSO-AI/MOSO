import { useState, useRef, useEffect } from 'react';
import { Mic, Paperclip, Send } from 'lucide-react';
import { StatusDot } from '../shared/StatusDot';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ActivityItem {
  id: string;
  type: 'thinking' | 'searching' | 'calling_tool' | 'finished';
  label: string;
}

interface AuraPanelProps {
  messages: ChatMessage[];
  isListening: boolean;
  isThinking: boolean;
  activityFeed: ActivityItem[];
  onSendMessage: (text: string) => void;
  onToggleVoice: () => void;
  onFileUpload: () => void;
  orbState: 'idle' | 'listening' | 'thinking' | 'speaking';
}

const MOCK_MESSAGES: ChatMessage[] = [
  { id: '1', role: 'user', content: 'How can I help you today?', timestamp: '22:14' },
];

const MOCK_ACTIVITY: ActivityItem[] = [
  { id: '1', type: 'thinking', label: 'Thinking...' },
  { id: '2', type: 'searching', label: 'Searching Memory' },
  { id: '3', type: 'calling_tool', label: 'Calling Tool' },
  { id: '4', type: 'finished', label: 'Agent Finished' },
];

export function AuraPanel({ messages, isListening, isThinking, activityFeed, onSendMessage, onToggleVoice, onFileUpload, orbState }: AuraPanelProps) {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const displayMessages = messages.length > 0 ? messages : MOCK_MESSAGES;
  const displayActivity = activityFeed.length > 0 ? activityFeed : MOCK_ACTIVITY;

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayMessages]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const orbColors = {
    idle: 'from-moso-purple to-moso-blue',
    listening: 'from-red-500 to-moso-purple',
    thinking: 'from-moso-purple to-moso-blue',
    speaking: 'from-moso-blue to-moso-purple',
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-moso-bg/20">
      {/* AURA Header */}
      <div className="px-4 pt-3 pb-2">
        <h2 className="text-[11px] font-semibold text-moso-text-dim uppercase tracking-wider">🧠 AURA</h2>
      </div>

      {/* Orb + Chat Area */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Orb Section */}
        <div className="flex flex-col items-center py-4 gap-3">
          <div className="relative w-20 h-20 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border border-moso-purple/20 animate-rotate-slow" />
            <div className="absolute inset-2 rounded-full border border-moso-blue/15 animate-rotate-slow" style={{ animationDirection: 'reverse', animationDuration: '15s' }} />

            <div className={`w-14 h-14 rounded-full bg-gradient-to-br ${orbColors[orbState]} flex items-center justify-center animate-pulse-glow relative`}>
              <div className="w-3 h-3 rounded-full bg-white/80" />
            </div>

            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="absolute w-1.5 h-1.5 rounded-full bg-moso-purple/40"
                style={{
                  animation: `orbit ${8 + i * 2}s linear infinite`,
                  animationDelay: `${i * -2}s`,
                }}
              />
            ))}
          </div>

          <div className="flex items-center gap-1.5">
            <StatusDot status={isListening ? 'active' : isThinking ? 'thinking' : 'idle'} size={5} />
            <span className="text-[10px] text-moso-text-dim">
              {orbState === 'listening' ? '🎙 Listening...' :
               orbState === 'thinking' ? '🧠 Thinking...' :
               orbState === 'speaking' ? '🔊 Speaking...' : '🎙 Listening...'}
            </span>
          </div>

          <p className="text-xs text-moso-text-muted italic">"How can I help you today?"</p>
        </div>

        <div className="h-px bg-moso-border mx-4" />

        {/* Chat Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {displayMessages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-xl px-3 py-2 ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-moso-purple to-moso-blue text-white text-xs'
                  : 'glass border border-moso-border text-xs text-moso-text'
              }`}>
                <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}

          {isThinking && (
            <div className="flex justify-start">
              <div className="glass border border-moso-border rounded-xl px-3 py-2">
                <div className="flex items-center gap-2">
                  <ThinkingDots />
                  <span className="text-[10px] text-moso-text-dim">Thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Activity Feed */}
        <div className="px-4 py-2">
          <div className="text-[10px] text-moso-text-muted mb-1.5">Activity Feed</div>
          <div className="flex flex-col gap-1">
            {displayActivity.map(item => (
              <div key={item.id} className="flex items-center gap-2 text-[11px] text-moso-text-dim">
                <div className={`w-1.5 h-1.5 rounded-full ${
                  item.type === 'thinking' ? 'bg-moso-purple animate-pulse' :
                  item.type === 'searching' ? 'bg-moso-blue' :
                  item.type === 'calling_tool' ? 'bg-moso-warning' :
                  'bg-moso-success'
                }`} />
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Input Bar */}
      <div className="px-4 pb-3">
        <div className="glass rounded-xl border border-moso-border p-2 flex items-center gap-2">
          <button
            onClick={onToggleVoice}
            className={`p-2 rounded-lg transition-colors ${
              isListening ? 'bg-moso-danger/20 text-moso-danger' : 'hover:bg-moso-surface-2 text-moso-text-muted'
            }`}
            title="Voice"
          >
            <Mic size={15} />
          </button>

          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Type a message..."
            className="flex-1 bg-transparent text-xs text-moso-text placeholder:text-moso-text-muted outline-none"
          />

          <button
            onClick={onFileUpload}
            className="p-2 rounded-lg hover:bg-moso-surface-2 transition-colors text-moso-text-muted"
            title="Files"
          >
            <Paperclip size={15} />
          </button>

          <button
            onClick={handleSend}
            className="p-2 rounded-lg bg-gradient-to-r from-moso-purple to-moso-blue text-white hover:opacity-90 transition-opacity"
          >
            <Send size={15} />
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
          className="w-1 h-1 rounded-full bg-moso-purple"
          style={{
            animation: 'wave 1.2s ease-in-out infinite',
            animationDelay: `${i * 0.15}s`,
          }}
        />
      ))}
    </div>
  );
}
