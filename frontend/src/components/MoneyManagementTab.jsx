import React, { useState, useEffect } from 'react'
import {
  PiggyBank, ShieldCheck, TrendingUp, CheckCircle2, AlertTriangle,
  Plus, Calculator, Landmark, Calendar, ArrowRight, Lock, Wallet,
  BarChart3, X, Sparkles, Heart, Briefcase
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from 'recharts'
import { financeApi } from '../api/client'
import { useI18n } from '../context/I18nContext'

const PAN_REGEX = /^[A-Z]{5}[0-9]{4}[A-Z]$/

const COMMITMENT_OPTIONS = [
  { id: 'child_education', labelKey: 'wealth_comm_child_edu' },
  { id: 'marriage', labelKey: 'wealth_comm_marriage' },
  { id: 'land_tractor', labelKey: 'wealth_comm_land_tractor' },
  { id: 'retirement', labelKey: 'wealth_comm_retirement' },
  { id: 'emergency_medical', labelKey: 'wealth_comm_emergency_medical' },
]

const RISK_OPTIONS = [
  { id: 'low', labelKey: 'wealth_risk_safe' },
  { id: 'moderate', labelKey: 'wealth_risk_balanced' },
  { id: 'growth', labelKey: 'wealth_risk_growth' },
]

export default function MoneyManagementTab({ netFarmProfit }) {
  const { t } = useI18n()

  // ===========================================================================
  // SECTION A: Profit Protection & Diversified Business Planner
  // ===========================================================================
  const [netProfitInput, setNetProfitInput] = useState(
    netFarmProfit != null ? Number(netFarmProfit) : 1154700
  )
  const [hasEditedProfit, setHasEditedProfit] = useState(false)
  const [reserves, setReserves] = useState({
    household_reserve: 180000,
    next_cultivation_reserve: 120000,
    harvest_reserve: 65000,
    other_reserve: 35000,
  })
  const [allocateResult, setAllocateResult] = useState(null)
  const [allocateLoading, setAllocateLoading] = useState(false)

  useEffect(() => {
    if (!hasEditedProfit && netFarmProfit != null && !Number.isNaN(Number(netFarmProfit))) {
      setNetProfitInput(Number(netFarmProfit))
    }
  }, [netFarmProfit, hasEditedProfit])

  useEffect(() => {
    const timer = setTimeout(() => {
      setAllocateLoading(true)
      financeApi
        .allocateWealth({
          net_profit: Number(netProfitInput) || 0,
          household_reserve: Number(reserves.household_reserve) || 0,
          next_cultivation_reserve: Number(reserves.next_cultivation_reserve) || 0,
          harvest_reserve: Number(reserves.harvest_reserve) || 0,
          other_reserve: Number(reserves.other_reserve) || 0,
        })
        .then((res) => {
          setAllocateResult(res.data)
          setAllocateLoading(false)
        })
        .catch(() => setAllocateLoading(false))
    }, 250)
    return () => clearTimeout(timer)
  }, [netProfitInput, reserves])

  const updateReserve = (field, rawVal) => {
    const num = Math.max(0, Number(rawVal) || 0)
    setReserves((prev) => ({ ...prev, [field]: num }))
  }

  const sliderMax = Math.max(500000, Math.round((Number(netProfitInput) || 500000) * 0.8))

  // ===========================================================================
  // SECTION B: PAN Loan Check & Debt Optimizer
  // ===========================================================================
  const [panInput, setPanInput] = useState('ABCDE1234F')
  const [panError, setPanError] = useState('')
  const [panData, setPanData] = useState(null)
  const [panLoading, setPanLoading] = useState(false)
  const [closingLoanId, setClosingLoanId] = useState(null)

  const [showAddLoanModal, setShowAddLoanModal] = useState(false)
  const [addingLoan, setAddingLoan] = useState(false)
  const [newLoan, setNewLoan] = useState({
    lender_name: '',
    loan_type: 'Informal/Moneylender',
    principal_amount: '',
    outstanding_balance: '',
    interest_rate_annual: '18',
    emi_amount: '',
    next_due_date: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
    interest_accumulated: '0',
  })

  const fetchPanLoans = (panToCheck, surplusOverride) => {
    const cleaned = (panToCheck || '').trim().toUpperCase()
    if (!PAN_REGEX.test(cleaned)) {
      setPanError(t('wealth_pan_invalid_err'))
      return
    }
    setPanError('')
    setPanLoading(true)
    financeApi
      .checkPanLoans({
        pan: cleaned,
        available_surplus:
          surplusOverride != null
            ? surplusOverride
            : allocateResult?.investable_surplus,
      })
      .then((res) => {
        setPanData(res.data)
        setPanLoading(false)
      })
      .catch((err) => {
        setPanError(err?.response?.data?.detail || t('wealth_pan_invalid_err'))
        setPanLoading(false)
      })
  }

  useEffect(() => {
    fetchPanLoans('ABCDE1234F')
  }, [])

  const handleCheckLoansSubmit = (e) => {
    e.preventDefault()
    fetchPanLoans(panInput)
  }

  const handleCloseLoan = (loanId) => {
    setClosingLoanId(loanId)
    financeApi
      .closeLoan(loanId)
      .then(() => {
        setClosingLoanId(null)
        fetchPanLoans(panInput)
      })
      .catch(() => setClosingLoanId(null))
  }

  const handleAddLoanSubmit = (e) => {
    e.preventDefault()
    const cleanedPan = (panInput || '').trim().toUpperCase()
    if (!PAN_REGEX.test(cleanedPan)) {
      setPanError(t('wealth_pan_invalid_err'))
      return
    }
    if (!newLoan.lender_name || !newLoan.principal_amount) return
    setAddingLoan(true)
    financeApi
      .addLoan({
        pan: cleanedPan,
        lender_name: newLoan.lender_name,
        loan_type: newLoan.loan_type,
        principal_amount: parseFloat(newLoan.principal_amount),
        outstanding_balance: newLoan.outstanding_balance
          ? parseFloat(newLoan.outstanding_balance)
          : parseFloat(newLoan.principal_amount),
        interest_rate_annual: parseFloat(newLoan.interest_rate_annual) || 0,
        emi_amount: parseFloat(newLoan.emi_amount) || 0,
        next_due_date: newLoan.next_due_date,
        interest_accumulated: parseFloat(newLoan.interest_accumulated) || 0,
        status: 'active',
      })
      .then(() => {
        setAddingLoan(false)
        setShowAddLoanModal(false)
        setNewLoan({
          lender_name: '',
          loan_type: 'Informal/Moneylender',
          principal_amount: '',
          outstanding_balance: '',
          interest_rate_annual: '18',
          emi_amount: '',
          next_due_date: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
          interest_accumulated: '0',
        })
        fetchPanLoans(cleanedPan)
      })
      .catch(() => setAddingLoan(false))
  }

  // ===========================================================================
  // SECTION C: Life Commitments & Investment Plan Matcher
  // ===========================================================================
  const [monthlyIncome, setMonthlyIncome] = useState(32000)
  const [riskProfile, setRiskProfile] = useState('moderate')
  const [commitments, setCommitments] = useState(['child_education', 'emergency_medical'])
  const [investPlan, setInvestPlan] = useState(null)
  const [investLoading, setInvestLoading] = useState(false)

  const toggleCommitment = (id) => {
    setCommitments((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setInvestLoading(true)
      financeApi
        .getInvestPlan({
          monthly_income: Number(monthlyIncome) || 0,
          risk_profile: riskProfile,
          commitments,
        })
        .then((res) => {
          setInvestPlan(res.data)
          setInvestLoading(false)
        })
        .catch(() => setInvestLoading(false))
    }, 200)
    return () => clearTimeout(timer)
  }, [monthlyIncome, riskProfile, commitments])

  // ===========================================================================
  // SECTION D: Future Returns Calculator
  // ===========================================================================
  const [calcMode, setCalcMode] = useState('sip') // 'sip' | 'fd' | 'lumpsum'
  const [calcAmount, setCalcAmount] = useState(5000)
  const [calcRate, setCalcRate] = useState(12.0)
  const [calcYears, setCalcYears] = useState(10)
  const [calcResult, setCalcResult] = useState(null)

  const handleModeSwitch = (mode) => {
    setCalcMode(mode)
    if (mode === 'sip') {
      setCalcAmount(5000)
      setCalcRate(12.0)
    } else if (mode === 'fd') {
      setCalcAmount(100000)
      setCalcRate(7.2)
    } else {
      setCalcAmount(100000)
      setCalcRate(11.5)
    }
  }

  useEffect(() => {
    const safeAmount = Math.max(100, Number(calcAmount) || 100)
    const safeRate = Math.max(0, Number(calcRate) || 0)
    const safeYears = Math.min(35, Math.max(1, Number(calcYears) || 1))

    const timer = setTimeout(() => {
      financeApi
        .calculateReturns({
          mode: calcMode,
          amount: safeAmount,
          annual_rate: safeRate,
          years: safeYears,
        })
        .then((res) => setCalcResult(res.data))
        .catch(() => {})
    }, 150)
    return () => clearTimeout(timer)
  }, [calcMode, calcAmount, calcRate, calcYears])

  const localSurplus = Math.max(
    0,
    (Number(netProfitInput) || 0) -
      ((Number(reserves.household_reserve) || 0) +
        (Number(reserves.next_cultivation_reserve) || 0) +
        (Number(reserves.harvest_reserve) || 0) +
        (Number(reserves.other_reserve) || 0))
  )

  const displayedTotalReserves =
    allocateResult?.total_secured_reserves ??
    ((Number(reserves.household_reserve) || 0) +
      (Number(reserves.next_cultivation_reserve) || 0) +
      (Number(reserves.harvest_reserve) || 0) +
      (Number(reserves.other_reserve) || 0))

  const displayedSurplus = allocateResult?.investable_surplus ?? localSurplus

  return (
    <div className="space-y-6">
      {/* =====================================================================
          SECTION A: PROFIT PROTECTION & DIVERSIFIED BUSINESS PLANNER
         ===================================================================== */}
      <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
          <div className="flex items-start gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-bold text-gray-900">
                {t('wealth_sec_a_title')}
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">{t('wealth_sec_a_sub')}</p>
            </div>
          </div>
          <span className="self-start sm:self-center text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            {t('wealth_autofilled_ledger')}
          </span>
        </div>

        {/* Net Profit + Safe Investable Surplus Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-4 space-y-1.5">
            <label className="text-[11px] font-bold uppercase tracking-wide text-gray-500 block">
              {t('wealth_net_farm_profit')}
            </label>
            <div className="flex items-center gap-1.5">
              <span className="text-lg font-bold text-gray-700">₹</span>
              <input
                type="number"
                min="0"
                step="1000"
                value={netProfitInput}
                onChange={(e) => {
                  setHasEditedProfit(true)
                  setNetProfitInput(Math.max(0, Number(e.target.value) || 0))
                }}
                className="w-full bg-white border border-gray-300 rounded-xl px-3 py-1.5 text-base font-bold text-gray-900 focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div className="bg-amber-50/70 border border-amber-200 rounded-2xl p-4 flex flex-col justify-center">
            <span className="text-[11px] font-bold uppercase tracking-wide text-amber-800">
              {t('wealth_total_locked')}
            </span>
            <div className="text-xl font-bold text-amber-900 mt-1">
              ₹{Number(displayedTotalReserves).toLocaleString()}
            </div>
          </div>

          <div className="bg-gradient-to-br from-emerald-600 to-green-700 text-white rounded-2xl p-4 shadow-sm flex flex-col justify-center">
            <span className="text-[11px] font-bold uppercase tracking-wide text-emerald-100">
              {t('wealth_safe_surplus')}
            </span>
            <div className="text-2xl font-extrabold mt-0.5">
              ₹{Number(displayedSurplus).toLocaleString()}
            </div>
            {allocateResult?.surplus_tier && (
              <span className="text-[11px] text-emerald-100 font-medium mt-0.5">
                {allocateResult.surplus_tier}
              </span>
            )}
            {allocateResult?.reserve_deficit > 0 && (
              <span className="text-[11px] text-amber-200 font-semibold mt-0.5">
                {t('wealth_reserve_deficit')}: ₹{allocateResult.reserve_deficit.toLocaleString()}
              </span>
            )}
          </div>
        </div>

        {/* 4 Reserve Inputs + Sliders */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { key: 'household_reserve', label: t('wealth_reserve_household') },
            { key: 'next_cultivation_reserve', label: t('wealth_reserve_cultivation') },
            { key: 'harvest_reserve', label: t('wealth_reserve_harvest') },
            { key: 'other_reserve', label: t('wealth_reserve_other') },
          ].map((item) => (
            <div
              key={item.key}
              className="bg-gray-50/80 border border-gray-200 rounded-xl p-3.5 space-y-2"
            >
              <div className="flex items-center justify-between gap-2">
                <label className="text-xs font-bold text-gray-700">{item.label}</label>
                <div className="flex items-center gap-1 bg-white border border-gray-300 rounded-lg px-2 py-1">
                  <span className="text-xs font-semibold text-gray-500">₹</span>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    value={reserves[item.key]}
                    onChange={(e) => updateReserve(item.key, e.target.value)}
                    className="w-24 text-right text-xs font-bold text-gray-900 focus:outline-none"
                  />
                </div>
              </div>
              <input
                type="range"
                min="0"
                max={sliderMax}
                step="5000"
                value={Math.min(sliderMax, reserves[item.key])}
                onChange={(e) => updateReserve(item.key, e.target.value)}
                className="w-full accent-emerald-600 cursor-pointer"
              />
            </div>
          ))}
        </div>

        {/* Matched Diversified Business Ideas */}
        <div className="space-y-3 pt-1">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-600 flex items-center gap-1.5">
              <Briefcase className="w-4 h-4 text-emerald-600" />
              {t('wealth_matched_ideas')}
            </h3>
            {allocateLoading && (
              <span className="text-[11px] text-gray-400">{t('loading')}</span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {(allocateResult?.matched_business_ideas || []).map((idea) => (
              <div
                key={idea.id}
                className="bg-white border border-emerald-200 rounded-2xl p-4 shadow-xs flex flex-col justify-between space-y-3 hover:border-emerald-400 transition-colors"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {idea.category}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        idea.fits_current_surplus
                          ? 'bg-emerald-600 text-white'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {idea.fits_current_surplus
                        ? t('wealth_fits_surplus')
                        : `${t('wealth_gap_label')}: ₹${Number(idea.funding_gap).toLocaleString()}`}
                    </span>
                  </div>

                  <h4 className="font-bold text-sm text-gray-900 leading-snug">
                    {idea.name}
                  </h4>
                  <p className="text-[11px] text-gray-600 leading-relaxed">
                    {idea.description}
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-gray-100">
                  <div className="grid grid-cols-3 gap-1.5 text-center bg-gray-50 p-2 rounded-xl">
                    <div>
                      <span className="text-[9px] uppercase font-bold text-gray-400 block">
                        {t('wealth_startup_cost')}
                      </span>
                      <span className="text-xs font-bold text-gray-900">
                        ₹{Number(idea.estimated_startup_cost).toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span className="text-[9px] uppercase font-bold text-gray-400 block">
                        {t('wealth_expected_roi')}
                      </span>
                      <span className="text-xs font-bold text-emerald-700">
                        {idea.expected_annual_roi_pct}%
                      </span>
                    </div>
                    <div>
                      <span className="text-[9px] uppercase font-bold text-gray-400 block">
                        {t('wealth_payback')}
                      </span>
                      <span className="text-xs font-bold text-blue-700">
                        {idea.payback_period}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-gray-500">
                    <span>
                      {t('wealth_risk_level')}: <strong className="text-gray-800">{idea.risk_level}</strong>
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* =====================================================================
          SECTION B: PAN LOAN CHECK & DEBT OPTIMIZER
         ===================================================================== */}
      <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-sm sm:text-base font-bold text-gray-900">
                  {t('wealth_sec_b_title')}
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  {t('wealth_demo_bureau_badge')}
                </span>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowAddLoanModal(true)}
            className="self-start sm:self-center flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>{t('wealth_add_loan_btn')}</span>
          </button>
        </div>

        {/* PAN Check Input Form */}
        <form
          onSubmit={handleCheckLoansSubmit}
          className="flex flex-col sm:flex-row sm:items-end gap-3 bg-gray-50 p-3.5 rounded-xl border border-gray-200"
        >
          <div className="flex-1 space-y-1">
            <label className="text-xs font-bold text-gray-700 block">
              {t('wealth_pan_label')}
            </label>
            <input
              type="text"
              maxLength={10}
              placeholder="ABCDE1234F"
              value={panInput}
              onChange={(e) => {
                setPanError('')
                setPanInput(e.target.value.toUpperCase())
              }}
              className="w-full sm:max-w-xs bg-white border border-gray-300 rounded-xl px-3 py-2 text-sm font-bold tracking-widest uppercase text-gray-900 focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <button
            type="submit"
            disabled={panLoading}
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs sm:text-sm font-bold rounded-xl shadow-xs transition-colors"
          >
            {panLoading ? t('loading') : t('wealth_check_loans')}
          </button>
        </form>

        {panError && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs font-semibold text-rose-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{panError}</span>
          </div>
        )}

        {panData && (
          <div className="space-y-4">
            {/* Summary Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-3">
                <span className="text-[10px] font-bold uppercase text-gray-400">
                  {t('wealth_masked_pan')}
                </span>
                <div className="text-sm font-bold text-gray-900 mt-0.5 tracking-wider">
                  {panData.pan_masked}
                </div>
              </div>
              <div className="bg-rose-50/70 border border-rose-200 rounded-xl p-3">
                <span className="text-[10px] font-bold uppercase text-rose-700">
                  {t('wealth_total_outstanding')}
                </span>
                <div className="text-base font-bold text-rose-800 mt-0.5">
                  ₹{Number(panData.total_outstanding).toLocaleString()}
                </div>
              </div>
              <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-3">
                <span className="text-[10px] font-bold uppercase text-amber-700">
                  {t('wealth_total_interest_acc')}
                </span>
                <div className="text-base font-bold text-amber-900 mt-0.5">
                  ₹{Number(panData.total_interest_accumulated).toLocaleString()}
                </div>
              </div>
              <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-3">
                <span className="text-[10px] font-bold uppercase text-emerald-700">
                  {t('wealth_active_loans')}
                </span>
                <div className="text-base font-bold text-emerald-800 mt-0.5">
                  {panData.active_loans_count} / {panData.total_loans}
                </div>
              </div>
            </div>

            {/* Highlighted Smart Action Plan Banner */}
            {panData.action_plan && (
              <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50 border-2 border-emerald-400 rounded-2xl p-4 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-emerald-700 flex-shrink-0" />
                    <h3 className="font-bold text-sm sm:text-base text-emerald-950">
                      {t('wealth_smart_action_plan')}
                    </h3>
                  </div>
                  {panData.action_plan.total_annual_interest_saved > 0 && (
                    <span className="self-start sm:self-center text-xs font-extrabold px-3 py-1 rounded-full bg-emerald-600 text-white">
                      {t('wealth_annual_interest_saved')}: ₹
                      {Number(panData.action_plan.total_annual_interest_saved).toLocaleString()}
                    </span>
                  )}
                </div>

                <p className="text-xs sm:text-sm font-semibold text-emerald-900 leading-relaxed">
                  {panData.action_plan.summary_note}
                </p>

                {panData.action_plan.payoff_steps?.length > 0 && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {panData.action_plan.payoff_steps.map((step) => (
                      <div
                        key={step.loan_id}
                        className="bg-white/90 border border-emerald-200 rounded-xl p-2.5 text-xs flex items-center justify-between gap-2"
                      >
                        <div>
                          <div className="font-bold text-gray-900">{step.lender_name}</div>
                          <div className="text-[11px] text-gray-500">
                            {step.interest_rate_annual}% · {step.action}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold text-emerald-700">
                            ₹{Number(step.amount_allocated).toLocaleString()}
                          </div>
                          <div className="text-[10px] text-emerald-600 font-semibold">
                            -₹{Number(step.estimated_annual_interest_saved).toLocaleString()}/yr
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Low-Interest Refinancing Alternatives */}
                <div className="pt-2 border-t border-emerald-200/80 space-y-2">
                  <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-900 flex items-center gap-1.5">
                    <Landmark className="w-3.5 h-3.5" />
                    {t('wealth_low_interest_alts')}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                    {(panData.action_plan.refinancing_alternatives || []).map((alt, idx) => (
                      <div
                        key={idx}
                        className="bg-white border border-emerald-200 rounded-xl p-2.5 text-xs space-y-1"
                      >
                        <div className="font-bold text-emerald-800">{alt.option}</div>
                        <div className="text-[11px] font-semibold text-emerald-600">
                          {alt.typical_range}
                        </div>
                        <p className="text-[11px] text-gray-600 leading-snug">{alt.best_for}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Upcoming Due Reminders */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-3.5 space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wide text-gray-700 flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-emerald-600" />
                {t('wealth_upcoming_dues')}
              </h4>
              {panData.upcoming_dues?.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  {panData.upcoming_dues.map((due) => (
                    <div
                      key={due.loan_id}
                      className="bg-white border border-gray-200 rounded-xl p-2.5 text-xs flex items-center justify-between gap-2"
                    >
                      <div>
                        <div className="font-bold text-gray-900 line-clamp-1">
                          {due.lender_name}
                        </div>
                        <div className="text-[11px] text-gray-500">
                          {t('wealth_due_date_short')}: <strong>{due.next_due_date}</strong>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="font-bold text-rose-700">
                          ₹{Number(due.emi_amount).toLocaleString()}
                        </div>
                        <div className="text-[10px] text-gray-500">
                          {due.interest_rate_annual}% p.a.
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500">{t('wealth_no_upcoming_dues')}</p>
              )}
            </div>

            {/* Individual Loan Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(panData.loans || []).map((loan) => {
                const isClosed = loan.status === 'closed'
                const isHighInterest = !isClosed && loan.interest_rate_annual >= 15
                return (
                  <div
                    key={loan.id}
                    className={`rounded-2xl border p-4 space-y-2.5 transition-colors ${
                      isClosed
                        ? 'bg-gray-50 border-gray-200 opacity-75'
                        : isHighInterest
                        ? 'bg-rose-50/40 border-rose-200'
                        : 'bg-white border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                          {loan.loan_type}
                        </span>
                        <h4 className="font-bold text-sm text-gray-900 mt-1">
                          {loan.lender_name}
                        </h4>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                          isClosed
                            ? 'bg-gray-200 text-gray-700'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {isClosed ? t('wealth_status_closed') : t('wealth_status_active')}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs bg-white/80 border border-gray-100 rounded-xl p-2.5">
                      <div>
                        <span className="text-[10px] text-gray-400 block">
                          {t('wealth_outstanding')}
                        </span>
                        <span className="font-bold text-gray-900">
                          ₹{Number(loan.outstanding_balance).toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-gray-400 block">
                          {t('wealth_rate_short')}
                        </span>
                        <span
                          className={`font-bold ${
                            loan.interest_rate_annual >= 15 ? 'text-rose-600' : 'text-emerald-700'
                          }`}
                        >
                          {loan.interest_rate_annual}% p.a.
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-gray-400 block">
                          {t('wealth_emi_short')}
                        </span>
                        <span className="font-bold text-gray-800">
                          ₹{Number(loan.emi_amount).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-1 text-xs">
                      <span className="text-gray-500">
                        {t('wealth_due_date_short')}: <strong>{loan.next_due_date}</strong>
                      </span>
                      {!isClosed && (
                        <button
                          type="button"
                          disabled={closingLoanId === loan.id}
                          onClick={() => handleCloseLoan(loan.id)}
                          className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 rounded-xl font-bold text-[11px] transition-colors"
                        >
                          {closingLoanId === loan.id
                            ? t('wealth_closing_loan')
                            : t('wealth_mark_closed')}
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </section>

      {/* =====================================================================
          SECTION C: LIFE COMMITMENTS & INVESTMENT PLAN MATCHER
         ===================================================================== */}
      <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-5">
        <div className="flex items-center gap-2.5 border-b border-gray-100 pb-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
            <Heart className="w-5 h-5" />
          </div>
          <h2 className="text-sm sm:text-base font-bold text-gray-900">
            {t('wealth_sec_c_title')}
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Monthly Income & Risk Selector */}
          <div className="space-y-3 bg-gray-50 p-3.5 rounded-xl border border-gray-200">
            <div>
              <label className="text-xs font-bold text-gray-700 block mb-1">
                {t('wealth_monthly_income_label')}
              </label>
              <input
                type="number"
                min="0"
                step="1000"
                value={monthlyIncome}
                onChange={(e) => setMonthlyIncome(Math.max(0, Number(e.target.value) || 0))}
                className="w-full bg-white border border-gray-300 rounded-xl px-3 py-2 text-sm font-bold text-gray-900 focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div>
              <span className="text-xs font-bold text-gray-700 block mb-1.5">
                {t('wealth_risk_selector')}
              </span>
              <div className="grid grid-cols-3 gap-2">
                {RISK_OPTIONS.map((opt) => {
                  const active = riskProfile === opt.id
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setRiskProfile(opt.id)}
                      className={`py-2 px-2 rounded-xl text-xs font-bold border transition-all ${
                        active
                          ? 'bg-emerald-600 text-white border-emerald-700 shadow-xs'
                          : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
                      }`}
                    >
                      {t(opt.labelKey)}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Clickable Commitment Chips */}
          <div className="space-y-2.5 bg-gray-50 p-3.5 rounded-xl border border-gray-200">
            <span className="text-xs font-bold text-gray-700 block">
              {t('wealth_commitments_prompt')}
            </span>
            <div className="flex flex-wrap gap-2">
              {COMMITMENT_OPTIONS.map((chip) => {
                const selected = commitments.includes(chip.id)
                return (
                  <button
                    key={chip.id}
                    type="button"
                    onClick={() => toggleCommitment(chip.id)}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all flex items-center gap-1.5 ${
                      selected
                        ? 'bg-emerald-600 text-white border-emerald-700 shadow-xs'
                        : 'bg-white text-gray-700 border-gray-300 hover:border-emerald-400'
                    }`}
                  >
                    {selected && <CheckCircle2 className="w-3.5 h-3.5" />}
                    <span>{t(chip.labelKey)}</span>
                  </button>
                )
              })}
            </div>
            {investPlan && (
              <div className="pt-2 text-xs text-emerald-800 font-semibold">
                {t('wealth_monthly_budget_label')}:{' '}
                <span className="font-extrabold">
                  ₹{Number(investPlan.monthly_investment_budget).toLocaleString()}
                  {t('wealth_per_month')}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Allocation Cards across FD, Mutual Funds (SIP), Insurance, PPF/Gold */}
        {investLoading && !investPlan ? (
          <div className="p-6 text-center text-xs text-gray-400">{t('loading')}</div>
        ) : (
          investPlan && (
            <div className="space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-600">
                {t('wealth_allocation_split')} · {investPlan.risk_label}
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {(investPlan.allocations || []).map((alloc) => (
                  <div
                    key={alloc.key}
                    className="bg-emerald-50/40 border border-emerald-200 rounded-2xl p-4 space-y-2.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-bold text-sm text-gray-900">{alloc.category}</h4>
                        <span className="text-[11px] font-semibold text-emerald-700">
                          {alloc.expected_return_note}
                        </span>
                      </div>
                      <span className="text-sm font-extrabold px-2.5 py-1 rounded-xl bg-emerald-600 text-white">
                        {alloc.allocation_pct}%
                      </span>
                    </div>

                    <div className="flex items-baseline gap-3 text-xs">
                      <span className="font-bold text-gray-900 text-sm">
                        ₹{Number(alloc.monthly_amount).toLocaleString()}
                        {t('wealth_per_month')}
                      </span>
                      <span className="text-gray-500">
                        (₹{Number(alloc.annual_amount).toLocaleString()}
                        {t('wealth_per_year')})
                      </span>
                    </div>

                    <ul className="space-y-1">
                      {(alloc.instruments || []).map((inst, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-1.5 text-[11px] text-gray-700"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          <span>{inst}</span>
                        </li>
                      ))}
                    </ul>

                    <p className="text-[11px] text-gray-600 leading-relaxed pt-1 border-t border-emerald-100">
                      {alloc.rationale}
                    </p>
                  </div>
                ))}
              </div>

              {/* Commitment-specific Reasons */}
              {investPlan.commitment_guidance?.length > 0 && (
                <div className="space-y-2.5 pt-1">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-600">
                    {t('wealth_commitment_guidance')}
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {investPlan.commitment_guidance.map((g, i) => (
                      <div
                        key={i}
                        className="bg-gray-50 border border-gray-200 rounded-xl p-3.5 space-y-1.5"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-xs text-gray-900">{g.label}</span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                            {g.horizon}
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-600 leading-relaxed">{g.reason}</p>
                        <div className="flex flex-wrap gap-1 pt-1">
                          {(g.recommended_instruments || []).map((inst, j) => (
                            <span
                              key={j}
                              className="text-[10px] bg-white border border-gray-200 px-2 py-0.5 rounded-full font-semibold text-gray-700"
                            >
                              {inst}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        )}
      </section>

      {/* =====================================================================
          SECTION D: FUTURE RETURNS CALCULATOR
         ===================================================================== */}
      <section className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
              <Calculator className="w-5 h-5" />
            </div>
            <h2 className="text-sm sm:text-base font-bold text-gray-900">
              {t('wealth_sec_d_title')}
            </h2>
          </div>

          {/* Mode Tabs */}
          <div className="flex gap-1.5 bg-gray-100 p-1 rounded-xl">
            {[
              { id: 'sip', label: t('wealth_mode_sip') },
              { id: 'fd', label: t('wealth_mode_fd') },
              { id: 'lumpsum', label: t('wealth_mode_lumpsum') },
            ].map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => handleModeSwitch(m.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  calcMode === m.id
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {/* Inputs & Sliders */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-700">
                {calcMode === 'sip'
                  ? t('wealth_calc_monthly_amt')
                  : t('wealth_calc_principal_amt')}
              </label>
              <input
                type="number"
                min="100"
                step={calcMode === 'sip' ? 500 : 5000}
                value={calcAmount}
                onChange={(e) => setCalcAmount(Math.max(0, Number(e.target.value) || 0))}
                className="w-28 bg-white border border-gray-300 rounded-lg px-2 py-1 text-right text-xs font-bold text-gray-900"
              />
            </div>
            <input
              type="range"
              min={calcMode === 'sip' ? 500 : 10000}
              max={calcMode === 'sip' ? 100000 : 2000000}
              step={calcMode === 'sip' ? 500 : 10000}
              value={Math.min(calcMode === 'sip' ? 100000 : 2000000, calcAmount)}
              onChange={(e) => setCalcAmount(Number(e.target.value))}
              className="w-full accent-emerald-600 cursor-pointer"
            />
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-700">
                {t('wealth_calc_rate')}
              </label>
              <input
                type="number"
                min="1"
                max="30"
                step="0.1"
                value={calcRate}
                onChange={(e) => setCalcRate(Math.max(0, Number(e.target.value) || 0))}
                className="w-20 bg-white border border-gray-300 rounded-lg px-2 py-1 text-right text-xs font-bold text-gray-900"
              />
            </div>
            <input
              type="range"
              min="1"
              max="25"
              step="0.5"
              value={Math.min(25, calcRate)}
              onChange={(e) => setCalcRate(Number(e.target.value))}
              className="w-full accent-emerald-600 cursor-pointer"
            />
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-700">
                {t('wealth_calc_years')}
              </label>
              <input
                type="number"
                min="1"
                max="35"
                value={calcYears}
                onChange={(e) =>
                  setCalcYears(Math.min(35, Math.max(1, Number(e.target.value) || 1)))
                }
                className="w-20 bg-white border border-gray-300 rounded-lg px-2 py-1 text-right text-xs font-bold text-gray-900"
              />
            </div>
            <input
              type="range"
              min="1"
              max="30"
              step="1"
              value={Math.min(30, calcYears)}
              onChange={(e) => setCalcYears(Number(e.target.value))}
              className="w-full accent-emerald-600 cursor-pointer"
            />
          </div>
        </div>

        {/* Live Result Cards & Recharts Breakdown */}
        {calcResult && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-gray-50 border border-gray-200 rounded-2xl p-4">
                <span className="text-[11px] font-bold uppercase text-gray-500">
                  {t('wealth_total_invested')}
                </span>
                <div className="text-xl font-bold text-gray-900 mt-1">
                  ₹{Number(calcResult.total_invested).toLocaleString()}
                </div>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4">
                <span className="text-[11px] font-bold uppercase text-emerald-700">
                  {t('wealth_est_returns')}
                </span>
                <div className="text-xl font-bold text-emerald-700 mt-1">
                  +₹{Number(calcResult.estimated_returns).toLocaleString()}
                </div>
              </div>
              <div className="bg-gradient-to-br from-emerald-600 to-green-700 text-white rounded-2xl p-4 shadow-sm">
                <span className="text-[11px] font-bold uppercase text-emerald-100">
                  {t('wealth_maturity_value')}
                </span>
                <div className="text-2xl font-extrabold mt-1">
                  ₹{Number(calcResult.maturity_value).toLocaleString()}
                </div>
              </div>
            </div>

            <div className="bg-gray-50/70 border border-gray-200 rounded-2xl p-4 space-y-2">
              <h3 className="text-xs font-bold text-gray-700">
                {t('wealth_growth_chart_title')}
              </h3>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={(calcResult.yearly_breakdown || []).map((row) => ({
                      ...row,
                      label: `${t('wealth_yr_short')} ${row.year}`,
                    }))}
                    margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickFormatter={(val) =>
                        val >= 100000
                          ? `₹${(val / 100000).toFixed(1)}L`
                          : `₹${Math.round(val / 1000)}k`
                      }
                    />
                    <Tooltip
                      formatter={(val) => [`₹${Number(val).toLocaleString()}`, '']}
                      contentStyle={{ borderRadius: '12px', fontSize: '12px' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    <Bar
                      dataKey="invested"
                      name={t('wealth_total_invested')}
                      fill="#94A3B8"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="value"
                      name={t('wealth_maturity_value')}
                      fill="#059669"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}
      </section>

      {/* =====================================================================
          MODAL: + ADD MY LOAN
         ===================================================================== */}
      {showAddLoanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-2">
              <h3 className="font-bold text-gray-900 text-base">
                {t('wealth_add_loan_modal_title')}
              </h3>
              <button
                type="button"
                onClick={() => setShowAddLoanModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddLoanSubmit} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-gray-700 block mb-1">
                  {t('wealth_lender_name')}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Local Cooperative / SBI Agri"
                  value={newLoan.lender_name}
                  onChange={(e) => setNewLoan({ ...newLoan, lender_name: e.target.value })}
                  className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-gray-700 block mb-1">
                    {t('wealth_loan_type')}
                  </label>
                  <select
                    value={newLoan.loan_type}
                    onChange={(e) => setNewLoan({ ...newLoan, loan_type: e.target.value })}
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl font-semibold"
                  >
                    <option value="Informal/Moneylender">Informal / Moneylender</option>
                    <option value="NBFC Tractor Loan">NBFC Tractor Loan</option>
                    <option value="KCC Crop Loan">KCC Crop Loan</option>
                    <option value="Gold Loan">Gold Loan</option>
                    <option value="SHG / Microfinance">SHG / Microfinance</option>
                  </select>
                </div>
                <div>
                  <label className="font-bold text-gray-700 block mb-1">
                    {t('wealth_interest_rate')}
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    required
                    value={newLoan.interest_rate_annual}
                    onChange={(e) =>
                      setNewLoan({ ...newLoan, interest_rate_annual: e.target.value })
                    }
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-gray-700 block mb-1">
                    {t('wealth_principal')}
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={newLoan.principal_amount}
                    onChange={(e) =>
                      setNewLoan({ ...newLoan, principal_amount: e.target.value })
                    }
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl font-bold"
                  />
                </div>
                <div>
                  <label className="font-bold text-gray-700 block mb-1">
                    {t('wealth_outstanding')}
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={newLoan.outstanding_balance}
                    onChange={(e) =>
                      setNewLoan({ ...newLoan, outstanding_balance: e.target.value })
                    }
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-gray-700 block mb-1">
                    {t('wealth_emi_amount')}
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={newLoan.emi_amount}
                    onChange={(e) => setNewLoan({ ...newLoan, emi_amount: e.target.value })}
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl"
                  />
                </div>
                <div>
                  <label className="font-bold text-gray-700 block mb-1">
                    {t('wealth_next_due_date')}
                  </label>
                  <input
                    type="date"
                    required
                    value={newLoan.next_due_date}
                    onChange={(e) => setNewLoan({ ...newLoan, next_due_date: e.target.value })}
                    className="w-full p-2 bg-gray-50 border border-gray-300 rounded-xl"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddLoanModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-xl text-gray-700 font-semibold"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  disabled={addingLoan}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition-colors"
                >
                  {addingLoan ? t('saving') : t('wealth_save_loan')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
