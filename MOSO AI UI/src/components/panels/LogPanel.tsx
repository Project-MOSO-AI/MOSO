import { useState } from 'react';
import { Search, ChevronDown, ChevronRight } from 'lucide-react';

export interface LogEntry {
  id: string;
  title: string;
  icon: string;
  date: string;
  tags: string[];
}

interface LogPanelProps {
  logs: LogEntry[];
  searchQuery: string;
  onSearchChange: (q: string) => void;
  activeFilter: string;
  onFilterChange: (f: string) => void;
  onLogSelect: (log: LogEntry) => void;
}

const FILTERS = ['Flutter', 'Vision', 'AI', 'Code', 'Design', 'Memory'];

const MOCK_LOGS: LogEntry[] = [
  { id: '1', title: 'Flutter UI', icon: '📊', date: 'Today', tags: ['Code', 'Design'] },
  { id: '2', title: 'Memory Engine', icon: '🧠', date: 'Today', tags: ['AI', 'Memory'] },
  { id: '3', title: 'README', icon: '📄', date: 'Today', tags: ['Code'] },
  { id: '4', title: 'Voice Pipeline', icon: '🎙', date: 'Today', tags: ['AI'] },
  { id: '5', title: 'Risk Engine', icon: '🛡', date: 'Today', tags: ['AI'] },
  { id: '6', title: 'Docker Setup', icon: '🐳', date: 'Today', tags: ['Code'] },
  { id: '7', title: 'API Endpoints', icon: '🔌', date: 'Today', tags: ['Code'] },
  { id: '8', title: 'Identity Module', icon: '🔐', date: 'Today', tags: ['AI'] },
  { id: '9', title: 'Screen Capture', icon: '👁', date: 'Today', tags: ['Vision'] },
  { id: '10', title: 'Model Manager', icon: '🤖', date: 'Today', tags: ['AI'] },
  { id: '11', title: 'Neural Background', icon: '✨', date: 'Today', tags: ['Design'] },
  { id: '12', title: 'Test Suite', icon: '🧪', date: 'Today', tags: ['Code'] },
  { id: '13', title: 'WebSocket Server', icon: '🔌', date: 'Yesterday', tags: ['Code'] },
  { id: '14', title: 'Knowledge Graph', icon: '🕸', date: 'Yesterday', tags: ['AI', 'Memory'] },
  { id: '15', title: 'Tool Registry', icon: '🔧', date: 'Yesterday', tags: ['Code'] },
  { id: '16', title: 'Voice Cloner', icon: '🗣', date: 'Yesterday', tags: ['AI'] },
  { id: '17', title: 'Browser Agent', icon: '🌐', date: 'Yesterday', tags: ['AI'] },
  { id: '18', title: 'File Manager', icon: '📁', date: 'Yesterday', tags: ['Code'] },
];

export function LogPanel({ logs, searchQuery, onSearchChange, activeFilter, onFilterChange, onLogSelect }: LogPanelProps) {
  const displayLogs = logs.length > 0 ? logs : MOCK_LOGS;
  const filtered = displayLogs.filter(log => {
    const matchesSearch = !searchQuery || log.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = !activeFilter || log.tags.includes(activeFilter);
    return matchesSearch && matchesFilter;
  });

  const todayLogs = filtered.filter(l => l.date === 'Today');
  const yesterdayLogs = filtered.filter(l => l.date === 'Yesterday');

  const [expandedToday, setExpandedToday] = useState(true);
  const [expandedYesterday, setExpandedYesterday] = useState(false);

  return (
    <div className="w-[30%] min-w-[240px] border-r border-moso-border bg-moso-bg/40 backdrop-blur-sm flex flex-col">
      <div className="px-3 pt-3 pb-2">
        <h2 className="text-[11px] font-semibold text-moso-text-dim uppercase tracking-wider mb-2">📜 LOG</h2>
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-moso-text-muted" />
          <input
            type="text"
            placeholder="Search"
            value={searchQuery}
            onChange={e => onSearchChange(e.target.value)}
            className="w-full pl-7 pr-3 py-1.5 rounded-lg bg-moso-surface border border-moso-border text-xs text-moso-text placeholder:text-moso-text-muted outline-none focus:border-moso-purple/40 transition-colors"
          />
        </div>
      </div>

      <div className="px-3 pb-2 overflow-y-auto">
        <DateGroup
          label="Today"
          count={todayLogs.length}
          expanded={expandedToday}
          onToggle={() => setExpandedToday(!expandedToday)}
          logs={todayLogs}
          onLogSelect={onLogSelect}
        />
        <DateGroup
          label="Yesterday"
          count={yesterdayLogs.length}
          expanded={expandedYesterday}
          onToggle={() => setExpandedYesterday(!expandedYesterday)}
          logs={yesterdayLogs}
          onLogSelect={onLogSelect}
        />
      </div>

      <div className="mt-auto px-3 pb-3">
        <div className="text-[10px] text-moso-text-muted mb-1.5">Filters</div>
        <div className="flex flex-wrap gap-1">
          {FILTERS.map(f => (
            <button
              key={f}
              onClick={() => onFilterChange(activeFilter === f ? '' : f)}
              className={`px-2 py-0.5 rounded-md text-[10px] border transition-colors ${
                activeFilter === f
                  ? 'bg-moso-purple/15 border-moso-purple/30 text-moso-purple'
                  : 'bg-moso-surface border-moso-border text-moso-text-muted hover:text-moso-text-dim'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function DateGroup({ label, count, expanded, onToggle, logs, onLogSelect }: {
  label: string;
  count: number;
  expanded: boolean;
  onToggle: () => void;
  logs: LogEntry[];
  onLogSelect: (log: LogEntry) => void;
}) {
  return (
    <div className="mb-1">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-1.5 py-1.5 text-[11px] text-moso-text-dim hover:text-moso-text transition-colors"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span className="font-medium">{expanded ? '▼' : '▶'} {label}</span>
        <span className="text-moso-text-muted">({count})</span>
      </button>
      {expanded && (
        <div className="ml-3 flex flex-col gap-0.5">
          {logs.map(log => (
            <button
              key={log.id}
              onClick={() => onLogSelect(log)}
              className="w-full flex items-center gap-2 px-2 py-1 rounded-lg text-left hover:bg-moso-surface transition-colors group"
            >
              <span className="text-xs">{log.icon}</span>
              <span className="text-xs text-moso-text-dim group-hover:text-moso-text transition-colors truncate">{log.title}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
