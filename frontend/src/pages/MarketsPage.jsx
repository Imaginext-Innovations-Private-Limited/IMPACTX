import React, { useState, useEffect } from 'react'
import {
  BarChart2, TrendingUp, TrendingDown, Minus, Building2,
  Calendar, Clock, Sparkles, Filter, Search, ArrowRight, MapPin
} from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, Area, ComposedChart
} from 'recharts'
import { marketApi } from '../api/client'
import { useI18n } from '../context/I18nContext'
import { useLocationContext } from '../context/LocationContext'

const CURRENCY = '₹'

export default function MarketsPage({ defaultCommodity = 'Areca Nut (Chali)' }) {
  const { lang, t, getCommodityName } = useI18n()
  const { location } = useLocationContext()
  const [commodities, setCommodities] = useState([])
  const [selectedCommodity, setSelectedCommodity] = useState(defaultCommodity)
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [chartView, setChartView] = useState('seasonal_pattern') // 'seasonal_pattern' or 'six_year_trend'
  const [search, setSearch] = useState('')

  const activeState = location?.state || 'Karnataka'

  // Load commodities list when location/state changes
  useEffect(() => {
    marketApi.getList(location?.state, location?.district, location?.location_name, location?.lat, location?.lon)
      .then(res => {
        const list = res.data || []
        setCommodities(list)
        if (list.length > 0) {
          // If current selected commodity is not in this state's list, select first crop
          const exists = list.some(c => c.name.toLowerCase() === selectedCommodity.toLowerCase())
          if (!exists) {
            setSelectedCommodity(list[0].name)
          }
        }
      })
      .catch(() => {})
  }, [location?.state, location?.district, location?.location_name])

  // Load analytics for selected commodity
  useEffect(() => {
    if (!selectedCommodity) return
    setLoading(true)
    marketApi.getCommodityAnalytics(
      selectedCommodity,
      location?.state,
      location?.district,
      location?.location_name,
      location?.lat,
      location?.lon,
      lang
    )
      .then(res => {
        setAnalytics(res.data)
        setLoading(false)
      })
      .catch(() => {
        setLoading(false)
      })
  }, [selectedCommodity, location?.state, location?.district, location?.location_name, lang])

  const filteredCommodities = commodities.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    (c.name_kannada && c.name_kannada.includes(search)) ||
    (c.name_hindi && c.name_hindi.includes(search))
  )

  const regionTitle = analytics?.state || activeState
  const searchPlaceholderText = lang === 'te-IN'
    ? 'పంటను శోధించండి (వరి, మిర్చి, పత్తి)…'
    : lang === 'hi-IN'
    ? 'फसल खोजें (गेहूं, कपास, धान)…'
    : lang === 'ta-IN'
    ? 'பயிரைத் தேடுங்கள் (நெல், பருத்தி)…'
    : lang === 'mr-IN'
    ? 'पीक शोधा (कापूस, सोयाबीन, कांदा)…'
    : lang === 'kn-IN'
    ? 'ಬೆಳೆ ಹುಡುಕಿ (ಭತ್ತ, ಅಡಿಕೆ, ಮೆಕ್ಕೆಜೋಳ)…'
    : 'Search crop (Paddy, Cotton, Maize)…'

  return (
    <div className="px-4 py-4 space-y-5 max-w-4xl mx-auto">
      {/* Page Header */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700">
            <BarChart2 className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-gray-800">
              {regionTitle} APMC Market Analytics
            </h1>
            <p className="text-xs text-gray-500">
              Live Mandi Selling Rates · Cross-Market Arbitrage · 6-Year Seasonal Price Trends
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-60">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder={searchPlaceholderText}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-gray-50 border border-gray-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>
      </div>

      {/* Commodity Selector Chips */}
      <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
        {filteredCommodities.map(c => {
          const isSelected = selectedCommodity === c.name || (analytics?.commodity?.name === c.name)
          return (
            <button
              key={c.id}
              onClick={() => setSelectedCommodity(c.name)}
              className={`flex-shrink-0 flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all border ${
                isSelected
                  ? 'bg-emerald-700 text-white border-emerald-800 shadow-sm'
                  : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
              }`}
            >
              <span>{getCommodityName(c.name) || c.name.split(' (')[0]}</span>
              <span className={`text-[11px] font-bold ${
                isSelected ? 'text-emerald-200' : (c.trend === 'up' ? 'text-emerald-600' : 'text-red-500')
              }`}>
                {CURRENCY}{c.current_price.toLocaleString('en-IN')}
              </span>
            </button>
          )
        })}
      </div>

      {loading ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 flex flex-col items-center justify-center text-gray-400 gap-3">
          <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Loading market intelligence & historical analysis for {selectedCommodity}…</p>
        </div>
      ) : !analytics ? (
        <div className="text-center py-12 text-gray-400">Failed to load analytics data.</div>
      ) : (
        <>
          {/* Key Metric Highlights */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-4">
              <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wide">Modal Price</span>
              <p className="text-2xl font-black text-emerald-950 mt-1">
                {CURRENCY}{analytics.commodity.current_price.toLocaleString('en-IN')}
              </p>
              <div className="flex items-center gap-1.5 mt-1 text-xs">
                <span className={`font-semibold ${analytics.commodity.trend === 'up' ? 'text-emerald-700' : 'text-red-600'}`}>
                  {analytics.commodity.trend === 'up' ? '▲ +' : '▼ -'}{Math.abs(analytics.commodity.change_pct)}%
                </span>
                <span className="text-gray-400">/{analytics.commodity.unit}</span>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-100 rounded-2xl p-4">
              <span className="text-[11px] font-bold text-blue-800 uppercase tracking-wide">Top Regional Mandi</span>
              <p className="text-base font-bold text-blue-950 mt-1 truncate">{analytics.best_mandi}</p>
              <p className="text-xs font-bold text-blue-700 mt-1">
                {CURRENCY}{analytics.highest_modal_price?.toLocaleString('en-IN')} /{analytics.commodity.unit}
              </p>
            </div>

            <div className="bg-amber-50 border border-amber-100 rounded-2xl p-4">
              <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wide">Peak Selling Cycle</span>
              <p className="text-sm font-bold text-amber-950 mt-1">
                {analytics.peak_months?.join(', ') || 'Seasonal'}
              </p>
              <p className="text-[11px] text-amber-700 mt-1">Highest yearly margin</p>
            </div>

            <div className="bg-purple-50 border border-purple-100 rounded-2xl p-4">
              <span className="text-[11px] font-bold text-purple-800 uppercase tracking-wide">Warehouse Advisory</span>
              <p className="text-sm font-bold text-purple-950 mt-1">
                {analytics.selling_advisory?.best_selling_window}
              </p>
              <p className="text-[11px] text-purple-700 mt-1">Recommended sale period</p>
            </div>
          </div>

          {/* PANEL 1: 5-to-6 Year Seasonal Price Chart */}
          <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-gray-100">
              <div>
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-emerald-600" />
                  5-to-6 Year Seasonal Price History (2021 – 2026)
                </h3>
                <p className="text-xs text-gray-500">
                  Agmarknet monthly modal prices. Notice predictable seasonal peak and post-harvest glut drop months.
                </p>
              </div>

              {/* View Switcher */}
              <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl text-xs self-start sm:self-auto">
                <button
                  onClick={() => setChartView('seasonal_pattern')}
                  className={`px-3 py-1 rounded-lg transition-colors font-medium ${
                    chartView === 'seasonal_pattern' ? 'bg-white shadow-sm text-emerald-800 font-bold' : 'text-gray-600'
                  }`}
                >
                  12-Month Curve
                </button>
                <button
                  onClick={() => setChartView('six_year_trend')}
                  className={`px-3 py-1 rounded-lg transition-colors font-medium ${
                    chartView === 'six_year_trend' ? 'bg-white shadow-sm text-emerald-800 font-bold' : 'text-gray-600'
                  }`}
                >
                  Full 6-Year Trend
                </button>
              </div>
            </div>

            {/* Recharts Component */}
            <div className="w-full h-64 sm:h-72">
              <ResponsiveContainer width="100%" height="100%">
                {chartView === 'seasonal_pattern' ? (
                  <ComposedChart data={analytics.monthly_pattern} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} domain={['dataMin - 100', 'dataMax + 100']} />
                    <Tooltip
                      formatter={(val) => [`${CURRENCY}${Number(val).toLocaleString('en-IN')}`, '6-Year Average Modal']}
                      labelFormatter={(l) => `Month: ${l}`}
                      contentStyle={{ borderRadius: '0.75rem', borderColor: '#cbd5e1', fontSize: '12px' }}
                    />
                    <Area type="monotone" dataKey="six_year_avg" fill="#ecfdf5" stroke="#10b981" strokeWidth={2} />
                    <Line type="monotone" dataKey="six_year_avg" stroke="#047857" strokeWidth={3} dot={{ r: 4, fill: '#047857' }} />
                  </ComposedChart>
                ) : (
                  <LineChart data={analytics.six_year_seasonal} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={5} />
                    <YAxis tick={{ fontSize: 11 }} domain={['dataMin - 150', 'dataMax + 150']} />
                    <Tooltip
                      formatter={(val, name, item) => [
                        `${CURRENCY}${Number(val).toLocaleString('en-IN')}`,
                        item.payload.is_peak ? '🌟 Peak Price Month' : item.payload.is_drop ? '🔻 Harvest Drop Month' : 'Modal Price'
                      ]}
                      labelFormatter={(l) => `Date: ${l}`}
                      contentStyle={{ borderRadius: '0.75rem', borderColor: '#cbd5e1', fontSize: '12px' }}
                    />
                    <Line type="monotone" dataKey="avg_price" stroke="#059669" strokeWidth={2.5} dot={false} />
                  </LineChart>
                )}
              </ResponsiveContainer>
            </div>

            {/* Peak & Drop Season Badges */}
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
              <span className="font-semibold text-gray-700">Seasonal Peak Months:</span>
              {analytics.peak_months?.map(m => (
                <span key={m} className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
                  ▲ {m} (Sell Window)
                </span>
              ))}
              <span className="font-semibold text-gray-700 ml-2">Seasonal Drop Months:</span>
              {analytics.drop_months?.map(m => (
                <span key={m} className="bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
                  ▼ {m} (Harvest Glut)
                </span>
              ))}
            </div>

            {/* Actionable Advice Banner */}
            {analytics.selling_advisory && (
              <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-4">
                <div className="flex items-start gap-2.5">
                  <Sparkles className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-bold text-emerald-800 uppercase tracking-wide">
                      Farmer Selling Advisory: {analytics.selling_advisory.headline}
                    </p>
                    {analytics.selling_advisory.headline_kannada && (
                      <p className="text-xs font-semibold text-emerald-950 mt-0.5">
                        {analytics.selling_advisory.headline_kannada}
                      </p>
                    )}
                    <p className="text-xs text-gray-700 mt-2 leading-relaxed">
                      {analytics.selling_advisory.advice}
                    </p>
                    <div className="mt-2.5 flex flex-wrap gap-4 text-xs text-emerald-900 font-medium">
                      <span>📅 Best Window: <strong>{analytics.selling_advisory.best_selling_window}</strong></span>
                      <span>🏛️ Storage Viability: <strong>{analytics.selling_advisory.storage_feasibility}</strong></span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* PANEL 2: Cross-Mandi Selling Price Comparison */}
          <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-gray-100">
              <div>
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-blue-600" />
                  Cross-Mandi Selling Price Comparison (Today)
                </h3>
                <p className="text-xs text-gray-500">
                  Side-by-side selling prices across 5–6 Karnataka APMC markets for {analytics.commodity.name}
                </p>
              </div>
              <span className="text-xs bg-blue-100 text-blue-800 px-2.5 py-0.5 rounded-full font-semibold">
                Agmarknet
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs sm:text-sm">
                <thead>
                  <tr className="bg-gray-50 text-gray-500 text-left uppercase text-[11px]">
                    <th className="py-2.5 px-3 rounded-l-lg">APMC Market</th>
                    <th className="py-2.5 px-3">District</th>
                    <th className="py-2.5 px-3 text-right">Min Rate</th>
                    <th className="py-2.5 px-3 text-right">Max Rate</th>
                    <th className="py-2.5 px-3 text-right font-bold">Modal Price</th>
                    <th className="py-2.5 px-3 text-right">Daily Arrivals</th>
                    <th className="py-2.5 px-3 text-right rounded-r-lg">Diff vs Base</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {analytics.cross_mandi_comparison?.map((m) => (
                    <tr
                      key={m.market_name}
                      className={`transition-colors ${m.is_highest ? 'bg-emerald-50/70 font-semibold' : 'hover:bg-gray-50'}`}
                    >
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-1.5">
                          <span>{m.market_name}</span>
                          {m.is_highest && (
                            <span className="bg-emerald-600 text-white text-[10px] px-1.5 py-0.5 rounded font-bold">
                              TOP RATE
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-gray-500 text-xs">{m.district}</td>
                      <td className="py-3 px-3 text-right text-gray-600">{CURRENCY}{m.min_price.toLocaleString('en-IN')}</td>
                      <td className="py-3 px-3 text-right text-gray-600">{CURRENCY}{m.max_price.toLocaleString('en-IN')}</td>
                      <td className={`py-3 px-3 text-right text-base font-bold ${m.is_highest ? 'text-emerald-700' : 'text-gray-900'}`}>
                        {CURRENCY}{m.modal_price.toLocaleString('en-IN')}
                      </td>
                      <td className="py-3 px-3 text-right text-gray-500 text-xs">{m.arrivals_tonnes} t</td>
                      <td className={`py-3 px-3 text-right text-xs font-semibold ${m.diff_from_base > 0 ? 'text-emerald-600' : m.diff_from_base < 0 ? 'text-red-500' : 'text-gray-400'}`}>
                        {m.diff_from_base > 0 ? `+${CURRENCY}${m.diff_from_base}` : m.diff_from_base < 0 ? `-${CURRENCY}${Math.abs(m.diff_from_base)}` : 'Base'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* PANEL 3: Past 2-Week Daily Price History */}
          <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-gray-100">
              <div>
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-purple-600" />
                  Past 2-Week Daily Price History (14 Days)
                </h3>
                <p className="text-xs text-gray-500">
                  Daily price movement at {analytics.commodity.market}
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs sm:text-sm">
                <thead>
                  <tr className="bg-gray-50 text-gray-500 text-left uppercase text-[11px]">
                    <th className="py-2.5 px-3 rounded-l-lg">Date</th>
                    <th className="py-2.5 px-3 text-right">Min Rate</th>
                    <th className="py-2.5 px-3 text-right">Max Rate</th>
                    <th className="py-2.5 px-3 text-right font-bold rounded-r-lg">Modal Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {analytics.two_week_history?.map((h, i) => (
                    <tr key={h.day_offset} className="hover:bg-gray-50">
                      <td className="py-2.5 px-3 font-medium text-gray-700">
                        {h.date} {i === 0 ? <span className="text-emerald-600 text-xs font-bold ml-1">(Today)</span> : ''}
                      </td>
                      <td className="py-2.5 px-3 text-right text-gray-500">{CURRENCY}{h.min_price.toLocaleString('en-IN')}</td>
                      <td className="py-2.5 px-3 text-right text-gray-500">{CURRENCY}{h.max_price.toLocaleString('en-IN')}</td>
                      <td className="py-2.5 px-3 text-right font-bold text-emerald-800">
                        {CURRENCY}{h.modal_price.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
