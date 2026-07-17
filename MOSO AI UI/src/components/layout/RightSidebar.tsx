import { GlassCard } from '../shared/GlassCard';
import { StatusDot } from '../shared/StatusDot';
import { Clock, GitBranch, StickyNote, FileText, Terminal } from 'lucide-react';

const runningTasks = [
  { name: 'Code Review', agent: 'Agent Alpha', progress: 78 },
  { name: 'Data Analysis', agent: 'Agent Beta', progress: 45 },
  { name: 'Web Scrape', agent: 'Agent Gamma', progress: 92 },
];

const memoryTimeline = [
  { time: '2 min ago', event: 'Memory consolidated', type: 'memory' },
  { time: '5 min ago', event: 'Knowledge graph updated', type: 'knowledge' },
  { time: '12 min ago', event: 'New pattern learned', type: 'learning' },
  { time: '1 hr ago', event: 'Session context saved', type: 'session' },
];

const knowledgeNodes = [
  { name: 'Python', connections: 12 },
  { name: 'React', connections: 8 },
  { name: 'ML Ops', connections: 6 },
  { name: 'API Design', connections: 9 },
  { name: 'Databases', connections: 7 },
];

const recentNotes = [
  { title: 'API Architecture Notes', time: '10m' },
  { title: 'Project Milestone v2', time: '1h' },
  { title: 'Research Summary', time: '3h' },
];

const pinnedFiles = [
  { name: 'config.yaml', icon: <FileText size={12} /> },
  { name: 'main.py', icon: <Terminal size={12} /> },
  { name: 'README.md', icon: <StickyNote size={12} /> },
];

export function RightSidebar() {
  return (
    <aside className="w-[260px] border-l border-moso-border bg-moso-bg/60 backdrop-blur-xl overflow-y-auto flex flex-col gap-3 p-3">
      <GlassCard padding="p-3">
        <h3 className="text-[11px] font-semibold text-moso-text-dim uppercase tracking-wider mb-3">Running Tasks</h3>
        <div className="flex flex-col gap-2.5">
          {runningTasks.map((task) => (
            <div key={task.name} className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-moso-text font-medium">{task.name}</span>
                <StatusDot status={task.progress > 80 ? 'active' : 'thinking'} size={5} />
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1 rounded-full bg-moso-surface-3 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-moso-purple to-moso-blue transition-all duration-700"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
                <span className="text-[10px] text-moso-text-muted">{task.progress}%</span>
              </div>
              <span className="text-[10px] text-moso-text-muted">{task.agent}</span>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard padding="p-3">
        <h3 className="text-[11px] font-semibold text-moso-text-dim uppercase tracking-wider mb-3">Memory Timeline</h3>
        <div className="flex flex-col gap-2">
          {memoryTimeline.map((item, i) => (
            <div key={i} className="flex items-start gap-2.5 relative">
              <div className="flex flex-col items-center mt-1">
                <div className="w-1.5 h-1.5 rounded-full bg-moso-purple" />
                {i < memoryTimeline.length - 1 && <div className="w-px h-4 bg-moso-border mt-1" />}
              </div>
              <div className="flex flex-col -mt-0.5">
                <span className="text-[11px] text-moso-text">{item.event}</span>
                <span className="text-[10px] text-moso-text-muted flex items-center gap-1">
                  <Clock size={9} /> {item.time}
                </span>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard padding="p-3">
        <h3 className="text-[11px] font-semibold text-moso-text-dim uppercase tracking-wider mb-3">Knowledge Graph</h3>
        <div className="flex flex-col gap-2">
          {knowledgeNodes.map((node) => (
            <div key={node.name} className="flex items-center justify-between group cursor-pointer">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-moso-purple/50 group-hover:bg-moso-purple transition-colors" />
                <span className="text-xs text-moso-text-dim group-hover:text-moso-text transition-colors">{node.name}</span>
              </div>
              <div className="flex items-center gap-1">
                <GitBranch size={10} className="text-moso-text-muted" />
                <span className="text-[10px] text-moso-text-muted">{node.connections}</span>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard padding="p-3">
        <h3 className="text-[11px] font-semibold text-moso-text-dim uppercase tracking-wider mb-3">Recent Notes</h3>
        <div className="flex flex-col gap-2">
          {recentNotes.map((note) => (
            <div key={note.title} className="flex items-center justify-between group cursor-pointer hover:bg-moso-surface-2 rounded-lg px-2 py-1.5 -mx-2 transition-colors">
              <div className="flex items-center gap-2">
                <StickyNote size={12} className="text-moso-text-muted" />
                <span className="text-xs text-moso-text-dim group-hover:text-moso-text transition-colors">{note.title}</span>
              </div>
              <span className="text-[10px] text-moso-text-muted">{note.time}</span>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard padding="p-3">
        <h3 className="text-[11px] font-semibold text-moso-text-dim uppercase tracking-wider mb-3">Pinned Files</h3>
        <div className="flex flex-col gap-1.5">
          {pinnedFiles.map((file) => (
            <div key={file.name} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-moso-surface-2 transition-colors cursor-pointer -mx-2 group">
              <span className="text-moso-text-muted group-hover:text-moso-purple transition-colors">{file.icon}</span>
              <span className="text-xs text-moso-text-dim group-hover:text-moso-text transition-colors">{file.name}</span>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard padding="p-3">
        <h3 className="text-[11px] font-semibold text-moso-text-dim uppercase tracking-wider mb-3">Live Logs</h3>
        <div className="bg-moso-bg rounded-lg p-2 font-mono text-[10px] text-moso-text-muted leading-relaxed max-h-[120px] overflow-y-auto">
          <div><span className="text-moso-purple">[11:42]</span> Memory sync complete</div>
          <div><span className="text-moso-blue">[11:41]</span> Agent Alpha: task assigned</div>
          <div><span className="text-moso-success">[11:40]</span> Knowledge graph: 3 nodes added</div>
          <div><span className="text-moso-purple">[11:38]</span> Context window: 42k tokens</div>
          <div><span className="text-moso-blue">[11:35]</span> Plugin loaded: code-review</div>
        </div>
      </GlassCard>
    </aside>
  );
}
