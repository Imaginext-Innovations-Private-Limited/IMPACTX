import { clsx } from 'clsx'

const RISK_CONFIG = {
  CRITICAL: { label: 'CRITICAL', bg: 'bg-red-900/40', border: 'border-red-500', text: 'text-red-400', dot: 'bg-red-500' },
  HIGH:     { label: 'HIGH',     bg: 'bg-orange-900/40', border: 'border-orange-500', text: 'text-orange-400', dot: 'bg-orange-500' },
  MEDIUM:   { label: 'MEDIUM',   bg: 'bg-yellow-900/40', border: 'border-yellow-500', text: 'text-yellow-400', dot: 'bg-yellow-500' },
  LOW:      { label: 'LOW',      bg: 'bg-green-900/40', border: 'border-green-500', text: 'text-green-400', dot: 'bg-green-500' },
}

export function RiskBadge({ level, className }) {
  const cfg = RISK_CONFIG[level] || RISK_CONFIG.LOW
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border',
      cfg.bg, cfg.border, cfg.text, className,
      level === 'CRITICAL' && 'pulse-critical'
    )}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', cfg.dot)} />
      {cfg.label}
    </span>
  )
}
