import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Legend, CartesianGrid } from 'recharts'

const HOURLY_DATA = Array.from({ length: 24 }, (_, i) => ({
  hour: `${i.toString().padStart(2,'0')}:00`,
  rainfall_mm: Math.max(0, Math.sin(i * 0.4) * 30 + Math.random() * 15),
  flood_risk: Math.min(1, Math.max(0, Math.sin(i * 0.3 + 1) * 0.4 + 0.3)),
  temperature: 28 + Math.sin(i * 0.26 - 1) * 8 + Math.random() * 2,
}))

const ZONE_DATA = [
  { zone: 'Dharavi', flood_risk: 82, heat_index: 46 },
  { zone: 'Andheri', flood_risk: 72, heat_index: 43 },
  { zone: 'Kurla',   flood_risk: 65, heat_index: 44 },
  { zone: 'Worli',   flood_risk: 38, heat_index: 42 },
  { zone: 'Bandra',  flood_risk: 15, heat_index: 40 },
]

const CUSTOM_TOOLTIP_STYLE = {
  contentStyle: { background: '#1f2937', border: '1px solid #374151', borderRadius: 8, fontSize: 12 },
  labelStyle: { color: '#9ca3af' },
}

export default function AnalyticsPage() {
  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold text-white">Analytics & Trends</h1>

      {/* 24h rainfall + flood risk trend */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h2 className="font-semibold text-white mb-4">24-Hour Rainfall & Flood Risk Trend</h2>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={HOURLY_DATA}>
            <defs>
              <linearGradient id="rainGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="hour" tick={{ fontSize: 11, fill: '#6b7280' }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#6b7280' }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip {...CUSTOM_TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
            <Area yAxisId="left" type="monotone" dataKey="rainfall_mm" name="Rainfall (mm)" stroke="#3b82f6" fill="url(#rainGrad)" strokeWidth={2} />
            <Area yAxisId="right" type="monotone" dataKey="flood_risk" name="Flood Risk (0-1)" stroke="#ef4444" fill="url(#riskGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Temperature trend */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h2 className="font-semibold text-white mb-4">24-Hour Temperature Trend (°C)</h2>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={HOURLY_DATA}>
            <defs>
              <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.4}/>
                <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="hour" tick={{ fontSize: 11, fill: '#6b7280' }} />
            <YAxis domain={[20, 50]} tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip {...CUSTOM_TOOLTIP_STYLE} />
            <Area type="monotone" dataKey="temperature" name="Temp (°C)" stroke="#f97316" fill="url(#tempGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Zone comparison */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h2 className="font-semibold text-white mb-4">Zone Risk Comparison</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={ZONE_DATA} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis type="number" tick={{ fontSize: 11, fill: '#6b7280' }} />
            <YAxis dataKey="zone" type="category" tick={{ fontSize: 12, fill: '#d1d5db' }} width={70} />
            <Tooltip {...CUSTOM_TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
            <Bar dataKey="flood_risk" name="Flood Risk %" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            <Bar dataKey="heat_index" name="Heat Index °C" fill="#f97316" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
