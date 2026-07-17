import { Mic, Camera, Monitor, ScanText, Globe, Terminal, Workflow, Puzzle, Code2 } from 'lucide-react';

const dockItems = [
  { icon: <Mic size={18} />, label: 'Microphone', color: '#EF4444' },
  { icon: <Camera size={18} />, label: 'Camera', color: '#3B82F6' },
  { icon: <Monitor size={18} />, label: 'Screen', color: '#8B5CF6' },
  { icon: <ScanText size={18} />, label: 'OCR', color: '#22C55E' },
  { icon: <Globe size={18} />, label: 'Browser', color: '#F59E0B' },
  { icon: <Terminal size={18} />, label: 'Terminal', color: '#6B6B80' },
  { icon: <Workflow size={18} />, label: 'Auto', color: '#EC4899' },
  { icon: <Puzzle size={18} />, label: 'Plugins', color: '#14B8A6' },
  { icon: <Code2 size={18} />, label: 'Dev Mode', color: '#F97316' },
];

export function BottomDock() {
  return (
    <div className="h-14 flex items-center justify-center border-t border-moso-border bg-moso-bg/80 backdrop-blur-xl relative z-40">
      <div className="flex items-center gap-1 px-3 py-1.5 rounded-2xl bg-moso-surface/50 border border-moso-border">
        {dockItems.map((item) => (
          <button
            key={item.label}
            className="group relative flex flex-col items-center justify-center w-10 h-10 rounded-xl hover:bg-moso-surface-2 transition-all duration-200"
            title={item.label}
          >
            <span className="transition-colors duration-200" style={{ color: '#6B6B80' }}>
              {item.icon}
            </span>
            <span
              className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 w-0 h-0.5 rounded-full group-hover:w-4 transition-all duration-300"
              style={{ backgroundColor: item.color }}
            />
            <span className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-md bg-moso-surface-2 border border-moso-border text-[10px] text-moso-text opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
              {item.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
