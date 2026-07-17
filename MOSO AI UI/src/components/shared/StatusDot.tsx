interface StatusDotProps {
  status: 'active' | 'thinking' | 'idle' | 'error';
  size?: number;
}

const statusColors = {
  active: '#22C55E',
  thinking: '#8B5CF6',
  idle: '#6B6B80',
  error: '#EF4444',
};

export function StatusDot({ status, size = 8 }: StatusDotProps) {
  const color = statusColors[status];
  return (
    <span className="relative flex items-center justify-center" style={{ width: size + 4, height: size + 4 }}>
      {status !== 'idle' && (
        <span
          className="absolute rounded-full animate-ping"
          style={{
            width: size,
            height: size,
            backgroundColor: color,
            opacity: 0.3,
          }}
        />
      )}
      <span
        className="relative rounded-full"
        style={{
          width: size,
          height: size,
          backgroundColor: color,
          boxShadow: `0 0 8px ${color}60`,
        }}
      />
    </span>
  );
}
