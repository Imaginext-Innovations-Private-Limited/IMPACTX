import React, { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Minus, ExternalLink, X, BarChart2 } from 'lucide-react'
import { commodityApi } from '../api/client'
import { useI18n } from '../context/I18nContext'

const CURRENCY = '₹'

function PriceTag({ item, onClick }) {
  const { getCommodityName } = useI18n()
  const color = item.trend === 'up' ? 'text-emerald-400' : item.trend === 'down' ? 'text-red-400' : 'text-gray-300'
  const arrow = item.trend === 'up' ? '▲' : item.trend === 'down' ? '▼' : '—'
  const pct = Math.abs(item.change_pct)
  const displayName = getCommodityName(item.name) || item.name.split(' (')[0]

  return (
    <button
      onClick={() => onClick && onClick(item.name)}
      className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1 whitespace-nowrap select-none hover:bg-gray-800 rounded transition-all cursor-pointer group shrink-0 min-w-0"
      title={`Click to view 6-year analytics for ${item.name}`}
    >
      <span className="text-gray-100 font-medium text-xs sm:text-sm group-hover:text-emerald-300 underline-offset-2 group-hover:underline truncate">
        {displayName}
      </span>
      <span className={`font-bold text-xs sm:text-sm ${color} shrink-0`}>
        {arrow} {CURRENCY}{item.current_price.toLocaleString('en-IN')}
        <span className="text-[10px] sm:text-xs font-normal ml-0.5 opacity-80">/{item.unit}</span>
      </span>
      {pct > 0 && (
        <span className={`text-[10px] rounded px-1 py-0.5 font-semibold shrink-0 ${item.trend === 'up' ? 'bg-emerald-900/60 text-emerald-300' : 'bg-red-900/60 text-red-300'}`}>
          {item.trend === 'up' ? '+' : '-'}{pct}%
        </span>
      )}
      <span className="text-gray-600 mx-1 shrink-0">|</span>
    </button>
  )
}

// Full commodity rates modal
function AllRatesModal({ onClose, onSelectCommodity }) {
  const { getCommodityName } = useI18n()
  const [commodities, setCommodities] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterCat, setFilterCat] = useState('all')

  useEffect(() => {
    commodityApi.getAll().then(r => {
      setCommodities(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const categories = ['all', ...new Set(commodities.map(c => c.category))]
  const filtered = filterCat === 'all' ? commodities : commodities.filter(c => c.category === filterCat)

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full sm:max-w-2xl bg-white rounded-t-2xl sm:rounded-2xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-emerald-800 text-white rounded-t-2xl sm:rounded-t-2xl">
          <div>
            <h2 className="text-white font-bold text-lg flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-emerald-300" />
              Karnataka APMC Market Rates
            </h2>
            <p className="text-emerald-200 text-xs">Click any row to open 6-Year Historical Analytics & Cross-Mandi Comparison</p>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white p-1 rounded-full hover:bg-white/10">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Category filter */}
        <div className="px-4 py-2 flex gap-2 overflow-x-auto border-b bg-gray-50">
          {categories.map(cat => (
            <button key={cat}
              onClick={() => setFilterCat(cat)}
              className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors
                ${filterCat === cat ? 'bg-emerald-600 text-white' : 'bg-white text-gray-600 border hover:bg-emerald-50'}`}>
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-gray-400">Loading rates…</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-100 z-10">
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-2">Commodity (Click for Analytics)</th>
                  <th className="px-4 py-2">Market</th>
                  <th className="px-4 py-2 text-right">Price</th>
                  <th className="px-4 py-2 text-right">Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map(c => {
                  const color = c.trend === 'up' ? 'text-emerald-600' : c.trend === 'down' ? 'text-red-500' : 'text-gray-500'
                  const arrow = c.trend === 'up' ? '▲' : c.trend === 'down' ? '▼' : '—'
                  return (
                    <tr
                      key={c.id}
                      onClick={() => {
                        onClose()
                        onSelectCommodity && onSelectCommodity(c.name)
                      }}
                      className="hover:bg-emerald-50 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-800 flex items-center gap-1.5 hover:text-emerald-700">
                          <span>{getCommodityName(c.name) || c.name}</span>
                          <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.2 rounded font-medium">Analytics →</span>
                        </div>
                        {c.name_kannada && <div className="text-xs text-gray-400">{c.name_kannada}</div>}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{c.market}</td>
                      <td className={`px-4 py-3 text-right font-bold ${color}`}>
                        {CURRENCY}{c.current_price.toLocaleString('en-IN')}
                        <div className="text-[10px] font-normal text-gray-400">/{c.unit}</div>
                      </td>
                      <td className={`px-4 py-3 text-right text-xs font-semibold ${color}`}>
                        {arrow} {Math.abs(c.change_pct)}%
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className="px-4 py-2 text-xs text-gray-400 border-t text-center bg-gray-50">
          Source: APMC Karnataka (e-NAM / Agmarknet) • Click any commodity for 6-year seasonal charts
        </div>
      </div>
    </div>
  )
}

export default function CommodityTicker({ onSelectCommodity }) {
  const [items, setItems] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchTicker = () => {
    commodityApi.getTicker()
      .then(r => { setItems(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchTicker()
    const interval = setInterval(fetchTicker, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="sticky top-0 z-40 h-9 bg-gray-900 flex items-center px-4 text-gray-400 text-xs animate-pulse">
        Loading Karnataka APMC market rates…
      </div>
    )
  }

  const doubled = [...items, ...items]

  return (
    <>
      <div className="sticky top-0 z-40 bg-gray-900 border-b border-gray-700 overflow-hidden h-9 flex items-center min-w-0">
        {/* Scrolling ticker */}
        <div className="flex-1 overflow-hidden min-w-0">
          <div className="ticker-scroll flex items-center h-9">
            {doubled.map((item, idx) => (
              <PriceTag
                key={`${item.id}-${idx}`}
                item={item}
                onClick={onSelectCommodity}
              />
            ))}
          </div>
        </div>

        {/* View All button */}
        <button
          onClick={() => setShowModal(true)}
          className="shrink-0 flex items-center gap-1 px-2.5 sm:px-3 h-9 bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold transition-colors whitespace-nowrap border-l border-gray-700 shadow-sm"
        >
          View All <ExternalLink className="w-3 h-3 shrink-0" />
        </button>
      </div>

      {showModal && (
        <AllRatesModal
          onClose={() => setShowModal(false)}
          onSelectCommodity={onSelectCommodity}
        />
      )}
    </>
  )
}
