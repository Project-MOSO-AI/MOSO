import type { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  glow?: boolean;
  padding?: string;
}

export function GlassCard({ children, className = '', glow = false, padding = 'p-4' }: GlassCardProps) {
  return (
    <div
      className={`glass rounded-2xl ${padding} transition-all duration-300 ${glow ? 'glow-border' : ''} hover:border-moso-purple/30 hover:shadow-[0_0_20px_#8B5CF615] ${className}`}
    >
      {children}
    </div>
  );
}
