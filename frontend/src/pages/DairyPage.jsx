import React, { useState, useEffect } from 'react'
import {
  Beef,
  Droplet,
  HeartPulse,
  Sparkles,
  GitMerge,
  ShieldAlert,
  HelpCircle,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  Info,
  Calendar,
  Layers,
  Thermometer,
  Wind,
  PhoneCall,
  Volume2,
  Plus,
  X,
  Search,
  MapPin,
  Clock,
  User,
  Tag,
  ShoppingBag,
  Stethoscope
} from 'lucide-react'
import { dairyApi, weatherApi } from '../api/client'
import { useI18n } from '../context/I18nContext'
import { useLocationContext } from '../context/LocationContext'

const CATTLE_BREED_OPTIONS = [
  'Hallikar',
  'Malnad Gidda',
  'HF Cross',
  'Jersey',
  'Gir',
  'Murrah Buffalo',
]

const CATTLE_ANIMAL_TYPES = ['Cow', 'Buffalo', 'Heifer', 'Calf']

export default function DairyPage({ onAskVoice }) {
  const { t, lang } = useI18n()
  const { location } = useLocationContext()
  const activeState = location?.state || 'Karnataka'
  const activeDistrict = location?.district || location?.name || 'Bengaluru'
  const activeLocationName = location?.location_name || location?.name || activeDistrict
  const activeLat = location?.lat ?? 12.9716
  const activeLon = location?.lon ?? 77.5946
  const locParams = {
    state: activeState,
    district: activeDistrict,
    location_name: activeLocationName,
    lat: activeLat,
    lon: activeLon,
    language: lang,
  }

  const [activeSubTab, setActiveSubTab] = useState('rates') // 'rates', 'breeds', 'feed', 'sire', 'disease', 'cattle'
  const [advisory, setAdvisory] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({
      state: activeState,
      district: activeDistrict,
      location_name: activeLocationName,
      language: lang,
    })
    fetch(`/api/dairy/advisory?${params.toString()}`, { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setAdvisory(data)
      })
      .catch(() => {})
    return () => controller.abort()
  }, [activeState, activeDistrict, activeLocationName, lang])
  
  // Rate board state
  const [rates, setRates] = useState([])
  const [ratesLoading, setRatesLoading] = useState(true)
  const [milkFilter, setMilkFilter] = useState('All') // 'All', 'Cow', 'Buffalo'
  const [calcMilkType, setCalcMilkType] = useState('Cow')
  const [calcFat, setCalcFat] = useState(3.8)
  const [calcSnf, setCalcSnf] = useState(8.5)
  const [calcQty, setCalcQty] = useState(15.0)
  const [calcResult, setCalcResult] = useState(null)
  const [calcLoading, setCalcLoading] = useState(false)

  // Breeds state
  const [breeds, setBreeds] = useState([])
  const [breedsLoading, setBreedsLoading] = useState(false)
  const [breedAnimalFilter, setBreedAnimalFilter] = useState('All')
  const [ambientTemp, setAmbientTemp] = useState(27.0)

  // Feed planner state
  const [feedPlans, setFeedPlans] = useState([])
  const [feedLoading, setFeedLoading] = useState(false)
  const [feedStageFilter, setFeedStageFilter] = useState('All') // 'All', 'Dry', 'Lactating'
  const [feedAnimalFilter, setFeedAnimalFilter] = useState('All')

  // Sire semen guide state
  const [sireGuides, setSireGuides] = useState([])
  const [sireLoading, setSireLoading] = useState(false)
  const [selectedDamBreed, setSelectedDamBreed] = useState('')

  // Disease advisor state
  const [diseases, setDiseases] = useState([])
  const [diseaseLoading, setDiseaseLoading] = useState(false)
  const [symptomSearch, setSymptomSearch] = useState('')
  const [selectedSymptomKey, setSelectedSymptomKey] = useState('')

  // Livestock Health toggle & Cow/Vet Doctors state
  const [healthView, setHealthView] = useState('symptoms') // 'symptoms' | 'doctors'
  const [doctors, setDoctors] = useState([])
  const [doctorsLoading, setDoctorsLoading] = useState(false)
  const [doctorTypeFilter, setDoctorTypeFilter] = useState('All')
  const [doctorSearch, setDoctorSearch] = useState('')
  const [isDoctorModalOpen, setIsDoctorModalOpen] = useState(false)
  const [doctorSaving, setDoctorSaving] = useState(false)
  const [doctorError, setDoctorError] = useState('')
  const [doctorForm, setDoctorForm] = useState({
    name: '',
    doctor_type: 'Local Cow Doctor',
    specialization: '',
    phone: '',
    location: '',
    availability: '',
    emergency_available: false,
  })

  // Cattle Market state
  const [cattleListings, setCattleListings] = useState([])
  const [cattleLoading, setCattleLoading] = useState(false)
  const [cattleBreedFilter, setCattleBreedFilter] = useState('All')
  const [cattleMinPrice, setCattleMinPrice] = useState('')
  const [cattleMaxPrice, setCattleMaxPrice] = useState('')
  const [cattleSortBy, setCattleSortBy] = useState('newest')
  const [isCattleModalOpen, setIsCattleModalOpen] = useState(false)
  const [cattleSaving, setCattleSaving] = useState(false)
  const [cattleError, setCattleError] = useState('')
  const [cattleForm, setCattleForm] = useState({
    title: '',
    breed: 'HF Cross',
    animal_type: 'Cow',
    price_inr: '',
    milk_yield_liters_per_day: '',
    age_years: '',
    location: '',
    owner_name: '',
    owner_phone: '',
    description: '',
  })

  // Auto-sync live temperature for the selected location
  useEffect(() => {
    weatherApi.getForecast(activeLat, activeLon, activeLocationName, activeState, lang)
      .then(res => {
        const liveTemp = res.data?.current?.temperature_2m ?? res.data?.current_weather?.temperature
        if (typeof liveTemp === 'number' && !Number.isNaN(liveTemp)) {
          setAmbientTemp(Number(liveTemp.toFixed(1)))
        }
      })
      .catch(() => {})
  }, [activeState, activeDistrict, activeLocationName, activeLat, activeLon, lang])

  // Load procurement rates on mount and when location/language/filter changes
  useEffect(() => {
    fetchRates()
  }, [milkFilter, activeState, activeDistrict, activeLocationName, activeLat, activeLon, lang])

  const fetchRates = () => {
    setRatesLoading(true)
    const filterParam = milkFilter === 'All' ? null : milkFilter
    dairyApi.getProcurementRates(filterParam, locParams)
      .then(res => {
        setRates(res.data)
        setRatesLoading(false)
      })
      .catch(() => setRatesLoading(false))
  }

  // Load breeds when subtab opens or ambientTemp/animal filter/location/language changes
  useEffect(() => {
    if (activeSubTab === 'breeds') {
      setBreedsLoading(true)
      const aFilter = breedAnimalFilter === 'All' ? null : breedAnimalFilter
      dairyApi.getBreeds(ambientTemp, aFilter, locParams)
        .then(res => {
          setBreeds(res.data)
          setBreedsLoading(false)
        })
        .catch(() => setBreedsLoading(false))
    }
  }, [activeSubTab, breedAnimalFilter, ambientTemp, activeState, activeDistrict, activeLocationName, activeLat, activeLon, lang])

  // Load feed plans
  useEffect(() => {
    if (activeSubTab === 'feed') {
      setFeedLoading(true)
      const sFilter = feedStageFilter === 'All' ? null : feedStageFilter
      const aFilter = feedAnimalFilter === 'All' ? null : feedAnimalFilter
      dairyApi.getFeedPlans(aFilter, sFilter, locParams)
        .then(res => {
          setFeedPlans(res.data)
          setFeedLoading(false)
        })
        .catch(() => setFeedLoading(false))
    }
  }, [activeSubTab, feedStageFilter, feedAnimalFilter, activeState, activeDistrict, activeLocationName, activeLat, activeLon, lang])

  // Load sire guide
  useEffect(() => {
    if (activeSubTab === 'sire') {
      setSireLoading(true)
      dairyApi.getBreedingGuide(selectedDamBreed || null, locParams)
        .then(res => {
          setSireGuides(res.data)
          setSireLoading(false)
        })
        .catch(() => setSireLoading(false))
    }
  }, [activeSubTab, selectedDamBreed, activeState, activeDistrict, activeLocationName, activeLat, activeLon, lang])

  // Load disease advisor
  useEffect(() => {
    if (activeSubTab === 'disease' && healthView === 'symptoms') {
      setDiseaseLoading(true)
      dairyApi.getDiseaseAdvisor(symptomSearch || null, locParams)
        .then(res => {
          setDiseases(res.data)
          setDiseaseLoading(false)
        })
        .catch(() => setDiseaseLoading(false))
    }
  }, [activeSubTab, healthView, symptomSearch, activeState, activeDistrict, activeLocationName, activeLat, activeLon, lang])

  // Load Cow & Vet Doctors
  const fetchDoctors = () => {
    setDoctorsLoading(true)
    const dt = doctorTypeFilter === 'All' ? null : doctorTypeFilter
    dairyApi.getDoctors(dt, doctorSearch.trim() || null)
      .then(res => {
        setDoctors(res.data || [])
        setDoctorsLoading(false)
      })
      .catch(() => setDoctorsLoading(false))
  }

  useEffect(() => {
    if (activeSubTab === 'disease' && healthView === 'doctors') {
      fetchDoctors()
    }
  }, [activeSubTab, healthView, doctorTypeFilter, doctorSearch])

  // Load Cattle Market listings
  const fetchCattle = () => {
    setCattleLoading(true)
    dairyApi.getCattle({
      state: activeState,
      district: activeDistrict,
      location_name: activeLocationName,
      breed: cattleBreedFilter === 'All' ? null : cattleBreedFilter,
      min_price: cattleMinPrice,
      max_price: cattleMaxPrice,
      sort_by: cattleSortBy,
    })
      .then(res => {
        setCattleListings(res.data || [])
        setCattleLoading(false)
      })
      .catch(() => setCattleLoading(false))
  }

  useEffect(() => {
    if (activeSubTab === 'cattle') {
      fetchCattle()
    }
  }, [activeSubTab, activeState, activeDistrict, activeLocationName, cattleBreedFilter, cattleMinPrice, cattleMaxPrice, cattleSortBy])

  const handleCreateDoctor = (e) => {
    e.preventDefault()
    setDoctorSaving(true)
    setDoctorError('')
    dairyApi.createDoctor({
      ...doctorForm,
      specialization: doctorForm.specialization || null,
      availability: doctorForm.availability || null,
    })
      .then(() => {
        setIsDoctorModalOpen(false)
        setDoctorForm({
          name: '',
          doctor_type: 'Local Cow Doctor',
          specialization: '',
          phone: '',
          location: '',
          availability: '',
          emergency_available: false,
        })
        fetchDoctors()
      })
      .catch(err => setDoctorError(err?.response?.data?.detail || 'Failed to add doctor'))
      .finally(() => setDoctorSaving(false))
  }

  const handleCreateCattle = (e) => {
    e.preventDefault()
    setCattleSaving(true)
    setCattleError('')
    dairyApi.createCattle({
      title: cattleForm.title,
      breed: cattleForm.breed,
      animal_type: cattleForm.animal_type,
      price_inr: parseFloat(cattleForm.price_inr || '0'),
      milk_yield_liters_per_day: parseFloat(cattleForm.milk_yield_liters_per_day || '0'),
      age_years: parseFloat(cattleForm.age_years || '0'),
      location: cattleForm.location?.trim()
        ? (cattleForm.location.toLowerCase().includes(activeState.toLowerCase())
            ? cattleForm.location.trim()
            : `${cattleForm.location.trim()}, ${activeState}`)
        : `${activeLocationName}, ${activeState}`,
      owner_name: cattleForm.owner_name,
      owner_phone: cattleForm.owner_phone,
      description: cattleForm.description || null,
    })
      .then(() => {
        setIsCattleModalOpen(false)
        setCattleForm({
          title: '',
          breed: 'HF Cross',
          animal_type: 'Cow',
          price_inr: '',
          milk_yield_liters_per_day: '',
          age_years: '',
          location: '',
          owner_name: '',
          owner_phone: '',
          description: '',
        })
        fetchCattle()
      })
      .catch(err => setCattleError(err?.response?.data?.detail || 'Failed to post cattle listing'))
      .finally(() => setCattleSaving(false))
  }

  // Milk payout calculation
  const handleCalculatePayout = (e) => {
    e.preventDefault()
    setCalcLoading(true)
    dairyApi.calculatePayout({
      milk_type: calcMilkType,
      fat_pct: parseFloat(calcFat),
      snf_pct: parseFloat(calcSnf),
      quantity_litres: parseFloat(calcQty)
    })
      .then(res => {
        setCalcResult(res.data)
        setCalcLoading(false)
      })
      .catch(() => setCalcLoading(false))
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
          <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700">
            <Beef className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-gray-800">
              {advisory?.title || `Animal Husbandry & Dairy Advisory — ${activeLocationName}, ${activeState}`}
            </h1>
            <p className="text-xs text-gray-500">
              {advisory?.subtitle || `${lang === 'kn' ? 'ಹೈನುಗಾರಿಕೆ ಮಾಹಿತಿ ಕೇಂದ್ರ · ' : ''}Milk Rates, Breed Matching, Nutrition, Sire Selection & Vet Advisor`}
            </p>
            <p className="text-[11px] font-medium text-amber-700 mt-0.5">
              {`Showing Dairy Advisory for ${activeLocationName},${activeState}`}
            </p>
          </div>
        </div>
      </div>

      {/* SUB-TABS NAVIGATION */}
      <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar border-b border-gray-200">
        {[
          { id: 'rates', label: 'Milk Rate Board', labelKn: 'ಹಾಲು ದರ ಪಟ್ಟಿ', icon: Droplet },
          { id: 'breeds', label: 'Climate Breeds', labelKn: 'ತಳಿ ಆಯ್ಕೆ', icon: Sparkles },
          { id: 'feed', label: 'Feed & Nutrition', labelKn: 'ಮೇವು ಮತ್ತು ಪೋಷಣೆ', icon: Layers },
          { id: 'sire', label: 'Sire Semen Guide', labelKn: 'ವೀರ್ಯ ತಳಿ ಮಾರ್ಗದರ್ಶಿ', icon: GitMerge },
          { id: 'disease', label: 'Livestock Health', labelKn: 'ಆರೋಗ್ಯ & ಪ್ರಥಮ ಚಿಕಿತ್ಸೆ', icon: HeartPulse },
          { id: 'cattle', label: t('cattle_market', 'Cattle Market'), labelKn: t('cattle_market_sub', 'ಜಾನುವಾರು ಮಾರುಕಟ್ಟೆ'), icon: ShoppingBag },
        ].map((tab) => {
          const Icon = tab.icon
          const isActive = activeSubTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`flex-shrink-0 flex items-center gap-2 px-3.5 py-2.5 rounded-t-xl text-xs sm:text-sm font-semibold transition-all border-b-2 ${
                isActive
                  ? 'border-amber-600 text-amber-800 bg-amber-50/70'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-amber-600' : 'text-gray-400'}`} />
              <div className="text-left">
                <div>{tab.label}</div>
                {lang === 'kn' && tab.labelKn && (
                  <div className="text-[10px] font-normal text-gray-400">{tab.labelKn}</div>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {/* 1. MILK RATE BOARD SUBSECTION */}
      {activeSubTab === 'rates' && (
        <div className="space-y-5">
          {/* State Cooperative & Incentive Banner */}
          <div className="bg-gradient-to-r from-amber-500 to-orange-600 text-white rounded-2xl p-4 shadow-md flex items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="bg-white/20 text-white text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                  {activeState} Dairy Cooperative
                </span>
                {lang === 'kn' && activeState === 'Karnataka' && (
                  <span className="text-xs text-amber-100 font-medium">ಕ್ಷೀರ ಧಾರೆ ಯೋಜನೆ</span>
                )}
              </div>
              <h2 className="text-base sm:text-lg font-bold mt-1">
                {activeState === 'Karnataka'
                  ? 'KMF Nandini Standard Payout: ₹42/L Base + ₹5/L State Incentive = ₹47.00/L'
                  : `${activeState} Regional Procurement Benchmark (${rates[0]?.dairy_name || 'State Cooperative'})`}
              </h2>
              <p className="text-xs text-amber-100 mt-0.5">
                {activeState === 'Karnataka'
                  ? 'Eligible registered dairy farmers receive ₹5.00/L direct benefit transfer directly to their bank accounts.'
                  : `LiveFat/SNF procurement comparison for ${activeLocationName}, ${activeState}.`}
              </p>
            </div>
          </div>

          {/* Rate comparison table controls */}
          <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-gray-800 text-sm sm:text-base flex items-center gap-2">
                  <Droplet className="w-4 h-4 text-blue-500" />
                  Major Dairies Procurement Rate Board ({activeState})
                </h3>
                <p className="text-xs text-gray-500">
                  Current procurement prices across major cooperatives and private dairies in {activeState}
                </p>
              </div>
              <div className="flex gap-1.5 bg-gray-100 p-1 rounded-xl">
                {['All', 'Cow', 'Buffalo'].map(type => (
                  <button
                    key={type}
                    onClick={() => setMilkFilter(type)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                      milkFilter === type
                        ? 'bg-white text-gray-800 shadow-sm'
                        : 'text-gray-500 hover:text-gray-800'
                    }`}
                  >
                    {type} Milk
                  </button>
                ))}
              </div>
            </div>

            {/* Table */}
            {ratesLoading ? (
              <div className="p-8 text-center text-gray-400">Loading procurement rates…</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs sm:text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-gray-600 font-semibold border-b border-gray-200">
                      <th className="py-2.5 px-3">Dairy & Brand</th>
                      <th className="py-2.5 px-3">Type & Quality Slab</th>
                      <th className="py-2.5 px-3 text-right">Base Fat / SNF</th>
                      <th className="py-2.5 px-3 text-right">Dairy Base</th>
                      <th className="py-2.5 px-3 text-right text-emerald-600">Govt Incentive</th>
                      <th className="py-2.5 px-3 text-right font-bold text-gray-900">Total Payout</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {rates.map(r => (
                      <tr key={r.id} className="hover:bg-amber-50/50 transition-colors">
                        <td className="py-3 px-3 font-semibold text-gray-800">
                          <div className="flex items-center gap-2">
                            <span className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-600">
                              {r.brand_logo || '🥛'}
                            </span>
                            <div>
                              <div>{r.dairy_name}</div>
                              <div className="text-[10px] text-gray-400 font-normal">{r.notes}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
                            r.milk_type === 'Cow' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                          }`}>
                            {r.slab_name || `${r.milk_type} Standard`}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right text-gray-600">
                          {r.base_fat_pct}% / {r.base_snf_pct}%
                        </td>
                        <td className="py-3 px-3 text-right text-gray-700">
                          ₹{r.base_rate_per_litre.toFixed(2)}
                        </td>
                        <td className="py-3 px-3 text-right font-semibold text-emerald-600">
                          {r.govt_incentive > 0 ? `+₹${r.govt_incentive.toFixed(2)}` : '—'}
                        </td>
                        <td className="py-3 px-3 text-right font-bold text-base text-gray-900">
                          ₹{r.total_effective_rate.toFixed(2)}/L
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Interactive Milk Payout Calculator */}
          <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                ₹
              </div>
              <div>
                <h3 className="font-bold text-gray-800 text-sm sm:text-base">
                  Daily Milk Payout Calculator (ಹಾಲಿನ ಆದಾಯ ಲೆಕ್ಕಾಚಾರ)
                </h3>
                <p className="text-xs text-gray-500">
                  Enter your tested Fat % and SNF % to see exact expected earnings per liter across all dairies.
                </p>
              </div>
            </div>

            <form onSubmit={handleCalculatePayout} className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50 p-3 rounded-xl border border-gray-100">
              <div>
                <label className="text-[11px] font-bold text-gray-600 block mb-1">Animal Type</label>
                <select
                  value={calcMilkType}
                  onChange={(e) => setCalcMilkType(e.target.value)}
                  className="w-full text-xs font-semibold bg-white border border-gray-200 rounded-lg p-2 focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="Cow">Cow (ಹಸು)</option>
                  <option value="Buffalo">Buffalo (ಎಮ್ಮೆ)</option>
                </select>
              </div>
              <div>
                <label className="text-[11px] font-bold text-gray-600 block mb-1">Fat % (ಕೊಬ್ಬಿನಾಂಶ)</label>
                <input
                  type="number"
                  step="0.1"
                  min="2.5"
                  max="12.0"
                  value={calcFat}
                  onChange={(e) => setCalcFat(e.target.value)}
                  className="w-full text-xs font-semibold bg-white border border-gray-200 rounded-lg p-2 focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-bold text-gray-600 block mb-1">SNF % (ಘನಾಂಶ)</label>
                <input
                  type="number"
                  step="0.1"
                  min="7.0"
                  max="11.0"
                  value={calcSnf}
                  onChange={(e) => setCalcSnf(e.target.value)}
                  className="w-full text-xs font-semibold bg-white border border-gray-200 rounded-lg p-2 focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-bold text-gray-600 block mb-1">Daily Litres (ಪ್ರಮಾಣ)</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    max="1000"
                    value={calcQty}
                    onChange={(e) => setCalcQty(e.target.value)}
                    className="w-full text-xs font-semibold bg-white border border-gray-200 rounded-lg p-2 focus:ring-2 focus:ring-emerald-500"
                  />
                  <button
                    type="submit"
                    disabled={calcLoading}
                    className="px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors"
                  >
                    {calcLoading ? '…' : 'Calculate'}
                  </button>
                </div>
              </div>
            </form>

            {calcResult && (
              <div className="space-y-3">
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs flex items-center justify-between">
                  <span className="text-emerald-900 font-medium">
                    Highest Paying Dairy for {calcMilkType} ({calcFat}% Fat, {calcSnf}% SNF):
                  </span>
                  <span className="font-bold text-emerald-800 text-sm">
                    🏆 {calcResult.best_dairy} (₹{calcResult.max_payout.toLocaleString()} for {calcQty}L)
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {calcResult.results.map((r, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-xl border transition-all ${
                        r.is_highest
                          ? 'bg-amber-50/80 border-amber-300 shadow-sm ring-1 ring-amber-300'
                          : 'bg-white border-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-gray-800 text-xs sm:text-sm">{r.dairy_name}</span>
                        <span className="font-bold text-base text-emerald-700">₹{r.rate_per_litre}/L</span>
                      </div>
                      <div className="text-[11px] text-gray-500 mt-1 flex justify-between">
                        <span>Base: ₹{r.base_rate} · Fat/SNF diff: {r.fat_adjustment + r.snf_adjustment >= 0 ? '+' : ''}{(r.fat_adjustment + r.snf_adjustment).toFixed(2)}</span>
                        <span className="font-semibold text-gray-700">Total: ₹{r.total_payout.toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. WEATHER-MATCHED HIGH-YIELD BREEDS SUBSECTION */}
      {activeSubTab === 'breeds' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-gray-800 text-sm sm:text-base flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-500" />
                Weather-Matched High-Yield Cow & Buffalo Breeds
              </h3>
              <p className="text-xs text-gray-500">
                Climate-tailored breed profiles including HF Cross, Jersey Cross, Gir, Hallikar, Malnad Gidda, Murrah & Jaffarabadi
              </p>
            </div>
            
            {/* Ambient temperature simulation slider */}
            <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-xl">
              <Thermometer className="w-4 h-4 text-red-500" />
              <span className="text-xs font-medium text-gray-600">Simulate Temp:</span>
              <input
                type="range"
                min="18"
                max="42"
                value={ambientTemp}
                onChange={(e) => setAmbientTemp(parseFloat(e.target.value))}
                className="w-24 accent-amber-600"
              />
              <span className="text-xs font-bold text-gray-800">{ambientTemp}°C</span>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex gap-2">
            {['All', 'Cow', 'Buffalo'].map(type => (
              <button
                key={type}
                onClick={() => setBreedAnimalFilter(type)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                  breedAnimalFilter === type
                    ? 'bg-amber-700 text-white border-amber-800'
                    : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                }`}
              >
                {type} Breeds
              </button>
            ))}
          </div>

          {/* Breeds List */}
          {breedsLoading ? (
            <div className="p-12 text-center text-gray-400">Loading weather-matched breed profiles…</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {breeds.map(b => {
                const isOptimal = b.weather_match.suitability_score === 'high'
                const isLow = b.weather_match.suitability_score === 'low'
                return (
                  <div
                    key={b.id}
                    className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
                  >
                    <div>
                      {/* Climate Match Badge */}
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                          isOptimal
                            ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                            : isLow
                            ? 'bg-rose-100 text-rose-800 border-rose-200'
                            : 'bg-amber-100 text-amber-800 border-amber-200'
                        }`}>
                          {b.weather_match.suitability}
                        </span>
                        <span className="text-xs text-gray-400">{b.origin}</span>
                      </div>

                      <h4 className="font-bold text-gray-900 text-base">
                        {b.breed_name}
                      </h4>
                      <p className="text-xs font-medium text-amber-900 mb-2">
                        {b.breed_kannada}
                      </p>

                      {/* Yield & Fat Metrics */}
                      <div className="grid grid-cols-3 gap-2 bg-gray-50 p-2.5 rounded-xl text-center mb-3">
                        <div>
                          <div className="text-[10px] text-gray-500 uppercase font-semibold">Avg Yield</div>
                          <div className="text-xs font-bold text-gray-800">{b.avg_yield_litres} L/day</div>
                        </div>
                        <div>
                          <div className="text-[10px] text-gray-500 uppercase font-semibold">Peak Yield</div>
                          <div className="text-xs font-bold text-emerald-700">{b.peak_yield_litres} L/day</div>
                        </div>
                        <div>
                          <div className="text-[10px] text-gray-500 uppercase font-semibold">Fat %</div>
                          <div className="text-xs font-bold text-amber-800">{b.fat_pct}%</div>
                        </div>
                      </div>

                      <p className="text-xs text-gray-600 leading-relaxed mb-3">
                        {b.description}
                      </p>

                      {/* Climate and care tip */}
                      <div className="p-2.5 bg-amber-50/60 rounded-xl border border-amber-100 text-xs text-amber-950 space-y-1">
                        <div className="font-semibold flex items-center gap-1.5">
                          <Wind className="w-3.5 h-3.5 text-amber-700" />
                          Climate Care at {b.weather_match.current_temp}°C:
                        </div>
                        <p className="text-[11px] text-amber-900">{b.weather_match.cooling_advice}</p>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
                      <span className="text-gray-500">Resistance: <strong className="text-gray-700">{b.disease_resistance}</strong></span>
                      <button
                        onClick={() => triggerVoiceWithPrompt(`${b.breed_name} ಹಸು/ಎಮ್ಮೆ ಸಾಕಣೆ ಬಗ್ಗೆ ಮತ್ತು ರೋಗ ತಡೆಗಟ್ಟುವಿಕೆ ತಿಳಿಸಿ`)}
                        className="text-amber-700 font-semibold hover:underline flex items-center gap-1"
                      >
                        Ask Voice Advisor <Volume2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* 3. TARGETED FEED & NUTRITION PLANNER SUBSECTION */}
      {activeSubTab === 'feed' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-gray-800 text-sm sm:text-base flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-600" />
                Targeted Feed & Nutrition Planner (ಮೇವು ಮತ್ತು ಪೋಷಣೆ ಯೋಜನೆ)
              </h3>
              <p className="text-xs text-gray-500">
                Dedicated daily rations for (a) Unfertilized / Dry Cows & Buffaloes and (b) High-Yield Lactating Cattle
              </p>
            </div>

            <div className="flex gap-2">
              <select
                value={feedAnimalFilter}
                onChange={(e) => setFeedAnimalFilter(e.target.value)}
                className="text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-2.5 py-1.5"
              >
                <option value="All">All Cattle</option>
                <option value="Cow">Cows (ಹಸುಗಳು)</option>
                <option value="Buffalo">Buffaloes (ಎಮ್ಮೆಗಳು)</option>
              </select>

              <select
                value={feedStageFilter}
                onChange={(e) => setFeedStageFilter(e.target.value)}
                className="text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-2.5 py-1.5"
              >
                <option value="All">All Stages</option>
                <option value="Dry">Dry / Unfertilized</option>
                <option value="Lactating">High-Yield Lactating</option>
              </select>
            </div>
          </div>

          {feedLoading ? (
            <div className="p-12 text-center text-gray-400">Loading daily feed rations…</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {feedPlans.map(plan => (
                <div
                  key={plan.id}
                  className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm hover:border-emerald-300 transition-colors flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                        plan.stage === 'Lactating'
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-amber-100 text-amber-800 border-amber-200'
                      }`}>
                        {plan.stage === 'Lactating' ? '🍼 High-Yield Lactating' : '🌾 Dry / Unfertilized Preparation'}
                      </span>
                      <span className="text-xs font-bold text-gray-700">
                        Body Wt: ~{plan.body_weight_kg} kg
                      </span>
                    </div>

                    <h4 className="font-bold text-gray-900 text-base">
                      {plan.plan_title || `${plan.animal_type} Daily Nutrition Ration`}
                    </h4>
                    {plan.plan_title_kannada && (
                      <p className="text-xs font-semibold text-emerald-900 mb-3">
                        {plan.plan_title_kannada}
                      </p>
                    )}

                    {/* Breakdown table */}
                    <div className="bg-gray-50 rounded-xl p-3 space-y-2 border border-gray-100 text-xs">
                      <div className="flex justify-between items-center py-1 border-b border-gray-200/60">
                        <span className="text-gray-600">🌿 Green Fodder (ಹಸಿರು ಮೇವು):</span>
                        <strong className="text-gray-900">{plan.green_fodder_kg} kg / day</strong>
                      </div>
                      <div className="flex justify-between items-center py-1 border-b border-gray-200/60">
                        <span className="text-gray-600">🌾 Dry Fodder / Straw (ಒಣ ಮೇವು):</span>
                        <strong className="text-gray-900">{plan.dry_fodder_kg} kg / day</strong>
                      </div>
                      <div className="flex justify-between items-center py-1 border-b border-gray-200/60">
                        <span className="text-gray-600">🥣 Cattle Feed Concentrate (ಹಿಂಡಿ/ಬೂಸ):</span>
                        <strong className="text-emerald-700 font-bold">{plan.concentrate_kg} kg / day</strong>
                      </div>
                      <div className="flex justify-between items-center py-1 border-b border-gray-200/60">
                        <span className="text-gray-600">🧪 Mineral Mixture (ಖನಿಜ ಮಿಶ್ರಣ):</span>
                        <strong className="text-gray-900">{plan.mineral_mixture_g} grams / day</strong>
                      </div>
                      {plan.bypass_fat_g > 0 && (
                        <div className="flex justify-between items-center py-1 border-b border-gray-200/60">
                          <span className="text-gray-600">🧈 Bypass Fat (ಬೈಪಾಸ್ ಕೊಬ್ಬು):</span>
                          <strong className="text-amber-800 font-bold">{plan.bypass_fat_g} g / day</strong>
                        </div>
                      )}
                      <div className="flex justify-between items-center py-1">
                        <span className="text-gray-600">💧 Clean Drinking Water:</span>
                        <strong className="text-blue-700">{plan.water_litres} Litres / day</strong>
                      </div>
                    </div>

                    {/* Practical tip */}
                    <div className="mt-3 p-3 bg-emerald-50 rounded-xl border border-emerald-100 text-xs text-emerald-950">
                      <p className="font-semibold text-emerald-900 mb-1">Feeding Routine & Schedule:</p>
                      <p className="text-[11px] leading-relaxed">{plan.schedule_tips}</p>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
                    <span className="text-gray-400">Target: {plan.target_yield_litres > 0 ? `${plan.target_yield_litres}L Milk/day` : 'Fertility Preparation'}</span>
                    <button
                      onClick={() => triggerVoiceWithPrompt(`${plan.animal_type} ${plan.stage} ಹಂತದ ಮೇವಿನ ವೇಳಾಪಟ್ಟಿ ಮತ್ತು ಖನಿಜ ಮಿಶ್ರಣ ಮಾಹಿತಿ ನೀಡಿ`)}
                      className="text-emerald-700 font-semibold hover:underline flex items-center gap-1"
                    >
                      Ask Voice Assistant <Volume2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 4. SIRE / BULL SEMEN MATCHING GUIDE SUBSECTION */}
      {activeSubTab === 'sire' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-4">
            <div>
              <h3 className="font-bold text-gray-800 text-sm sm:text-base flex items-center gap-2">
                <GitMerge className="w-4 h-4 text-purple-600" />
                Sire / Bull Semen Matching Guide (ಕೃತಕ ಗರ್ಭಧಾರಣೆ & ಹೋರಿ ತಳಿ ಆಯ್ಕೆ)
              </h3>
              <p className="text-xs text-gray-500">
                Select your mother cow or buffalo breed to discover the optimal bull semen match for high milk yields and disease resistance.
              </p>
            </div>

            {/* Dam Breed Dropdown Selector */}
            <div className="max-w-md">
              <label className="text-xs font-bold text-gray-700 block mb-1.5">
                Select Dam (Mother) Breed / ತಾಯಿ ಹಸು/ಎಮ್ಮೆ ತಳಿ:
              </label>
              <select
                value={selectedDamBreed}
                onChange={(e) => setSelectedDamBreed(e.target.value)}
                className="w-full text-xs sm:text-sm font-semibold bg-gray-50 border border-gray-300 rounded-xl p-2.5 focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All Breeds (ಎಲ್ಲಾ ತಳಿಗಳು)</option>
                <option value="Holstein Friesian Cross">Holstein Friesian Cross (HF ಕ್ರಾಸ್ ಹಸು)</option>
                <option value="Jersey Cross">Jersey Cross (ಜರ್ಸಿ ಕ್ರಾಸ್ ಹಸು)</option>
                <option value="Gir Cow">Gir Cow (ಗಿರ್ ಹಸು)</option>
                <option value="Hallikar Cow">Hallikar Cow (ಹಳ್ಳಿಕಾರ್ ಹಸು)</option>
                <option value="Malnad Gidda">Malnad Gidda (ಮಲೆನಾಡು ಗಿಡ್ಡ ಹಸು)</option>
                <option value="Murrah Buffalo">Murrah Buffalo (ಮುರ್ರಾ ಎಮ್ಮೆ)</option>
                <option value="Jaffarabadi Buffalo">Jaffarabadi Buffalo (ಜಾಫ್ರಾಬಾದಿ ಎಮ್ಮೆ)</option>
              </select>
            </div>
          </div>

          {sireLoading ? (
            <div className="p-12 text-center text-gray-400">Loading sire matching records…</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sireGuides.map(guide => (
                <div
                  key={guide.id}
                  className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm hover:border-purple-300 transition-colors space-y-3"
                >
                  <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Dam Breed</span>
                      <h4 className="font-bold text-gray-800 text-sm">{guide.dam_breed}</h4>
                      {guide.dam_breed_kannada && (
                        <p className="text-[11px] text-purple-900 font-medium">{guide.dam_breed_kannada}</p>
                      )}
                    </div>
                    <GitMerge className="w-5 h-5 text-purple-500" />
                    <div className="text-right">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600">Recommended Sire</span>
                      <h4 className="font-bold text-purple-900 text-sm">{guide.recommended_sire}</h4>
                      {guide.recommended_sire_kannada && (
                        <p className="text-[11px] text-purple-700 font-medium">{guide.recommended_sire_kannada}</p>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="bg-purple-50 p-2.5 rounded-xl border border-purple-100">
                      <strong className="text-purple-900 block mb-0.5">Breeding Goal / Purpose:</strong>
                      <span className="text-purple-950">{guide.purpose}</span>
                    </div>

                    <div className="bg-emerald-50 p-2.5 rounded-xl border border-emerald-100">
                      <strong className="text-emerald-900 block mb-0.5">Expected Daughter Gain:</strong>
                      <span className="text-emerald-950 font-medium">{guide.expected_gain}</span>
                    </div>

                    <div className="bg-amber-50 p-2.5 rounded-xl border border-amber-100 text-amber-950">
                      <strong className="text-amber-900 block mb-0.5">Inbreeding & Safety Caution:</strong>
                      <span>{guide.inbreeding_caution}</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-xs">
                    <span className="text-gray-400 text-[11px]">KAHBI / BAIF semen straws recommended</span>
                    <button
                      onClick={() => triggerVoiceWithPrompt(`${guide.dam_breed} ಹಸುವಿಗೆ ${guide.recommended_sire} ತಳಿಯ ವೀರ್ಯದ ಲಾಭಗಳು ಮತ್ತು ಎಚ್ಚರಿಕೆಗಳನ್ನು ತಿಳಿಸಿ`)}
                      className="text-purple-700 font-semibold hover:underline flex items-center gap-1"
                    >
                      Ask Voice Assistant <Volume2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 5. LIVESTOCK HEALTH & BEHAVIOR VARIATION ADVISOR SUBSECTION */}
      {activeSubTab === 'disease' && (
        <div className="space-y-4">
          {/* Compact 1962 Pashu Sanjeevini Emergency Banner */}
          <div className="bg-gradient-to-r from-rose-600 to-red-600 text-white rounded-2xl p-3.5 sm:p-4 shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <span className="inline-block bg-white/20 text-white text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                🚑 {t('emergency_1962_badge')}
              </span>
              <h3 className="text-sm sm:text-base font-bold leading-snug">
                {t('emergency_1962_title')}
              </h3>
              <p className="text-[11px] sm:text-xs text-rose-100">
                {t('emergency_1962_sub')}
              </p>
            </div>
            <a
              href="tel:1962"
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-white text-rose-700 hover:bg-rose-50 font-extrabold text-xs sm:text-sm rounded-xl shadow-sm transition-colors shrink-0"
            >
              <PhoneCall className="w-4 h-4" />
              <span>{t('call_1962')}</span>
            </a>
          </div>

          {/* 2-Pill Toggle: Symptom Checker vs Cow & Vet Doctors */}
          <div className="inline-flex gap-1.5 bg-gray-100 p-1 rounded-xl">
            <button
              onClick={() => setHealthView('symptoms')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                healthView === 'symptoms'
                  ? 'bg-white text-amber-800 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <HeartPulse className="w-3.5 h-3.5 text-rose-500" />
              <span>{t('symptom_checker')}</span>
            </button>
            <button
              onClick={() => setHealthView('doctors')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                healthView === 'doctors'
                  ? 'bg-white text-amber-800 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Stethoscope className="w-3.5 h-3.5 text-emerald-600" />
              <span>{t('cow_vet_doctors')}</span>
            </button>
          </div>

          {healthView === 'symptoms' && (
            <>
              <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="font-bold text-gray-800 text-sm sm:text-base flex items-center gap-2">
                      <HeartPulse className="w-4 h-4 text-rose-500" />
                      Livestock Health & Behavior Variation Checker
                    </h3>
                    <p className="text-xs text-gray-500">
                      Instant first-aid protocols for sudden milk drops, bloat, fever, mastitis, and appetite loss
                    </p>
                  </div>

                  <input
                    type="text"
                    placeholder="Search symptom (e.g. fever, mastitis)…"
                    value={symptomSearch}
                    onChange={(e) => setSymptomSearch(e.target.value)}
                    className="text-xs bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 w-full sm:w-60 focus:ring-2 focus:ring-rose-500"
                  />
                </div>

                {/* Quick Symptom Chips */}
                <div className="flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
                  {[
                    { label: 'All Symptoms', key: '' },
                    { label: 'Sudden Milk Drop', key: 'sudden_milk_drop' },
                    { label: 'High Fever', key: 'high_fever' },
                    { label: 'Bloating (ಹೊಟ್ಟೆ ಉಬ್ಬರ)', key: 'severe_bloat' },
                    { label: 'Mastitis / ಕೆಚ್ಚಲು ಬಾವು', key: 'mastitis_signs' },
                    { label: 'Lameness (ಕುಂಟುವುದು)', key: 'lameness_foot_lesions' },
                    { label: 'Restlessness', key: 'restlessness_bellowing' },
                  ].map(s => (
                    <button
                      key={s.key}
                      onClick={() => setSymptomSearch(s.key)}
                      className={`flex-shrink-0 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                        symptomSearch === s.key
                          ? 'bg-rose-600 text-white border-rose-700 shadow-sm'
                          : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-rose-50'
                      }`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {diseaseLoading ? (
                <div className="p-12 text-center text-gray-400">Loading diagnostic guidelines…</div>
              ) : (
                <div className="space-y-4">
                  {diseases.map(d => {
                    const isEmergency = d.urgency_level.includes('Emergency') || d.urgency_level.includes('Urgent')
                    return (
                      <div
                        key={d.id}
                        className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-3"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                                isEmergency
                                  ? 'bg-rose-100 text-rose-800 border-rose-200 animate-pulse'
                                  : 'bg-amber-100 text-amber-800 border-amber-200'
                              }`}>
                                ⚠️ {d.urgency_level}
                              </span>
                              <span className="text-xs font-bold text-gray-500">Symptom: {d.symptom_display}</span>
                            </div>
                            <h4 className="font-bold text-gray-900 text-base mt-1">
                              Suspected: {d.suspected_condition}
                            </h4>
                            {d.suspected_kannada && (
                              <p className="text-xs font-semibold text-rose-900">
                                {d.suspected_kannada}
                              </p>
                            )}
                          </div>

                          <button
                            onClick={() => triggerVoiceWithPrompt(d.recommended_query)}
                            className="self-start sm:self-center px-3.5 py-2 bg-gradient-to-r from-rose-600 to-red-600 text-white rounded-xl text-xs font-bold shadow-sm hover:from-rose-700 hover:to-red-700 flex items-center gap-2 transition-all"
                          >
                            <Volume2 className="w-4 h-4" />
                            Ask Voice Advisor in My Language
                          </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                          {/* Immediate first aid */}
                          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 space-y-1.5">
                            <div className="flex items-center gap-1.5 font-bold text-emerald-900 uppercase tracking-wide text-[10px]">
                              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                              Immediate First Aid Protocol (ತಕ್ಷಣದ ಕ್ರಮ):
                            </div>
                            <p className="text-emerald-950 font-medium leading-relaxed">
                              {d.immediate_first_aid}
                            </p>
                          </div>

                          {/* What to avoid */}
                          <div className="bg-rose-50 border border-rose-200 rounded-xl p-3.5 space-y-1.5">
                            <div className="flex items-center gap-1.5 font-bold text-rose-900 uppercase tracking-wide text-[10px]">
                              <AlertTriangle className="w-4 h-4 text-rose-600" />
                              Avoid Doing (ಮಾಡಬಾರದ ತಪ್ಪುಗಳು):
                            </div>
                            <p className="text-rose-950 font-medium leading-relaxed">
                              {d.avoid_doing}
                            </p>
                          </div>
                        </div>

                        {/* Voice prompt preview pill */}
                        <div className="bg-gray-50 rounded-xl p-2.5 text-xs text-gray-600 flex items-center justify-between gap-3">
                          <span className="truncate">
                            <strong>Suggested Query:</strong> "{d.recommended_query}"
                          </span>
                          <button
                            onClick={() => triggerVoiceWithPrompt(d.recommended_query)}
                            className="text-rose-600 font-bold hover:underline whitespace-nowrap"
                          >
                            Ask Now →
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </>
          )}

          {healthView === 'doctors' && (
            <div className="space-y-4">
              {/* Filter & Add Doctor Header */}
              <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
                    {[
                      { value: 'All', label: t('all') },
                      { value: 'Local Cow Doctor', label: t('doctor_type_local') },
                      { value: 'Veterinary Doctor', label: t('doctor_type_vet') },
                    ].map(opt => (
                      <button
                        key={opt.value}
                        onClick={() => setDoctorTypeFilter(opt.value)}
                        className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                          doctorTypeFilter === opt.value
                            ? 'bg-amber-700 text-white border-amber-800 shadow-sm'
                            : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-amber-50'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => setIsDoctorModalOpen(true)}
                    className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-sm transition-colors shrink-0"
                  >
                    <Plus className="w-4 h-4" />
                    <span>{t('add_doctor').replace(/^\+\s*/, '')}</span>
                  </button>
                </div>

                <div className="relative">
                  <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={doctorSearch}
                    onChange={(e) => setDoctorSearch(e.target.value)}
                    placeholder={t('search_doctors_placeholder')}
                    className="w-full pl-9 pr-3 py-2 text-xs bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              {/* Doctors Cards */}
              {doctorsLoading ? (
                <div className="p-10 text-center text-sm text-gray-400">{t('loading')}</div>
              ) : doctors.length === 0 ? (
                <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center text-sm text-gray-500">
                  {t('no_doctors_found')}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {doctors.map(doc => (
                    <div
                      key={doc.id}
                      className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between gap-3"
                    >
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                            doc.doctor_type === 'Veterinary Doctor'
                              ? 'bg-blue-50 text-blue-800 border-blue-200'
                              : 'bg-amber-50 text-amber-800 border-amber-200'
                          }`}>
                            {doc.doctor_type === 'Veterinary Doctor' ? t('doctor_type_vet') : t('doctor_type_local')}
                          </span>
                          {doc.emergency_available && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                              🚑 {t('emergency_available')}
                            </span>
                          )}
                        </div>

                        <h4 className="font-bold text-gray-900 text-sm sm:text-base">{doc.name}</h4>

                        {doc.specialization && (
                          <p className="text-xs text-gray-600 bg-gray-50 rounded-xl p-2.5 border border-gray-100 leading-relaxed">
                            <strong className="text-gray-700">{t('specialization')}:</strong> {doc.specialization}
                          </p>
                        )}

                        <div className="space-y-1 text-xs text-gray-600">
                          <div className="flex items-center gap-1.5">
                            <MapPin className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                            <span>{doc.location}</span>
                          </div>
                          {doc.availability && (
                            <div className="flex items-center gap-1.5">
                              <Clock className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                              <span>{doc.availability}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="pt-2.5 border-t border-gray-100 flex items-center justify-between gap-2">
                        <span className="text-sm font-bold text-gray-800">{doc.phone}</span>
                        <a
                          href={`tel:${doc.phone.replace(/\s+/g, '')}`}
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-sm transition-colors"
                        >
                          <PhoneCall className="w-3.5 h-3.5" />
                          <span>{t('call_now')}</span>
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 6. CATTLE BUY & SELL MARKETPLACE SUBSECTION */}
      {activeSubTab === 'cattle' && (
        <div className="space-y-4">
          {/* Cattle Market Header */}
          <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-gray-800 text-sm sm:text-base flex items-center gap-2">
                <ShoppingBag className="w-4 h-4 text-amber-600" />
                {t('cattle_market_title')}
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('cattle_market_desc')}
              </p>
            </div>
            <button
              onClick={() => setIsCattleModalOpen(true)}
              className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs sm:text-sm font-bold rounded-xl shadow-sm transition-colors shrink-0"
            >
              <Plus className="w-4 h-4" />
              <span>{t('sell_cattle').replace(/^\+\s*/, '')}</span>
            </button>
          </div>

          {/* Filters & Sort Controls */}
          <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="text-[11px] font-bold text-gray-600 block mb-1">{t('breed_filter')}</label>
              <select
                value={cattleBreedFilter}
                onChange={(e) => setCattleBreedFilter(e.target.value)}
                className="w-full text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
              >
                <option value="All">{t('all_breeds')}</option>
                {CATTLE_BREED_OPTIONS.map(b => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] font-bold text-gray-600 block mb-1">{t('min_price')}</label>
              <input
                type="number"
                min="0"
                placeholder="0"
                value={cattleMinPrice}
                onChange={(e) => setCattleMinPrice(e.target.value)}
                className="w-full text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div>
              <label className="text-[11px] font-bold text-gray-600 block mb-1">{t('max_price')}</label>
              <input
                type="number"
                min="0"
                placeholder="150000"
                value={cattleMaxPrice}
                onChange={(e) => setCattleMaxPrice(e.target.value)}
                className="w-full text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div>
              <label className="text-[11px] font-bold text-gray-600 block mb-1">{t('sort_by')}</label>
              <select
                value={cattleSortBy}
                onChange={(e) => setCattleSortBy(e.target.value)}
                className="w-full text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
              >
                <option value="newest">{t('sort_newest')}</option>
                <option value="price_asc">{t('sort_price_asc')}</option>
                <option value="price_desc">{t('sort_price_desc')}</option>
                <option value="milk_desc">{t('sort_milk_desc')}</option>
              </select>
            </div>
          </div>

          {/* Cattle Cards Grid */}
          {cattleLoading ? (
            <div className="p-10 text-center text-sm text-gray-400">{t('loading')}</div>
          ) : cattleListings.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center text-sm text-gray-500">
              {t('no_cattle_found')}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {cattleListings.map(item => (
                <div
                  key={item.id}
                  className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between gap-3"
                >
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                          <Tag className="w-3 h-3" />
                          {item.breed}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-100 text-gray-700 border border-gray-200">
                          {item.animal_type}
                        </span>
                      </div>
                      <span className="text-base sm:text-lg font-extrabold text-emerald-700 shrink-0">
                        ₹{Number(item.price_inr).toLocaleString('en-IN')}
                      </span>
                    </div>

                    <h4 className="font-bold text-gray-900 text-sm sm:text-base leading-snug">
                      {item.title}
                    </h4>

                    <div className="grid grid-cols-2 gap-2 bg-gray-50 rounded-xl p-2.5 border border-gray-100 text-xs">
                      <div>
                        <span className="text-[10px] text-gray-400 uppercase font-bold block">{t('milk_per_day')}</span>
                        <span className="font-bold text-emerald-700">
                          {item.milk_yield_liters_per_day} {t('litres_per_day')}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-gray-400 uppercase font-bold block">{t('age_years_label')}</span>
                        <span className="font-bold text-gray-800">
                          {item.age_years} {t('years_short')}
                        </span>
                      </div>
                    </div>

                    {item.description && (
                      <p className="text-xs text-gray-600 leading-relaxed">{item.description}</p>
                    )}

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600">
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-emerald-600" />
                        {item.location}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <User className="w-3.5 h-3.5 text-gray-400" />
                        {item.owner_name}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2.5 border-t border-gray-100 flex items-center justify-between gap-2">
                    <span className="text-sm font-bold text-gray-800">{item.owner_phone}</span>
                    <a
                      href={`tel:${item.owner_phone.replace(/\s+/g, '')}`}
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-sm transition-colors"
                    >
                      <PhoneCall className="w-3.5 h-3.5" />
                      <span>{t('call_now')}</span>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add Doctor Modal */}
      {isDoctorModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-emerald-50/70 sticky top-0">
              <h2 className="text-base font-bold text-gray-800">{t('add_doctor_title')}</h2>
              <button
                onClick={() => setIsDoctorModalOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateDoctor} className="p-5 space-y-3.5">
              {doctorError && (
                <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
                  {doctorError}
                </div>
              )}

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('name')} *</label>
                <input
                  type="text"
                  required
                  value={doctorForm.name}
                  onChange={(e) => setDoctorForm({ ...doctorForm, name: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('category')} *</label>
                <select
                  value={doctorForm.doctor_type}
                  onChange={(e) => setDoctorForm({ ...doctorForm, doctor_type: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="Local Cow Doctor">{t('doctor_type_local')}</option>
                  <option value="Veterinary Doctor">{t('doctor_type_vet')}</option>
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('phone')} *</label>
                  <input
                    type="text"
                    required
                    placeholder="+91 98450 00000"
                    value={doctorForm.phone}
                    onChange={(e) => setDoctorForm({ ...doctorForm, phone: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('location')} *</label>
                  <input
                    type="text"
                    required
                    placeholder="Mandya / Shivamogga"
                    value={doctorForm.location}
                    onChange={(e) => setDoctorForm({ ...doctorForm, location: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('specialization')}</label>
                <input
                  type="text"
                  placeholder="AI, Mastitis, Obstetric Care…"
                  value={doctorForm.specialization}
                  onChange={(e) => setDoctorForm({ ...doctorForm, specialization: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('availability')}</label>
                <input
                  type="text"
                  placeholder="Daily 7 AM – 7 PM"
                  value={doctorForm.availability}
                  onChange={(e) => setDoctorForm({ ...doctorForm, availability: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <label className="flex items-center gap-2 text-xs font-semibold text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={doctorForm.emergency_available}
                  onChange={(e) => setDoctorForm({ ...doctorForm, emergency_available: e.target.checked })}
                  className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                />
                <span>{t('emergency_available')}</span>
              </label>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsDoctorModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  disabled={doctorSaving}
                  className="px-4 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm transition-colors disabled:opacity-60"
                >
                  {doctorSaving ? t('saving') : t('submit')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sell Cattle Modal */}
      {isCattleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-emerald-50/70 sticky top-0">
              <h2 className="text-base font-bold text-gray-800">{t('sell_cattle').replace(/^\+\s*/, '')}</h2>
              <button
                onClick={() => setIsCattleModalOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCattle} className="p-5 space-y-3.5">
              {cattleError && (
                <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
                  {cattleError}
                </div>
              )}

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('listing_title')} *</label>
                <input
                  type="text"
                  required
                  placeholder="High-Yield HF Crossbred Cow"
                  value={cattleForm.title}
                  onChange={(e) => setCattleForm({ ...cattleForm, title: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('breed_filter')} *</label>
                  <select
                    value={cattleForm.breed}
                    onChange={(e) => setCattleForm({ ...cattleForm, breed: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    {CATTLE_BREED_OPTIONS.map(b => (
                      <option key={b} value={b}>{b}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('animal_type')} *</label>
                  <select
                    value={cattleForm.animal_type}
                    onChange={(e) => setCattleForm({ ...cattleForm, animal_type: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    {CATTLE_ANIMAL_TYPES.map(at => (
                      <option key={at} value={at}>{at}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('price_inr')} *</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={cattleForm.price_inr}
                    onChange={(e) => setCattleForm({ ...cattleForm, price_inr: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('milk_yield_lpd')}</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={cattleForm.milk_yield_liters_per_day}
                    onChange={(e) => setCattleForm({ ...cattleForm, milk_yield_liters_per_day: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('age_years')}</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={cattleForm.age_years}
                    onChange={(e) => setCattleForm({ ...cattleForm, age_years: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('location')} *</label>
                <input
                  type="text"
                  required
                  placeholder="Hassan / Mandya / Belagavi"
                  value={cattleForm.location}
                  onChange={(e) => setCattleForm({ ...cattleForm, location: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('owner_name')} *</label>
                  <input
                    type="text"
                    required
                    value={cattleForm.owner_name}
                    onChange={(e) => setCattleForm({ ...cattleForm, owner_name: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('owner_phone')} *</label>
                  <input
                    type="text"
                    required
                    placeholder="+91 98450 00000"
                    value={cattleForm.owner_phone}
                    onChange={(e) => setCattleForm({ ...cattleForm, owner_phone: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('description')}</label>
                <textarea
                  rows={2}
                  value={cattleForm.description}
                  onChange={(e) => setCattleForm({ ...cattleForm, description: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCattleModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  disabled={cattleSaving}
                  className="px-4 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm transition-colors disabled:opacity-60"
                >
                  {cattleSaving ? t('saving') : t('submit')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
