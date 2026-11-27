import React, { useState, useEffect } from 'react'
import {
  Wallet, DollarSign, TrendingUp, TrendingDown, Plus, Trash2,
  Calendar, Layers, CheckCircle2, AlertTriangle, ArrowRight,
  ShieldCheck, Droplets, SunMedium, Landmark, Award, BookOpen,
  PieChart as PieIcon, BarChart3, HelpCircle, FileText, ChevronRight,
  PiggyBank
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, Cell
} from 'recharts'
import { financeApi } from '../api/client'
import { useI18n } from '../context/I18nContext'
import MoneyManagementTab from '../components/MoneyManagementTab'

export default function FinancePage({ onAskVoice }) {
  const { t } = useI18n()
  const [activeSubTab, setActiveSubTab] = useState('balancesheet') // 'balancesheet', 'comparator', 'advisory', 'wealth'
  
  // Ledger / Balance Sheet State
  const [balanceSheetData, setBalanceSheetData] = useState(null)
  const [ledgerEntries, setLedgerEntries] = useState([])
  const [monthlyChart, setMonthlyChart] = useState([])
  const [loadingLedger, setLoadingLedger] = useState(true)
  const [filterCrop, setFilterCrop] = useState('All')
  const [filterType, setFilterType] = useState('All')

  // New Transaction Modal State
  const [showAddModal, setShowAddModal] = useState(false)
  const [newEntry, setNewEntry] = useState({
    entry_date: new Date().toISOString().slice(0, 10),
    crop_tag: 'Paddy',
    entry_type: 'expense',
    category: 'cultivation',
    sub_category: 'Seeds & Nursery',
    description: '',
    amount: '',
    notes: ''
  })
  const [addingEntry, setAddingEntry] = useState(false)

  // Crop Comparator State
  const [selectedSoil, setSelectedSoil] = useState('Red Sandy Loam')
  const [comparatorTemp, setComparatorTemp] = useState(27.0)
  const [farmerCrops, setFarmerCrops] = useState([])
  const [recommendedAlternatives, setRecommendedAlternatives] = useState([])
  const [availableSoils, setAvailableSoils] = useState([])
  const [comparatorLoading, setComparatorLoading] = useState(false)

  // Credit Advisory State
  const [advisoryData, setAdvisoryData] = useState(null)
  const [advisoryLoading, setAdvisoryLoading] = useState(false)
  const [activeCreditPillar, setActiveCreditPillar] = useState('kcc')

  // Interactive Loan Calculator inside advisory
  const [calcAcreage, setCalcAcreage] = useState(2.0)
  const [calcCropType, setCalcCropType] = useState('Paddy')
  const [calcPromptPay, setCalcPromptPay] = useState(true)

  // Fetch ledger data
  useEffect(() => {
    fetchLedger()
  }, [filterCrop, filterType])

  const fetchLedger = () => {
    setLoadingLedger(true)
    financeApi.getLedger(filterCrop, filterType)
      .then(res => {
        setBalanceSheetData(res.data.balance_sheet)
        setLedgerEntries(res.data.entries || [])
        setMonthlyChart(res.data.monthly_chart || [])
        setLoadingLedger(false)
      })
      .catch(() => setLoadingLedger(false))
  }

  // Fetch profit comparator
  useEffect(() => {
    if (activeSubTab === 'comparator') {
      setComparatorLoading(true)
      financeApi.getProfitComparison(selectedSoil, comparatorTemp)
        .then(res => {
          setFarmerCrops(res.data.farmer_crops || [])
          setRecommendedAlternatives(res.data.recommended_alternatives || [])
          setAvailableSoils(res.data.available_soils || [])
          setComparatorLoading(false)
        })
        .catch(() => setComparatorLoading(false))
    }
  }, [activeSubTab, selectedSoil, comparatorTemp])

  // Fetch advisory data
  useEffect(() => {
    if (activeSubTab === 'advisory' && !advisoryData) {
      setAdvisoryLoading(true)
      financeApi.getAdvisory()
        .then(res => {
          setAdvisoryData(res.data)
          setAdvisoryLoading(false)
        })
        .catch(() => setAdvisoryLoading(false))
    }
  }, [activeSubTab])

  const handleAddEntry = (e) => {
    e.preventDefault()
    if (!newEntry.amount || isNaN(parseFloat(newEntry.amount))) return
    setAddingEntry(true)
    financeApi.addLedgerEntry({
      ...newEntry,
      amount: parseFloat(newEntry.amount)
    })
      .then(() => {
        setShowAddModal(false)
        setAddingEntry(false)
        setNewEntry({
          entry_date: new Date().toISOString().slice(0, 10),
          crop_tag: 'Paddy',
          entry_type: 'expense',
          category: 'cultivation',
          sub_category: 'Seeds & Nursery',
          description: '',
          amount: '',
          notes: ''
        })
        fetchLedger()
      })
      .catch(() => setAddingEntry(false))
  }

  const handleDeleteEntry = (id) => {
    if (!window.confirm('Are you sure you want to delete this ledger entry?')) return
    financeApi.deleteLedgerEntry(id)
      .then(() => fetchLedger())
      .catch(() => {})
  }

  const triggerVoiceWithPrompt = (prompt) => {
    if (onAskVoice) {
      onAskVoice(prompt)
    } else {
      window.dispatchEvent(new CustomEvent('farmAdvisor:voiceQuery', { detail: { prompt } }))
    }
  }

  return (
    <div className="px-4 py-4 space-y-5 max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700">
            <Wallet className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-gray-800">
              Farm & Household Finances
            </h1>
            <p className="text-xs text-gray-500">
              ಕೃಷಿ ಆರ್ಥಿಕತೆ · Whole-Year Balance Sheet, Crop Profit Ratio & Credit Advisory Hub
            </p>
          </div>
        </div>

        {activeSubTab === 'balancesheet' && (
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center justify-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs sm:text-sm font-bold shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Record Entry (ಖರ್ಚು/ಆದಾಯ ನಮೂದು)</span>
          </button>
        )}
      </div>

      {/* SUB-TABS NAVIGATION */}
      <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar border-b border-gray-200">
        {[
          { id: 'balancesheet', label: 'Annual Balance Sheet', labelKn: 'ವಾರ್ಷಿಕ ಲೆಕ್ಕಪತ್ರ', icon: BarChart3 },
          { id: 'comparator', label: 'Crop Profit Ratio Engine', labelKn: 'ಬೆಳೆ ಲಾಭಾಂಶ ಮತ್ತು ಪರ್ಯಾಯ ಬೆಳೆಗಳು', icon: TrendingUp },
          { id: 'advisory', label: 'Financing & Credit Hub', labelKn: 'ಕೃಷಿ ಸಾಲ ಮತ್ತು ವಿಮೆ ಸೌಲಭ್ಯಗಳು', icon: Landmark },
          { id: 'wealth', label: t('wealth_tab_title'), labelKn: t('wealth_tab_sub'), icon: PiggyBank },
        ].map((tab) => {
          const Icon = tab.icon
          const isActive = activeSubTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`flex-shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-t-xl text-xs sm:text-sm font-semibold transition-all border-b-2 ${
                isActive
                  ? 'border-emerald-600 text-emerald-800 bg-emerald-50/70'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-600' : 'text-gray-400'}`} />
              <div className="text-left">
                <div>{tab.label}</div>
                <div className="text-[10px] font-normal text-gray-400">{tab.labelKn}</div>
              </div>
            </button>
          )
        })}
      </div>

      {/* =========================================================================
          MODULE 2: WHOLE-YEAR FARM & HOUSEHOLD BALANCE SHEET
         ========================================================================= */}
      {activeSubTab === 'balancesheet' && (
        <div className="space-y-5">
          {loadingLedger ? (
            <div className="p-12 text-center text-gray-400">Loading whole-year financial records…</div>
          ) : balanceSheetData ? (
            <>
              {/* Top Metrics Cards Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5">
                <div className="bg-white border border-gray-200 p-3 rounded-2xl shadow-xs">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Cultivation Cost</span>
                  <div className="text-sm sm:text-base font-bold text-gray-800 mt-0.5">
                    ₹{balanceSheetData.total_cultivation_cost.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-gray-500">Seeds, fertilizer, labor</span>
                </div>

                <div className="bg-white border border-gray-200 p-3 rounded-2xl shadow-xs">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Irrigation Cost</span>
                  <div className="text-sm sm:text-base font-bold text-gray-800 mt-0.5">
                    ₹{balanceSheetData.total_irrigation_cost.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-gray-500">Power, canal & pumps</span>
                </div>

                <div className="bg-white border border-gray-200 p-3 rounded-2xl shadow-xs">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Harvest Expenses</span>
                  <div className="text-sm sm:text-base font-bold text-gray-800 mt-0.5">
                    ₹{balanceSheetData.total_harvest_expense.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-gray-500">Cutting, bagging, transport</span>
                </div>

                <div className="bg-white border border-gray-200 p-3 rounded-2xl shadow-xs">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Household Living</span>
                  <div className="text-sm sm:text-base font-bold text-rose-700 mt-0.5">
                    ₹{balanceSheetData.household_living_expenses.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-gray-500">Groceries & school</span>
                </div>

                <div className="bg-white border border-gray-200 p-3 rounded-2xl shadow-xs">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Crop Sales Revenue</span>
                  <div className="text-sm sm:text-base font-bold text-emerald-700 mt-0.5">
                    ₹{balanceSheetData.gross_crop_revenue.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-gray-500">Mandi auctions</span>
                </div>

                <div className="bg-gradient-to-br from-emerald-600 to-green-700 text-white p-3 rounded-2xl shadow-xs">
                  <span className="text-[10px] uppercase font-bold text-emerald-100">Net Farm Profit</span>
                  <div className="text-sm sm:text-base font-bold mt-0.5">
                    ₹{balanceSheetData.net_farm_profit.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-emerald-100">ROI: {balanceSheetData.overall_farm_roi_percent}%</span>
                </div>
              </div>

              {/* Monthly Income vs Expense Bar Chart */}
              <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-gray-800 text-sm sm:text-base">
                      12-Month Farm & Household Cashflow Breakdown
                    </h3>
                    <p className="text-xs text-gray-500">
                      Monthly incoming revenues vs outgoing cultivation and living expenses (2026)
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs font-medium">
                    <span className="flex items-center gap-1.5 text-emerald-700">
                      <span className="w-3 h-3 rounded-xs bg-emerald-600 inline-block" /> Total Inflow (ಆದಾಯ)
                    </span>
                    <span className="flex items-center gap-1.5 text-rose-600">
                      <span className="w-3 h-3 rounded-xs bg-rose-500 inline-block" /> Total Outflow (ಖರ್ಚು)
                    </span>
                  </div>
                </div>

                <div className="h-64 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={monthlyChart} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} tickFormatter={(val) => `₹${val/1000}k`} />
                      <Tooltip
                        formatter={(val) => [`₹${Number(val).toLocaleString()}`, '']}
                        labelStyle={{ fontWeight: 'bold' }}
                        contentStyle={{ borderRadius: '12px', fontSize: '12px' }}
                      />
                      <Bar dataKey="income" name="Total Inflow" fill="#059669" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="expense" name="Total Outflow" fill="#E11D48" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Crop Wise Summary Table */}
              <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-xs space-y-3">
                <h3 className="font-bold text-gray-800 text-sm sm:text-base">
                  Crop Wise Performance Breakdown
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs sm:text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-gray-600 font-semibold border-b border-gray-200">
                        <th className="py-2.5 px-3">Crop Name</th>
                        <th className="py-2.5 px-3 text-right">Total Production Cost</th>
                        <th className="py-2.5 px-3 text-right">Mandi Sales Revenue</th>
                        <th className="py-2.5 px-3 text-right font-bold text-gray-900">Net Crop Profit</th>
                        <th className="py-2.5 px-3 text-right text-emerald-700 font-bold">Profit Ratio</th>
                        <th className="py-2.5 px-3 text-right">ROI %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {balanceSheetData.crop_summary.map((c, i) => (
                        <tr key={i} className="hover:bg-emerald-50/40 transition-colors">
                          <td className="py-2.5 px-3 font-bold text-gray-800">{c.crop}</td>
                          <td className="py-2.5 px-3 text-right text-gray-600">₹{c.cost.toLocaleString()}</td>
                          <td className="py-2.5 px-3 text-right text-gray-800 font-semibold">₹{c.revenue.toLocaleString()}</td>
                          <td className="py-2.5 px-3 text-right font-bold text-emerald-800">₹{c.net_profit.toLocaleString()}</td>
                          <td className="py-2.5 px-3 text-right font-bold text-emerald-700">{c.profit_ratio}x</td>
                          <td className="py-2.5 px-3 text-right font-semibold text-gray-800">{c.roi_percent}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Transactions Ledger Table with Filters */}
              <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-xs space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="font-bold text-gray-800 text-sm sm:text-base">
                      Transaction Ledger ({ledgerEntries.length} Records)
                    </h3>
                    <p className="text-xs text-gray-500">
                      Itemized transactions tagged by crop, cultivation, irrigation, harvest, and household
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <select
                      value={filterCrop}
                      onChange={(e) => setFilterCrop(e.target.value)}
                      className="text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-2.5 py-1.5"
                    >
                      <option value="All">All Crops</option>
                      <option value="Paddy">Paddy</option>
                      <option value="Areca">Areca</option>
                      <option value="Ginger">Ginger</option>
                      <option value="General/Household">Household</option>
                    </select>

                    <select
                      value={filterType}
                      onChange={(e) => setFilterType(e.target.value)}
                      className="text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-2.5 py-1.5"
                    >
                      <option value="All">All Types</option>
                      <option value="expense">Expenses Only</option>
                      <option value="revenue">Revenues Only</option>
                    </select>
                  </div>
                </div>

                <div className="overflow-x-auto max-h-96">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-gray-50 border-b border-gray-200 text-gray-600 font-semibold z-10">
                      <tr>
                        <th className="py-2.5 px-3">Date</th>
                        <th className="py-2.5 px-3">Crop / Area</th>
                        <th className="py-2.5 px-3">Category</th>
                        <th className="py-2.5 px-3">Description</th>
                        <th className="py-2.5 px-3 text-right">Amount</th>
                        <th className="py-2.5 px-3 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {ledgerEntries.map((e) => {
                        const isExpense = e.entry_type === 'expense'
                        return (
                          <tr key={e.id} className="hover:bg-gray-50/70 transition-colors">
                            <td className="py-2 px-3 text-gray-500 whitespace-nowrap">{e.entry_date}</td>
                            <td className="py-2 px-3 font-semibold text-gray-800">
                              <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 text-[10px]">
                                {e.crop_tag}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-gray-600 capitalize">
                              {e.category.replace('_', ' ')}
                            </td>
                            <td className="py-2 px-3 text-gray-800 max-w-xs truncate" title={e.description}>
                              {e.description}
                            </td>
                            <td className={`py-2 px-3 text-right font-bold whitespace-nowrap ${
                              isExpense ? 'text-rose-600' : 'text-emerald-700'
                            }`}>
                              {isExpense ? '-₹' : '+₹'}{e.amount.toLocaleString()}
                            </td>
                            <td className="py-2 px-3 text-center">
                              <button
                                onClick={() => handleDeleteEntry(e.id)}
                                className="p-1 text-gray-400 hover:text-rose-600 rounded-md transition-colors"
                                title="Delete entry"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* =========================================================================
          MODULE 3: CROP PROFIT-RATIO ENGINE & WEATHER/SOIL ALTERNATIVE COMPARATOR
         ========================================================================= */}
      {activeSubTab === 'comparator' && (
        <div className="space-y-5">
          {/* Controls: Soil Selector and Temperature */}
          <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-gray-800 text-sm sm:text-base flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-600" />
                Soil & Weather-Matched Alternative Crop Comparator
              </h3>
              <p className="text-xs text-gray-500">
                Compare your current crop ROI against alternative high-profit crops adapted to your soil & climate
              </p>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-bold text-gray-600">Select Soil:</label>
              <select
                value={selectedSoil}
                onChange={(e) => setSelectedSoil(e.target.value)}
                className="text-xs font-semibold bg-gray-50 border border-gray-300 rounded-xl px-3 py-1.5 focus:ring-2 focus:ring-emerald-500"
              >
                {availableSoils.map((s, idx) => (
                  <option key={idx} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>

          {comparatorLoading ? (
            <div className="p-12 text-center text-gray-400">Evaluating soil and weather-matched crop alternatives…</div>
          ) : (
            <>
              {/* Currently Cultivated Crops Profit Ratios */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500">
                  Your Current Farm Crops (Recorded in Balance Sheet):
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {farmerCrops.map((c, i) => (
                    <div key={i} className="bg-white rounded-2xl border border-emerald-200 p-4 shadow-xs space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-gray-900 text-base">{c.crop_name}</span>
                        <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full">
                          Cultivated
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-1 text-xs">
                        <span className="text-gray-500">Cost: ₹{c.total_cost.toLocaleString()}</span>
                        <span className="text-gray-800 font-semibold text-right">Rev: ₹{c.gross_revenue.toLocaleString()}</span>
                      </div>
                      <div className="pt-2 border-t border-gray-100 flex items-center justify-between">
                        <div>
                          <span className="text-[10px] text-gray-400 uppercase font-semibold">Profit Ratio</span>
                          <div className="text-sm font-bold text-emerald-700">{c.profit_ratio}x</div>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-gray-400 uppercase font-semibold">Net Profit</span>
                          <div className="text-sm font-bold text-gray-900">₹{c.net_profit.toLocaleString()}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommended Alternative Crops Matching Soil & Weather */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500">
                    Recommended High-ROI Alternative Crops for {selectedSoil}:
                  </h4>
                  <span className="text-xs text-emerald-700 font-semibold">
                    Matched to {comparatorTemp}°C Karnataka climate
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {recommendedAlternatives.map((alt) => (
                    <div
                      key={alt.id}
                      className="bg-white rounded-2xl border border-gray-200 p-4 shadow-xs hover:border-emerald-300 transition-colors space-y-3 flex flex-col justify-between"
                    >
                      <div>
                        {/* Header */}
                        <div className="flex items-center justify-between">
                          <div>
                            <h5 className="font-bold text-gray-900 text-base">{alt.crop_name}</h5>
                            {alt.crop_kannada && (
                              <p className="text-xs text-emerald-900 font-semibold">{alt.crop_kannada}</p>
                            )}
                          </div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                            alt.is_soil_match
                              ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                              : 'bg-amber-100 text-amber-800 border-amber-200'
                          }`}>
                            {alt.is_soil_match ? '✓ Soil Matched' : 'Moderate Match'}
                          </span>
                        </div>

                        {/* Metrics Table */}
                        <div className="grid grid-cols-3 gap-2 bg-gray-50 p-2.5 rounded-xl text-center mt-3 text-xs">
                          <div>
                            <span className="text-[10px] text-gray-400 uppercase font-semibold">Net / Acre</span>
                            <div className="font-bold text-emerald-800 mt-0.5">₹{alt.avg_net_profit_per_acre.toLocaleString()}</div>
                          </div>
                          <div>
                            <span className="text-[10px] text-gray-400 uppercase font-semibold">Profit Ratio</span>
                            <div className="font-bold text-emerald-700 mt-0.5">{alt.profit_ratio}x</div>
                          </div>
                          <div>
                            <span className="text-[10px] text-gray-400 uppercase font-semibold">Water Need</span>
                            <div className="font-bold text-blue-700 mt-0.5">{alt.water_demand}</div>
                          </div>
                        </div>

                        {/* Advantages */}
                        <div className="mt-3 p-2.5 bg-emerald-50/60 rounded-xl border border-emerald-100 text-xs text-emerald-950">
                          <span className="font-semibold text-emerald-900 block mb-0.5">Agronomic Advantage:</span>
                          <p className="text-[11px] leading-relaxed">{alt.advantages}</p>
                        </div>
                      </div>

                      <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
                        <span className="text-gray-400">Duration: <strong>{alt.growth_duration_days} days</strong></span>
                        <button
                          onClick={() => triggerVoiceWithPrompt(`${alt.crop_name} ಬೆಳೆಯ ಕೃಷಿ ವೆಚ್ಚ, ನಿರೀಕ್ಷಿತ ಲಾಭ ಮತ್ತು ನೀರಾವರಿ ಪದ್ಧತಿ ತಿಳಿಸಿ`)}
                          className="text-emerald-700 font-semibold hover:underline flex items-center gap-1"
                        >
                          Ask Voice Advisor <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* =========================================================================
          MODULE 4: AGRICULTURAL FINANCING & CREDIT ADVISORY HUB
         ========================================================================= */}
      {activeSubTab === 'advisory' && (
        <div className="space-y-5">
          {advisoryLoading || !advisoryData ? (
            <div className="p-12 text-center text-gray-400">Loading agricultural financing guide…</div>
          ) : (
            <>
              {/* Credit Pillars Category Selector */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
                {advisoryData.credit_pillars.map((pillar) => {
                  const isSelected = activeCreditPillar === pillar.id
                  return (
                    <button
                      key={pillar.id}
                      onClick={() => setActiveCreditPillar(pillar.id)}
                      className={`p-3 rounded-2xl border text-left transition-all ${
                        isSelected
                          ? 'bg-emerald-700 text-white border-emerald-800 shadow-sm ring-2 ring-emerald-600'
                          : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <span className={`text-[10px] font-bold uppercase tracking-wider block ${
                        isSelected ? 'text-emerald-200' : 'text-emerald-700'
                      }`}>
                        {pillar.badge}
                      </span>
                      <h4 className="font-bold text-xs mt-1 leading-tight line-clamp-2">
                        {pillar.title.split('&')[0]}
                      </h4>
                    </button>
                  )
                })}
              </div>

              {/* Active Credit Pillar Details Card */}
              {(() => {
                const pillar = advisoryData.credit_pillars.find(p => p.id === activeCreditPillar) || advisoryData.credit_pillars[0]
                return (
                  <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
                      <div>
                        <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                          {pillar.badge}
                        </span>
                        <h3 className="font-bold text-gray-900 text-base sm:text-lg mt-1.5">
                          {pillar.title}
                        </h3>
                        {pillar.title_kannada && (
                          <p className="text-xs font-semibold text-emerald-900 mt-0.5">
                            {pillar.title_kannada}
                          </p>
                        )}
                      </div>

                      <button
                        onClick={() => triggerVoiceWithPrompt(`${pillar.title} ಬಗ್ಗೆ ಮತ್ತು ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ವಿಧಾನವನ್ನು ನನ್ನ ಭಾಷೆಯಲ್ಲಿ ತಿಳಿಸಿ`)}
                        className="self-start sm:self-center px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow-xs"
                      >
                        Ask Voice Advisor
                      </button>
                    </div>

                    <p className="text-xs text-gray-600 leading-relaxed">
                      {pillar.description}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Key Highlights */}
                      <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-3.5 space-y-2">
                        <h5 className="font-bold text-emerald-900 uppercase text-[10px] tracking-wide">
                          Key Scheme Highlights & Benefits:
                        </h5>
                        <ul className="space-y-1.5">
                          {pillar.key_highlights.map((h, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-emerald-950 font-medium">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                              <span>{h}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Required Documents */}
                      <div className="bg-gray-50 border border-gray-200 rounded-xl p-3.5 space-y-2">
                        <h5 className="font-bold text-gray-800 uppercase text-[10px] tracking-wide">
                          Mandatory Verification Documents:
                        </h5>
                        <ul className="space-y-1.5">
                          {pillar.required_documents.map((d, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-gray-700">
                              <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0 mt-0.5" />
                              <span>{d}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Interactive Loan / Subsidy Estimator for KCC / Solar */}
                    {pillar.id === 'kcc' && (
                      <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-4 space-y-3">
                        <h5 className="font-bold text-emerald-900 text-xs sm:text-sm">
                          KCC Scale-of-Finance Credit Limit Calculator
                        </h5>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                          <div>
                            <label className="text-[11px] font-bold text-gray-600 block mb-1">Crop Type</label>
                            <select
                              value={calcCropType}
                              onChange={(e) => setCalcCropType(e.target.value)}
                              className="w-full text-xs font-semibold bg-white border border-gray-300 rounded-lg p-2"
                            >
                              <option value="Paddy">Paddy (₹34,000/Acre)</option>
                              <option value="Areca">Arecanut (₹85,000/Acre)</option>
                              <option value="Ginger">Ginger (₹95,000/Acre)</option>
                              <option value="Corn">Corn / Maize (₹26,000/Acre)</option>
                            </select>
                          </div>
                          <div>
                            <label className="text-[11px] font-bold text-gray-600 block mb-1">Land Area (Acres)</label>
                            <input
                              type="number"
                              step="0.5"
                              min="0.5"
                              max="20"
                              value={calcAcreage}
                              onChange={(e) => setCalcAcreage(parseFloat(e.target.value) || 1)}
                              className="w-full text-xs font-semibold bg-white border border-gray-300 rounded-lg p-2"
                            />
                          </div>
                          <div className="bg-white p-2.5 rounded-lg border border-emerald-200 text-center flex flex-col justify-center">
                            <span className="text-[10px] text-gray-400 font-bold uppercase">Sanctioned Limit</span>
                            <div className="font-bold text-emerald-700 text-base">
                              ₹{(calcAcreage * (pillar.calculator_defaults.scale_per_acre[calcCropType] || 34000)).toLocaleString()}
                            </div>
                            <span className="text-[10px] text-emerald-600 font-semibold">Net Interest: 4% p.a.</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })()}
            </>
          )}
        </div>
      )}

      {/* =========================================================================
          MODULE 5: MONEY MANAGEMENT & FUTURE INVESTING
         ========================================================================= */}
      {activeSubTab === 'wealth' && (
        <MoneyManagementTab netFarmProfit={balanceSheetData?.net_farm_profit} />
      )}

      {/* =========================================================================
          MODAL: ADD NEW TRANSACTION RECORD
         ========================================================================= */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-2">
              <h3 className="font-bold text-gray-900 text-base">Record Farm Transaction</h3>
              <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>

            <form onSubmit={handleAddEntry} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-gray-700 block mb-1">Date</label>
                  <input
                    type="date"
                    value={newEntry.entry_date}
                    onChange={(e) => setNewEntry({ ...newEntry, entry_date: e.target.value })}
                    required
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl"
                  />
                </div>
                <div>
                  <label className="font-bold text-gray-700 block mb-1">Type</label>
                  <select
                    value={newEntry.entry_type}
                    onChange={(e) => setNewEntry({ ...newEntry, entry_type: e.target.value })}
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl font-semibold"
                  >
                    <option value="expense">Expense (ವೆಚ್ಚ)</option>
                    <option value="revenue">Revenue (ಆದಾಯ)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-gray-700 block mb-1">Crop / Target</label>
                  <select
                    value={newEntry.crop_tag}
                    onChange={(e) => setNewEntry({ ...newEntry, crop_tag: e.target.value })}
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl font-semibold"
                  >
                    <option value="Paddy">Paddy</option>
                    <option value="Areca">Arecanut</option>
                    <option value="Ginger">Ginger</option>
                    <option value="Corn">Corn</option>
                    <option value="General/Household">Household</option>
                  </select>
                </div>
                <div>
                  <label className="font-bold text-gray-700 block mb-1">Category</label>
                  <select
                    value={newEntry.category}
                    onChange={(e) => setNewEntry({ ...newEntry, category: e.target.value })}
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl font-semibold"
                  >
                    <option value="cultivation">Cultivation</option>
                    <option value="irrigation">Irrigation</option>
                    <option value="harvest">Harvest</option>
                    <option value="crop_sales">Crop Sales</option>
                    <option value="household">Household</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-bold text-gray-700 block mb-1">Description</label>
                <input
                  type="text"
                  placeholder="e.g. 2 bags Urea or Tractor harvest rent"
                  value={newEntry.description}
                  onChange={(e) => setNewEntry({ ...newEntry, description: e.target.value })}
                  required
                  className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl"
                />
              </div>

              <div>
                <label className="font-bold text-gray-700 block mb-1">Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="e.g. 4500"
                  value={newEntry.amount}
                  onChange={(e) => setNewEntry({ ...newEntry, amount: e.target.value })}
                  required
                  className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl font-bold text-sm"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-xl text-gray-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingEntry}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition-colors"
                >
                  {addingEntry ? 'Saving…' : 'Save Entry'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
