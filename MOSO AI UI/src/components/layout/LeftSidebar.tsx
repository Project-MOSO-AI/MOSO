import {
  LayoutDashboard, MessageSquare, Mic, Brain, Eye, Workflow,
  AppWindow, Globe, Bot, BookOpen, Search, Files, Settings, ChevronLeft, ChevronRight
} from 'lucide-react';
import { useState } from 'react';

interface NavItem {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
}

const topItems: NavItem[] = [
  { icon: <LayoutDashboard size={18} />, label: 'Dashboard', active: true },
  { icon: <MessageSquare size={18} />, label: 'Chat' },
  { icon: <Mic size={18} />, label: 'Voice' },
  { icon: <Brain size={18} />, label: 'Memory' },
  { icon: <Eye size={18} />, label: 'Vision' },
  { icon: <Workflow size={18} />, label: 'Automation' },
];

const midItems: NavItem[] = [
  { icon: <AppWindow size={18} />, label: 'Applications' },
  { icon: <Globe size={18} />, label: 'Browser' },
  { icon: <Bot size={18} />, label: 'Agents' },
  { icon: <BookOpen size={18} />, label: 'Knowledge' },
  { icon: <Search size={18} />, label: 'Research' },
  { icon: <Files size={18} />, label: 'Files' },
];

const bottomItems: NavItem[] = [
  { icon: <Settings size={18} />, label: 'Settings' },
];

export function LeftSidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`flex flex-col border-r border-moso-border bg-moso-bg/60 backdrop-blur-xl transition-all duration-300 relative z-40 ${
        collapsed ? 'w-[60px]' : 'w-[200px]'
      }`}
    >
      <div className="flex-1 py-3 flex flex-col">
        <div className="flex flex-col gap-0.5 px-2">
          {topItems.map((item) => (
            <SidebarItem key={item.label} item={item} collapsed={collapsed} />
          ))}
        </div>

        <div className="mx-3 my-3 h-px bg-moso-border" />

        <div className="flex flex-col gap-0.5 px-2">
          {midItems.map((item) => (
            <SidebarItem key={item.label} item={item} collapsed={collapsed} />
          ))}
        </div>

        <div className="mt-auto" />

        <div className="flex flex-col gap-0.5 px-2">
          {bottomItems.map((item) => (
            <SidebarItem key={item.label} item={item} collapsed={collapsed} />
          ))}
        </div>
      </div>

      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-moso-surface-2 border border-moso-border flex items-center justify-center hover:bg-moso-surface-3 transition-colors z-50"
      >
        {collapsed ? <ChevronRight size={12} className="text-moso-text-dim" /> : <ChevronLeft size={12} className="text-moso-text-dim" />}
      </button>
    </aside>
  );
}

function SidebarItem({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  return (
    <button
      className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl transition-all duration-200 group
        ${item.active
          ? 'bg-moso-purple/10 text-moso-purple border border-moso-purple/20'
          : 'text-moso-text-dim hover:bg-moso-surface hover:text-moso-text border border-transparent'
        }
        ${collapsed ? 'justify-center' : ''}
      `}
      title={collapsed ? item.label : undefined}
    >
      <span className={`flex-shrink-0 ${item.active ? 'text-moso-purple' : 'text-moso-text-muted group-hover:text-moso-text-dim'}`}>
        {item.icon}
      </span>
      {!collapsed && (
        <span className="text-xs font-medium truncate">{item.label}</span>
      )}
    </button>
  );
}
