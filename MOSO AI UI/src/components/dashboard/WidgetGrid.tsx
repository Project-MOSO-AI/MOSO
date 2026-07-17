import { GlassCard } from '../shared/GlassCard';
import { ProgressRing } from '../shared/ProgressRing';
import { Cpu, HardDrive, Activity, Gauge, Timer, Database, Bot, Puzzle } from 'lucide-react';

const widgets = [
  { icon: <Activity size={14} />, label: 'System Health', value: '98%', color: '#22C55E', ring: 98 },
  { icon: <Cpu size={14} />, label: 'Brain Activity', value: '73%', color: '#8B5CF6', ring: 73 },
  { icon: <Gauge size={14} />, label: 'GPU Usage', value: '45%', color: '#3B82F6', ring: 45 },
  { icon: <HardDrive size={14} />, label: 'RAM Usage', value: '62%', color: '#F59E0B', ring: 62 },
  { icon: <Timer size={14} />, label: 'Latency', value: '42ms', color: '#22C55E', ring: 15 },
  { icon: <Database size={14} />, label: 'Context Size', value: '42k', color: '#EC4899', ring: 33 },
  { icon: <Database size={14} />, label: 'Memory DB', value: '3.4 GB', color: '#8B5CF6', ring: 68 },
  { icon: <Database size={14} />, label: 'Knowledge DB', value: '12.8k', color: '#14B8A6', ring: 85 },
  { icon: <Bot size={14} />, label: 'Running Agents', value: '3', color: '#F97316', ring: 60 },
  { icon: <Puzzle size={14} />, label: 'Plugin Status', value: 'Active', color: '#22C55E', ring: 100 },
];

export function WidgetGrid() {
  return (
    <div className="grid grid-cols-5 gap-2">
      {widgets.map((w) => (
        <GlassCard key={w.label} padding="p-3" className="flex flex-col items-center gap-2 cursor-pointer">
          <ProgressRing size={44} progress={w.ring} color={w.color} strokeWidth={2.5} />
          <div className="flex flex-col items-center gap-0.5">
            <span className="text-xs font-semibold text-moso-text">{w.value}</span>
            <span className="text-[9px] text-moso-text-muted text-center leading-tight">{w.label}</span>
          </div>
        </GlassCard>
      ))}
    </div>
  );
}
