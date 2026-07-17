interface ProgressRingProps {
  size: number;
  progress: number;
  color?: string;
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
}

export function ProgressRing({ size, progress, color = '#8B5CF6', strokeWidth = 3, label, sublabel }: ProgressRingProps) {
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="rotate-[-90deg]">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#2A2A3C"
            strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
            style={{ filter: `drop-shadow(0 0 6px ${color}40)` }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-semibold" style={{ color }}>
            {Math.round(progress)}%
          </span>
        </div>
      </div>
      {label && <span className="text-[11px] text-moso-text-dim font-medium">{label}</span>}
      {sublabel && <span className="text-[10px] text-moso-text-muted">{sublabel}</span>}
    </div>
  );
}
