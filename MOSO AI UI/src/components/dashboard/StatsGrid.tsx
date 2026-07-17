import { GlassCard } from '../shared/GlassCard';
import { ProgressRing } from '../shared/ProgressRing';
import { MessageSquare, Brain, Database, Zap, Clock, BarChart3 } from 'lucide-react';

export function StatsGrid() {
  return (
    <div className="grid grid-cols-3 gap-3">
      <GlassCard padding="p-4" className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-moso-text-dim font-medium uppercase tracking-wider">Today's Activity</span>
          <MessageSquare size={13} className="text-moso-purple" />
        </div>
        <div className="flex items-end justify-between">
          <div>
            <span className="text-2xl font-bold text-moso-text">147</span>
            <span className="text-xs text-moso-text-dim ml-1">messages</span>
          </div>
          <span className="text-[11px] text-moso-success font-medium">+23%</span>
        </div>
        <div className="flex gap-0.5 items-end h-8">
          {[30, 50, 35, 65, 45, 80, 60, 90, 70, 85, 75, 95].map((h, i) => (
            <div key={i} className="flex-1 rounded-sm bg-moso-purple/30" style={{ height: `${h}%` }} />
          ))}
        </div>
      </GlassCard>

      <GlassCard padding="p-4" className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-moso-text-dim font-medium uppercase tracking-wider">Memory Stats</span>
          <Database size={13} className="text-moso-blue" />
        </div>
        <div className="flex items-center justify-center">
          <ProgressRing size={70} progress={68} color="#3B82F6" label="Used" sublabel="3.4 GB" />
        </div>
        <div className="flex justify-between text-[10px]">
          <span className="text-moso-text-muted">Short-term: 892 MB</span>
          <span className="text-moso-text-muted">Long-term: 2.5 GB</span>
        </div>
      </GlassCard>

      <GlassCard padding="p-4" className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-moso-text-dim font-medium uppercase tracking-wider">Tool Usage</span>
          <Zap size={13} className="text-moso-warning" />
        </div>
        <div className="flex flex-col gap-2">
          {[
            { name: 'Code', pct: 42, color: '#8B5CF6' },
            { name: 'Search', pct: 28, color: '#3B82F6' },
            { name: 'Files', pct: 18, color: '#22C55E' },
            { name: 'Other', pct: 12, color: '#6B6B80' },
          ].map((t) => (
            <div key={t.name} className="flex items-center gap-2">
              <span className="text-[10px] text-moso-text-muted w-10">{t.name}</span>
              <div className="flex-1 h-1.5 rounded-full bg-moso-surface-3 overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${t.pct}%`, backgroundColor: t.color }} />
              </div>
              <span className="text-[10px] text-moso-text-muted w-6 text-right">{t.pct}%</span>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard padding="p-3">
        <div className="flex items-center gap-2 mb-2">
          <Brain size={13} className="text-moso-purple" />
          <span className="text-[11px] text-moso-text-dim font-medium">Knowledge Growth</span>
        </div>
        <div className="flex items-end gap-1 h-10">
          {[20, 35, 30, 50, 40, 60, 55, 70, 65, 80, 75, 85, 80, 90, 88, 92].map((h, i) => (
            <div key={i} className="flex-1 rounded-sm bg-gradient-to-t from-moso-purple/20 to-moso-purple/50" style={{ height: `${h}%` }} />
          ))}
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className="text-[10px] text-moso-text-muted">12,847 knowledge nodes</span>
          <span className="text-[10px] text-moso-success">+156 today</span>
        </div>
      </GlassCard>

      <GlassCard padding="p-3">
        <div className="flex items-center gap-2 mb-2">
          <Clock size={13} className="text-moso-blue" />
          <span className="text-[11px] text-moso-text-dim font-medium">Recent Conversations</span>
        </div>
        <div className="flex flex-col gap-1.5">
          {[
            { title: 'Refactor API endpoints', time: '5m ago' },
            { title: 'Debug memory leak', time: '1h ago' },
            { title: 'Plan sprint tasks', time: '3h ago' },
          ].map((c) => (
            <div key={c.title} className="flex items-center justify-between px-2 py-1 rounded-lg hover:bg-moso-surface-2 transition-colors cursor-pointer">
              <span className="text-[11px] text-moso-text-dim truncate">{c.title}</span>
              <span className="text-[10px] text-moso-text-muted flex-shrink-0 ml-2">{c.time}</span>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard padding="p-3">
        <div className="flex items-center gap-2 mb-2">
          <BarChart3 size={13} className="text-moso-success" />
          <span className="text-[11px] text-moso-text-dim font-medium">Model Info</span>
        </div>
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between">
            <span className="text-[10px] text-moso-text-muted">Model</span>
            <span className="text-[10px] text-moso-text font-medium">GPT-4o</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[10px] text-moso-text-muted">Context</span>
            <span className="text-[10px] text-moso-text">128k tokens</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[10px] text-moso-text-muted">Latency</span>
            <span className="text-[10px] text-moso-success">42ms</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[10px] text-moso-text-muted">Quality</span>
            <div className="flex gap-0.5">
              {[1, 2, 3, 4, 5].map((s) => (
                <div key={s} className={`w-1.5 h-3 rounded-sm ${s <= 4 ? 'bg-moso-purple' : 'bg-moso-surface-3'}`} />
              ))}
            </div>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
