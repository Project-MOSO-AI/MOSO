import { Settings, Mic } from 'lucide-react';
import { StatusDot } from '../shared/StatusDot';

interface TopNavProps {
  status: 'live' | 'degraded' | 'offline';
  systemStats: { cpu: number; gpu: number; ram: string };
}

export function TopNav({ status, systemStats }: TopNavProps) {
  const now = new Date();
  const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });

  return (
    <nav className="h-10 flex items-center justify-between px-4 border-b border-moso-border bg-moso-bg/80 backdrop-blur-xl z-50 relative">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-lg bg-gradient-to-br from-moso-purple to-moso-blue flex items-center justify-center">
            <span className="text-white text-[9px] font-bold">M</span>
          </div>
          <span className="text-xs font-semibold tracking-tight text-moso-text">
            MOSO
          </span>
          <span className="text-[10px] text-moso-text-muted">●</span>
          <span className="text-[10px] text-moso-success font-medium">LIVE</span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-[11px] text-moso-text-dim">
        <span>CPU <span className="text-moso-text font-medium">{systemStats.cpu}%</span></span>
        <span className="text-moso-text-muted">│</span>
        <span>GPU <span className="text-moso-text font-medium">{systemStats.gpu}%</span></span>
        <span className="text-moso-text-muted">│</span>
        <span>RAM <span className="text-moso-text font-medium">{systemStats.ram}</span></span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <Mic size={12} className="text-moso-danger" />
          <StatusDot status={status === 'live' ? 'active' : 'idle'} size={5} />
          <span className="text-[10px] text-moso-text-dim">Listening</span>
        </div>

        <span className="text-[11px] text-moso-text-muted font-mono">{time}</span>

        <button className="p-1.5 rounded-lg hover:bg-moso-surface transition-colors">
          <Settings size={14} className="text-moso-text-dim" />
        </button>
      </div>
    </nav>
  );
}
