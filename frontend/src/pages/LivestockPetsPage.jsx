import React, { useState, useEffect } from 'react'
import {
  PawPrint,
  PhoneCall,
  MapPin,
  Plus,
  X,
  User,
  Tag
} from 'lucide-react'
import { livestockPetsApi } from '../api/client'
import { useI18n } from '../context/I18nContext'

const LP_CATEGORIES = [
  { value: 'Poultry', key: 'lp_cat_poultry' },
  { value: 'Goats & Sheep', key: 'lp_cat_goats_sheep' },
  { value: 'Pets', key: 'lp_cat_pets' },
  { value: 'Domestic Animals', key: 'lp_cat_domestic' },
]

const CATEGORY_KEY_MAP = Object.fromEntries(
  LP_CATEGORIES.map((c) => [c.value, c.key])
)

export default function LivestockPetsPage() {
  const { t } = useI18n()
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)

  const [selectedCategory, setSelectedCategory] = useState('All')
  const [minPrice, setMinPrice] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [sortBy, setSortBy] = useState('newest')

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [formData, setFormData] = useState({
    title: '',
    category: 'Poultry',
    breed_or_type: '',
    quantity: '1',
    age: '',
    price_inr: '',
    location: '',
    owner_name: '',
    owner_phone: '',
    description: '',
  })

  const fetchListings = () => {
    setLoading(true)
    livestockPetsApi
      .getListings({
        category: selectedCategory === 'All' ? null : selectedCategory,
        min_price: minPrice,
        max_price: maxPrice,
        sort_by: sortBy,
      })
      .then((res) => {
        setListings(res.data || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchListings()
  }, [selectedCategory, minPrice, maxPrice, sortBy])

  const handleSubmit = (e) => {
    e.preventDefault()
    setSaving(true)
    setErrorMsg('')
    livestockPetsApi
      .createListing({
        title: formData.title,
        category: formData.category,
        breed_or_type: formData.breed_or_type,
        quantity: parseInt(formData.quantity || '1', 10),
        age: formData.age || null,
        price_inr: parseFloat(formData.price_inr || '0'),
        location: formData.location,
        owner_name: formData.owner_name,
        owner_phone: formData.owner_phone,
        description: formData.description || null,
      })
      .then(() => {
        setIsModalOpen(false)
        setFormData({
          title: '',
          category: 'Poultry',
          breed_or_type: '',
          quantity: '1',
          age: '',
          price_inr: '',
          location: '',
          owner_name: '',
          owner_phone: '',
          description: '',
        })
        fetchListings()
      })
      .catch((err) => {
        setErrorMsg(err?.response?.data?.detail || 'Failed to post listing')
      })
      .finally(() => setSaving(false))
  }

  const getCategoryLabel = (val) => {
    const k = CATEGORY_KEY_MAP[val]
    return k ? t(k, val) : val
  }

  return (
    <div className="px-4 py-4 space-y-4 max-w-4xl mx-auto">
      {/* Header Card */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700 shrink-0">
            <PawPrint className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-gray-800">
              {t('livestock_pets_title')}
            </h1>
            <p className="text-xs text-gray-500">
              {t('livestock_pets_desc')}
            </p>
          </div>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs sm:text-sm font-bold rounded-xl shadow-sm transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>{t('post_listing').replace(/^\+\s*/, '')}</span>
        </button>
      </div>

      {/* Category Pills & Filter/Sort Bar */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm space-y-3">
        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
          <button
            onClick={() => setSelectedCategory('All')}
            className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all ${
              selectedCategory === 'All'
                ? 'bg-emerald-600 text-white border-emerald-700 shadow-sm'
                : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-emerald-50'
            }`}
          >
            {t('all')}
          </button>
          {LP_CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                selectedCategory === cat.value
                  ? 'bg-emerald-600 text-white border-emerald-700 shadow-sm'
                  : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-emerald-50'
              }`}
            >
              {t(cat.key, cat.value)}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
          <div>
            <label className="text-[11px] font-bold text-gray-600 block mb-1">{t('min_price')}</label>
            <input
              type="number"
              min="0"
              placeholder="0"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
              className="w-full text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="text-[11px] font-bold text-gray-600 block mb-1">{t('max_price')}</label>
            <input
              type="number"
              min="0"
              placeholder="150000"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              className="w-full text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="text-[11px] font-bold text-gray-600 block mb-1">{t('sort_by')}</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full text-xs font-semibold bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="newest">{t('sort_newest')}</option>
              <option value="price_asc">{t('sort_price_asc')}</option>
              <option value="price_desc">{t('sort_price_desc')}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Listings Grid */}
      {loading ? (
        <div className="p-10 text-center text-sm text-gray-400">{t('loading')}</div>
      ) : listings.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center text-sm text-gray-500">
          {t('no_listings_found')}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {listings.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between gap-3"
            >
              <div className="space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <Tag className="w-3 h-3" />
                    {getCategoryLabel(item.category)}
                  </span>
                  <span className="text-base sm:text-lg font-extrabold text-emerald-700">
                    ₹{Number(item.price_inr).toLocaleString('en-IN')}
                  </span>
                </div>

                <div>
                  <h3 className="font-bold text-gray-900 text-sm sm:text-base leading-snug">
                    {item.title}
                  </h3>
                  <p className="text-xs font-semibold text-gray-600 mt-0.5">
                    {item.breed_or_type}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 bg-gray-50 rounded-xl p-2.5 border border-gray-100 text-xs">
                  <div>
                    <span className="text-[10px] text-gray-400 uppercase font-bold block">{t('quantity')}</span>
                    <span className="font-bold text-gray-800">{item.quantity}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-gray-400 uppercase font-bold block">{t('age_label')}</span>
                    <span className="font-bold text-gray-800">{item.age || '—'}</span>
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

      {/* Post Listing Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-emerald-50/70 sticky top-0">
              <h2 className="text-base font-bold text-gray-800">{t('post_listing').replace(/^\+\s*/, '')}</h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-5 space-y-3.5">
              {errorMsg && (
                <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
                  {errorMsg}
                </div>
              )}

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('listing_title')} *</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('category')} *</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    {LP_CATEGORIES.map((cat) => (
                      <option key={cat.value} value={cat.value}>
                        {t(cat.key, cat.value)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('breed_or_type')} *</label>
                  <input
                    type="text"
                    required
                    placeholder="Naati Koli / Osmanabadi / Mudhol Hound"
                    value={formData.breed_or_type}
                    onChange={(e) => setFormData({ ...formData, breed_or_type: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('quantity')} *</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('age_label')}</label>
                  <input
                    type="text"
                    placeholder="6 months"
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('price_inr')} *</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={formData.price_inr}
                    onChange={(e) => setFormData({ ...formData, price_inr: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('location')} *</label>
                <input
                  type="text"
                  required
                  placeholder="Mandya / Mysuru / Bagalkote"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('owner_name')} *</label>
                  <input
                    type="text"
                    required
                    value={formData.owner_name}
                    onChange={(e) => setFormData({ ...formData, owner_name: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('owner_phone')} *</label>
                  <input
                    type="text"
                    required
                    placeholder="+91 98450 00000"
                    value={formData.owner_phone}
                    onChange={(e) => setFormData({ ...formData, owner_phone: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('description')}</label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm transition-colors disabled:opacity-60"
                >
                  {saving ? t('saving') : t('submit')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
