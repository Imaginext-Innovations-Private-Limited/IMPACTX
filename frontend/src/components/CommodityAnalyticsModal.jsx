import React, { useState, useEffect } from 'react'
import {
  X, TrendingUp, TrendingDown, Minus, Building2, Calendar,
  BarChart2, ArrowRight, ShieldCheck, Clock, Award, Info, Sparkles
} from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, Legend, ReferenceLine, Area, ComposedChart
} from 'recharts'
import { marketApi } from '../api/client'

const CURRENCY = '₹'

export default function CommodityAnalyticsModal({ commodityName, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [chartView, setChartView] = useState('seasonal_pattern') // 'seasonal_pattern' or 'six_year_trend'
  const [activeTab, setActiveTab] = useState('overview') // 'overview', 'mandi', 'seasonal', 'history'

  useEffect(() => {
    if (!commodityName) return
    setLoading(true)
    marketApi.getCommodityAnalytics(commodityName)
      .then(res => {
        setData(res.data)
        setLoading(false)
      })
      .catch(() => {
        setLoading(false)
      })
  }, [commodityName])

  if (!commodityName) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm p-0 sm:p-4">
      <div className="w-full sm:max-w-4xl bg-white rounded-t-3xl sm:rounded-2xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden border border-gray-100">
        {/* Header */}
        <div className="px-5 py-4 bg-gradient-to-r from-emerald-800 via-green-800 to-emerald-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
              <BarChart2 className="w-6 h-6 text-emerald-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg sm:text-xl font-bold">{data?.commodity?.name || commodityName}</h2>
                {data?.commodity?.name_kannada && (
                  <span className="text-xs bg-emerald-900/60 text-emerald-200 px-2 py-0.5 rounded-full border border-emerald-700/50">
                    {data.commodity.name_kannada}
                  </span>
                )}
              </div>
              <p className="text-xs text-emerald-200/80 mt-0.5">
                Market Analytics & 6-Year Historical Price Cycle (Agmarknet APMC)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-white/80 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Close"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Navigation tabs within modal */}
        <div className="flex items-center gap-1 px-4 py-2 bg-gray-50 border-b border-gray-200 overflow-x-auto text-xs font-medium">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors ${
              activeTab === 'overview'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-200/60'
            }`}
          >
            Overview & Advisory
          </button>
          <button
            onClick={() => setActiveTab('mandi')}
            className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors ${
              activeTab === 'mandi'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-200/60'
            }`}
          >
            Cross-Mandi Rates ({data?.cross_mandi_comparison?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('seasonal')}
            className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors ${
              activeTab === 'seasonal'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-200/60'
            }`}
          >
            6-Year Seasonal Chart
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors ${
              activeTab === 'history'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-200/60'
            }`}
          >
            14-Day History Table
          </button>
        </div>

        {/* Content body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400 gap-3">
              <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm">Fetching Agmarknet Mandi Analytics & Historical Data…</p>
            </div>
          ) : !data ? (
            <div className="text-center py-12 text-gray-400">
              No analytics data found for {commodityName}.
            </div>
          ) : (
            <>
              {/* Top Quick Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-3">
                  <p className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wide">Modal Price</p>
                  <p className="text-xl font-bold text-emerald-950 mt-1">
                    {CURRENCY}{data.commodity.current_price.toLocaleString('en-IN')}
                    <span className="text-xs font-normal text-gray-500 ml-1">/{data.commodity.unit}</span>
                  </p>
                  <p className={`text-xs mt-1 font-medium ${data.commodity.trend === 'up' ? 'text-emerald-700' : data.commodity.trend === 'down' ? 'text-red-600' : 'text-gray-500'}`}>
                    {data.commodity.trend === 'up' ? '▲ +' : data.commodity.trend === 'down' ? '▼ -' : '— '}{Math.abs(data.commodity.change_pct)}% today
                  </p>
                </div>

                <div className="bg-blue-50 border border-blue-100 rounded-xl p-3">
                  <p className="text-[11px] font-semibold text-blue-700 uppercase tracking-wide">Best Regional Mandi</p>
                  <p className="text-base font-bold text-blue-950 mt-1 truncate">{data.best_mandi || 'APMC'}</p>
                  <p className="text-xs text-blue-700 font-semibold mt-1">
                    {CURRENCY}{data.highest_modal_price?.toLocaleString('en-IN')} /{data.commodity.unit}
                  </p>
                </div>

                <div className="bg-amber-50 border border-amber-100 rounded-xl p-3">
                  <p className="text-[11px] font-semibold text-amber-800 uppercase tracking-wide">Peak Season</p>
                  <p className="text-sm font-bold text-amber-950 mt-1 truncate">
                    {data.peak_months?.join(', ') || 'May – July'}
                  </p>
                  <p className="text-[11px] text-amber-700 mt-1">Highest yearly rate window</p>
                </div>

                <div className="bg-purple-50 border border-purple-100 rounded-xl p-3">
                  <p className="text-[11px] font-semibold text-purple-700 uppercase tracking-wide">Best Selling Time</p>
                  <p className="text-sm font-bold text-purple-950 mt-1 truncate">
                    {data.selling_advisory?.best_selling_window || 'Post-Harvest'}
                  </p>
                  <p className="text-[11px] text-purple-700 mt-1">Warehouse holding advisory</p>
                </div>
              </div>

              {/* OVERVIEW TAB */}
              {(activeTab === 'overview' || activeTab === 'seasonal') && (
                <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-5 shadow-sm space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-gray-100">
                    <div>
                      <h3 className="font-bold text-gray-800 flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-emerald-600" />
                        5-to-6 Year Seasonal Price Trend (2021 – 2026)
                      </h3>
                      <p className="text-xs text-gray-500">
                        Monthly average APMC modal prices in Karnataka. Identifies cyclical price highs and lows.
                      </p>
                    </div>
                    <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl self-start sm:self-auto text-xs">
                      <button
                        onClick={() => setChartView('seasonal_pattern')}
                        className={`px-2.5 py-1 rounded-lg transition-colors ${
                          chartView === 'seasonal_pattern' ? 'bg-white shadow-sm font-bold text-emerald-800' : 'text-gray-600'
                        }`}
                      >
                        12-Month Seasonal Curve
                      </button>
                      <button
                        onClick={() => setChartView('six_year_trend')}
                        className={`px-2.5 py-1 rounded-lg transition-colors ${
                          chartView === 'six_year_trend' ? 'bg-white shadow-sm font-bold text-emerald-800' : 'text-gray-600'
                        }`}
                      >
                        6-Year Historical Line
                      </button>
                    </div>
                  </div>

                  {/* Recharts Chart Component */}
                  <div className="w-full h-64 sm:h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      {chartView === 'seasonal_pattern' ? (
                        <ComposedChart data={data.monthly_pattern} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                          <YAxis tick={{ fontSize: 11 }} domain={['dataMin - 50', 'dataMax + 50']} />
                          <Tooltip
                            formatter={(val) => [`${CURRENCY}${Number(val).toLocaleString('en-IN')}`, '6-Year Average']}
                            labelFormatter={(label) => `Month: ${label}`}
                            contentStyle={{ borderRadius: '0.75rem', borderColor: '#cbd5e1', fontSize: '12px' }}
                          />
                          <Area type="monotone" dataKey="six_year_avg" fill="#dcfce7" stroke="#16a34a" strokeWidth={2} />
                          <Line type="monotone" dataKey="six_year_avg" stroke="#15803d" strokeWidth={3} dot={{ r: 4, fill: '#15803d' }} />
                        </ComposedChart>
                      ) : (
                        <LineChart data={data.six_year_seasonal} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                          <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={5} />
                          <YAxis tick={{ fontSize: 11 }} domain={['dataMin - 100', 'dataMax + 100']} />
                          <Tooltip
                            formatter={(val, name, item) => [
                              `${CURRENCY}${Number(val).toLocaleString('en-IN')}`,
                              item.payload.is_peak ? '🌟 Seasonal Peak Month' : item.payload.is_drop ? '🔻 Price Drop Month' : 'Modal Average'
                            ]}
                            labelFormatter={(l) => `Date: ${l}`}
                            contentStyle={{ borderRadius: '0.75rem', borderColor: '#cbd5e1', fontSize: '12px' }}
                          />
                          <Line type="monotone" dataKey="avg_price" stroke="#059669" strokeWidth={2.5} dot={false} />
                        </LineChart>
                      )}
                    </ResponsiveContainer>
                  </div>

                  {/* Seasonal Insight Pill */}
                  <div className="flex flex-wrap items-center gap-2 pt-2 text-xs">
                    <span className="font-semibold text-gray-700">Seasonal Peak Months:</span>
                    {data.peak_months?.map(m => (
                      <span key={m} className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
                        ▲ {m} (Sell Window)
                      </span>
                    ))}
                    <span className="font-semibold text-gray-700 ml-2">Seasonal Drop Months:</span>
                    {data.drop_months?.map(m => (
                      <span key={m} className="bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
                        ▼ {m} (Harvest Glut)
                      </span>
                    ))}
                  </div>

                  {/* Selling Timing Advisory Banner */}
                  {data.selling_advisory && (
                    <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-4">
                      <div className="flex items-start gap-2.5">
                        <Sparkles className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-xs font-bold text-emerald-800 uppercase tracking-wide">
                            Farmer Action Advisory: {data.selling_advisory.headline}
                          </p>
                          {data.selling_advisory.headline_kannada && (
                            <p className="text-xs font-semibold text-emerald-950 mt-0.5">
                              {data.selling_advisory.headline_kannada}
                            </p>
                          )}
                          <p className="text-xs text-gray-700 mt-2 leading-relaxed">
                            {data.selling_advisory.advice}
                          </p>
                          <div className="mt-2.5 flex flex-wrap gap-3 text-xs text-emerald-900 font-medium">
                            <span>📅 Recommended Sale Window: <strong>{data.selling_advisory.best_selling_window}</strong></span>
                            <span>🏛️ Storage Viability: <strong>{data.selling_advisory.storage_feasibility}</strong></span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* CROSS-MANDI COMPARISON TAB */}
              {(activeTab === 'overview' || activeTab === 'mandi') && (
                <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-5 shadow-sm space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-gray-100">
                    <div>
                      <h3 className="font-bold text-gray-800 flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-blue-600" />
                        Cross-Mandi Selling Price Comparison (Today)
                      </h3>
                      <p className="text-xs text-gray-500">
                        Compare live modal selling prices across 5–6 Karnataka APMC markets for {data.commodity.name}
                      </p>
                    </div>
                    <span className="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-semibold border border-blue-200">
                      Live APMC Feeds
                    </span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs sm:text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-left uppercase text-[11px]">
                          <th className="py-2.5 px-3 rounded-l-lg">APMC Mandi</th>
                          <th className="py-2.5 px-3">District</th>
                          <th className="py-2.5 px-3 text-right">Min Rate</th>
                          <th className="py-2.5 px-3 text-right">Max Rate</th>
                          <th className="py-2.5 px-3 text-right font-bold">Modal Price</th>
                          <th className="py-2.5 px-3 text-right">Arrivals</th>
                          <th className="py-2.5 px-3 text-right rounded-r-lg">Diff vs Base</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {data.cross_mandi_comparison?.map((m) => (
                          <tr
                            key={m.market_name}
                            className={`transition-colors ${m.is_highest ? 'bg-emerald-50/70 font-semibold' : 'hover:bg-gray-50'}`}
                          >
                            <td className="py-3 px-3">
                              <div className="flex items-center gap-1.5">
                                <span>{m.market_name}</span>
                                {m.is_highest && (
                                  <span className="bg-emerald-600 text-white text-[10px] px-1.5 py-0.5 rounded font-bold">
                                    HIGHEST
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

                  <p className="text-[11px] text-gray-400 pt-1">
                    💡 Farmers in neighboring taluks can save logistics costs or divert trailers to <strong>{data.best_mandi}</strong> for a higher margin of {CURRENCY}{data.highest_modal_price - data.commodity.current_price} per quintal.
                  </p>
                </div>
              )}

              {/* 14-DAY HISTORY TAB */}
              {(activeTab === 'overview' || activeTab === 'history') && (
                <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-5 shadow-sm space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-gray-100">
                    <div>
                      <h3 className="font-bold text-gray-800 flex items-center gap-2">
                        <Clock className="w-4 h-4 text-purple-600" />
                        Past 2-Week Daily Price History (14 Days)
                      </h3>
                      <p className="text-xs text-gray-500">
                        Daily min, max, and modal trading range at {data.commodity.market}
                      </p>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs sm:text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-left uppercase text-[11px]">
                          <th className="py-2 px-3 rounded-l-lg">Date</th>
                          <th className="py-2 px-3 text-right">Min Rate</th>
                          <th className="py-2 px-3 text-right">Max Rate</th>
                          <th className="py-2 px-3 text-right font-bold rounded-r-lg">Modal Price</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {data.two_week_history?.map((h, i) => (
                          <tr key={h.day_offset} className="hover:bg-gray-50">
                            <td className="py-2 px-3 font-medium text-gray-700">
                              {h.date} {i === 0 ? <span className="text-emerald-600 text-xs font-bold ml-1">(Today)</span> : ''}
                            </td>
                            <td className="py-2 px-3 text-right text-gray-500">{CURRENCY}{h.min_price.toLocaleString('en-IN')}</td>
                            <td className="py-2 px-3 text-right text-gray-500">{CURRENCY}{h.max_price.toLocaleString('en-IN')}</td>
                            <td className="py-2 px-3 text-right font-semibold text-emerald-800">
                              {CURRENCY}{h.modal_price.toLocaleString('en-IN')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal footer */}
        <div className="px-5 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
          <span>Source: Agmarknet & Karnataka State Agricultural Marketing Board (KSAMB)</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-800 text-white rounded-lg hover:bg-gray-700 font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
