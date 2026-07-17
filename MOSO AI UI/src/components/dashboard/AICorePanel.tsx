import { Brain, Activity, Clock, Zap } from 'lucide-react';

export function AICorePanel() {
  return (
    <div className="flex flex-col gap-4">
      <div className="glass rounded-2xl p-6 glow-border relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-moso-purple/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-24 h-24 bg-moso-blue/5 rounded-full blur-3xl" />

        <div className="flex items-start justify-between relative z-10">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-moso-success animate-pulse" />
              <span className="text-[11px] text-moso-success font-medium uppercase tracking-wider">Neural Core Active</span>
            </div>
            <h2 className="text-2xl font-bold text-moso-text tracking-tight mb-1">Good morning, Harsha</h2>
            <p className="text-sm text-moso-text-dim">MOSO is ready. All systems operational.</p>
          </div>

          <div className="relative w-24 h-24 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border border-moso-purple/20 animate-rotate-slow" />
            <div className="absolute inset-2 rounded-full border border-moso-blue/15 animate-rotate-slow" style={{ animationDirection: 'reverse', animationDuration: '15s' }} />
            <div className="absolute inset-4 rounded-full border border-moso-purple/10 animate-rotate-slow" style={{ animationDuration: '25s' }} />

            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-moso-purple to-moso-blue flex items-center justify-center animate-pulse-glow">
              <Brain size={20} className="text-white" />
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
        </div>

        <div className="flex items-center gap-6 mt-5 relative z-10">
          <div className="flex items-center gap-2">
            <Activity size={13} className="text-moso-purple" />
            <span className="text-xs text-moso-text-dim">Reasoning: <span className="text-moso-text">Active</span></span>
          </div>
          <div className="flex items-center gap-2">
            <Clock size={13} className="text-moso-blue" />
            <span className="text-xs text-moso-text-dim">Uptime: <span className="text-moso-text">4h 23m</span></span>
          </div>
          <div className="flex items-center gap-2">
            <Zap size={13} className="text-moso-warning" />
            <span className="text-xs text-moso-text-dim">Tokens: <span className="text-moso-text">42.3k</span></span>
          </div>
        </div>
      </div>
    </div>
  );
}
