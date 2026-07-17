import { Wifi, WifiOff, Lock } from 'lucide-react';

interface StatusBarProps {
  memorySynced: boolean;
  localMode: boolean;
  offlineReady: boolean;
  encrypted: boolean;
}

export function StatusBar({ memorySynced, localMode, offlineReady, encrypted }: StatusBarProps) {
  return (
    <div className="h-7 flex items-center justify-between px-4 border-t border-moso-border bg-moso-bg/80 backdrop-blur-xl relative z-40">
      <div className="flex items-center gap-4 text-[10px] text-moso-text-muted">
        <StatusItem active={memorySynced} label="Memory Synced" />
        <StatusItem active={localMode} label="Local Mode" />
        <StatusItem active={offlineReady} label="Offline Ready" />
        <StatusItem active={encrypted} label="End-to-End Encrypted" icon={<Lock size={9} />} />
      </div>

      <div className="flex items-center gap-2 text-[10px] text-moso-text-muted">
        {localMode ? <WifiOff size={9} /> : <Wifi size={9} />}
        <span>{localMode ? 'Local' : 'Connected'}</span>
      </div>
    </div>
  );
}

function StatusItem({ active, label, icon }: { active: boolean; label: string; icon?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-1">
      <div className={`w-1 h-1 rounded-full ${active ? 'bg-moso-success' : 'bg-moso-text-muted'}`} />
      {icon && <span className="text-moso-text-muted">{icon}</span>}
      <span>{label}</span>
    </div>
  );
}
