import { clsx } from 'clsx'

export function StatCard({ title, value, subtitle, icon: Icon, color = 'blue', trend }) {
  const colors = {
    blue:   'bg-blue-900/30 border-blue-800 text-blue-400',
    red:    'bg-red-900/30 border-red-800 text-red-400',
    orange: 'bg-orange-900/30 border-orange-800 text-orange-400',
    green:  'bg-green-900/30 border-green-800 text-green-400',
  }
  return (
    <div className={clsx('rounded-xl border p-5', colors[color])}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium opacity-70 uppercase tracking-wider">{title}</p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
          {subtitle && <p className="text-xs opacity-60 mt-1">{subtitle}</p>}
        </div>
        {Icon && <div className="p-2 rounded-lg bg-white/10"><Icon size={20} /></div>}
      </div>
      {trend && (
        <p className={clsx('text-xs mt-3 font-medium', trend > 0 ? 'text-red-400' : 'text-green-400')}>
          {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% from last hour
        </p>
      )}
    </div>
  )
}
