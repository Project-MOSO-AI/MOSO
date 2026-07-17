import { useState, useCallback, useRef, useEffect } from 'react';
import type { ChatMessage, ActivityItem } from '../components/panels/AuraPanel';
import type { LogEntry } from '../components/panels/LogPanel';

const API_URL = import.meta.env.VITE_MOSO_API_URL || 'http://localhost:8000';

export function useMosoApi() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [logs] = useState<LogEntry[]>([]);
  const [activityFeed, setActivityFeed] = useState<ActivityItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [currentExplanation, setCurrentExplanation] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [orbState, setOrbState] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle');
  const [status, setStatus] = useState<'live' | 'degraded' | 'offline'>('offline');
  const [memorySynced] = useState(true);
  const [localMode] = useState(true);
  const [offlineReady] = useState(true);
  const [encrypted] = useState(true);
  const [systemStats, setSystemStats] = useState({ cpu: 18, gpu: 12, ram: '7.2GB' });

  const wsRef = useRef<WebSocket | null>(null);
  const msgId = useRef(0);

  // Health check polling
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API_URL}/health`);
        if (res.ok) {
          const data = await res.json();
          setStatus(data.status === 'healthy' ? 'live' : 'degraded');
        } else {
          setStatus('offline');
        }
      } catch {
        setStatus('offline');
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  // System stats polling
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_URL}/system`);
        if (res.ok) {
          const data = await res.json();
          if (data.cpu_percent !== undefined) {
            setSystemStats({
              cpu: Math.round(data.cpu_percent),
              gpu: 0,
              ram: `${(data.ram_used_gb || 7.2).toFixed(1)}GB`,
            });
          }
        }
      } catch { /* offline mode */ }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket for streaming responses
  useEffect(() => {
    if (status === 'offline') return;

    const connect = () => {
      try {
        const ws = new WebSocket(API_URL.replace('http', 'ws') + '/ws');
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'chat') {
              appendMessage('assistant', data.content);
              setIsThinking(false);
              setOrbState('idle');
            } else if (data.type === 'activity') {
              addActivity(data.activity_type, data.label);
            }
          } catch { /* ignore parse errors */ }
        };
        ws.onclose = () => setTimeout(connect, 5000);
        wsRef.current = ws;
      } catch { /* ws not available */ }
    };
    connect();

    return () => { wsRef.current?.close(); };
  }, [status]);

  const appendMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    const msg: ChatMessage = {
      id: String(++msgId.current),
      role,
      content,
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
    };
    setMessages(prev => [...prev, msg]);
  }, []);

  const addActivity = useCallback((type: ActivityItem['type'], label: string) => {
    const item: ActivityItem = {
      id: String(++msgId.current),
      type,
      label,
    };
    setActivityFeed(prev => [...prev.slice(-5), item]);
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    appendMessage('user', text);
    setIsThinking(true);
    setOrbState('thinking');
    addActivity('thinking', 'Thinking...');

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      if (res.ok) {
        const data = await res.json();
        appendMessage('assistant', data.response);
        addActivity('finished', 'Agent Finished');
      } else {
        appendMessage('assistant', '(Backend unavailable — running in local mode)');
      }
    } catch {
      appendMessage('assistant', '(Cannot reach MOSO backend at ' + API_URL + ')');
    } finally {
      setIsThinking(false);
      setOrbState('idle');
    }
  }, [appendMessage, addActivity]);

  const toggleVoice = useCallback(() => {
    setIsListening(prev => !prev);
    setOrbState(prev => prev === 'listening' ? 'idle' : 'listening');
  }, []);

  const uploadFile = useCallback(() => {
    // ponytail: placeholder, add when file upload is needed
  }, []);

  const selectLog = useCallback((log: LogEntry) => {
    setSelectedLog(log);
    setCurrentExplanation(`Analysis of "${log.title}" — the ${log.title.toLowerCase()} module is part of MOSO's ${log.tags.join(', ')} subsystem(s). Select different tabs above to view flowcharts, tables, graphs, or code.`);
  }, []);

  return {
    messages,
    logs,
    activityFeed,
    searchQuery,
    setSearchQuery,
    activeFilter,
    setActiveFilter,
    selectedLog,
    selectLog,
    currentExplanation,
    isListening,
    isThinking,
    orbState,
    status,
    systemStats,
    memorySynced,
    localMode,
    offlineReady,
    encrypted,
    sendMessage,
    toggleVoice,
    uploadFile,
  };
}
