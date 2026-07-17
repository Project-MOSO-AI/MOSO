import { useState } from 'react';
import { GitBranch, Table, BarChart3, Code2 } from 'lucide-react';
import type { LogEntry } from './LogPanel';

interface ExplainerPanelProps {
  explanation: string;
  selectedLog: LogEntry | null;
}

const TABS = [
  { id: 'flowchart', label: 'Flowchart', icon: <GitBranch size={11} /> },
  { id: 'table', label: 'Table', icon: <Table size={11} /> },
  { id: 'graph', label: 'Graph', icon: <BarChart3 size={11} /> },
  { id: 'code', label: 'Code', icon: <Code2 size={11} /> },
] as const;

export function ExplainerPanel({ explanation, selectedLog }: ExplainerPanelProps) {
  const [activeTab, setActiveTab] = useState<string>('flowchart');

  const hasContent = explanation || selectedLog;

  return (
    <div className="w-[28%] min-w-[220px] border-l border-moso-border bg-moso-bg/40 backdrop-blur-sm flex flex-col">
      <div className="px-3 pt-3 pb-2">
        <h2 className="text-[11px] font-semibold text-moso-text-dim uppercase tracking-wider">📊 EXPLAINER</h2>
      </div>

      {!hasContent ? (
        <div className="flex-1 flex items-center justify-center px-4">
          <div className="text-center">
            <p className="text-xs text-moso-text-dim mb-1">Nothing to explain yet</p>
            <p className="text-[10px] text-moso-text-muted leading-relaxed">
              Ask a question, upload a file, or select a previous log entry.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col min-h-0">
          {/* Tabs */}
          <div className="flex gap-0 px-3 border-b border-moso-border">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1 px-2.5 py-2 text-[10px] border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-moso-purple text-moso-purple'
                    : 'border-transparent text-moso-text-muted hover:text-moso-text-dim'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto px-3 py-3">
            <div className="glass rounded-xl border border-moso-border p-3 min-h-[120px]">
              <div className="text-[11px] text-moso-text-dim">
                {selectedLog && (
                  <div className="mb-2 pb-2 border-b border-moso-border">
                    <span className="text-xs">{selectedLog.icon}</span>
                    <span className="ml-1.5 font-medium text-moso-text">{selectedLog.title}</span>
                  </div>
                )}

                {explanation ? (
                  <p className="leading-relaxed whitespace-pre-wrap">{explanation}</p>
                ) : (
                  <GeneratedPlaceholder tab={activeTab} log={selectedLog} />
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function GeneratedPlaceholder({ tab, log }: { tab: string; log: LogEntry | null }) {
  if (tab === 'flowchart') {
    return (
      <div className="flex flex-col items-center gap-2 py-4">
        <div className="w-full h-32 rounded-lg bg-moso-surface border border-moso-border flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <GitBranch size={20} className="text-moso-purple/40" />
            <span className="text-[10px] text-moso-text-muted">Flowchart will appear here</span>
          </div>
        </div>
      </div>
    );
  }

  if (tab === 'table') {
    return (
      <div className="w-full">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b border-moso-border">
              <th className="text-left py-1 text-moso-text-muted">Component</th>
              <th className="text-left py-1 text-moso-text-muted">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-moso-border/50">
              <td className="py-1 text-moso-text-dim">{log?.title || '—'}</td>
              <td className="py-1 text-moso-success">Active</td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }

  if (tab === 'graph') {
    return (
      <div className="w-full h-32 rounded-lg bg-moso-surface border border-moso-border flex items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <BarChart3 size={20} className="text-moso-blue/40" />
          <span className="text-[10px] text-moso-text-muted">Graph visualization</span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full rounded-lg bg-moso-bg p-2 font-mono text-[10px] text-moso-text-muted">
      <div className="text-moso-purple"># {log?.title || 'code'}</div>
      <div className="text-moso-text-dim mt-1">Select a log entry to view code</div>
    </div>
  );
}
