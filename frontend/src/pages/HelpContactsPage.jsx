import React, { useState, useEffect } from 'react'
import {
  PhoneCall,
  Search,
  MapPin,
  Plus,
  X,
  FileText,
  Tag
} from 'lucide-react'
import { helpApi } from '../api/client'
import { useI18n } from '../context/I18nContext'

export const HELP_CATEGORIES = [
  { value: 'Agriculture Product Merchants & Buyers', key: 'cat_merchants' },
  { value: 'Agricultural Machineries (Tractors, Harvesters, Tree Cutters)', key: 'cat_machineries' },
  { value: 'Pesticide Sprayermen', key: 'cat_sprayermen' },
  { value: 'Farm Work Contractors', key: 'cat_contractors' },
  { value: 'Tree Planting Sketchers', key: 'cat_sketchers' },
  { value: 'Machine & Pump Set Mechanics', key: 'cat_mechanics' },
  { value: 'Electricians', key: 'cat_electricians' },
  { value: 'Carpenters', key: 'cat_carpenters' },
  { value: 'Pipe Connections & Water Jet Mounters', key: 'cat_pipes' },
  { value: 'Agricultural Products Shop Owners', key: 'cat_shop_owners' },
]

const CATEGORY_KEY_MAP = Object.fromEntries(
  HELP_CATEGORIES.map((c) => [c.value, c.key])
)

export default function HelpContactsPage() {
  const { t } = useI18n()
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [formData, setFormData] = useState({
    name: '',
    category: HELP_CATEGORIES[0].value,
    phone: '',
    location: '',
    notes: '',
  })

  const fetchContacts = () => {
    setLoading(true)
    const catParam = selectedCategory === 'All' ? null : selectedCategory
    const searchParam = searchQuery.trim() || null
    helpApi
      .getContacts(catParam, searchParam)
      .then((res) => {
        setContacts(res.data || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchContacts()
  }, [selectedCategory, searchQuery])

  const handleSubmit = (e) => {
    e.preventDefault()
    setSaving(true)
    setErrorMsg('')
    helpApi
      .createContact(formData)
      .then(() => {
        setIsModalOpen(false)
        setFormData({
          name: '',
          category: HELP_CATEGORIES[0].value,
          phone: '',
          location: '',
          notes: '',
        })
        fetchContacts()
      })
      .catch((err) => {
        setErrorMsg(err?.response?.data?.detail || 'Failed to save contact')
      })
      .finally(() => setSaving(false))
  }

  const getCategoryLabel = (catValue) => {
    const key = CATEGORY_KEY_MAP[catValue]
    return key ? t(key, catValue) : catValue
  }

  return (
    <div className="px-4 py-4 space-y-4 max-w-4xl mx-auto">
      {/* Header Card */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-700 shrink-0">
            <PhoneCall className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-gray-800">
              {t('help_directory_title')}
            </h1>
            <p className="text-xs text-gray-500">
              {t('help_directory_sub')}
            </p>
          </div>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs sm:text-sm font-bold rounded-xl shadow-sm transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>{t('add_contact').replace(/^\+\s*/, '')}</span>
        </button>
      </div>

      {/* Search & Category Pills */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('search_contacts_placeholder')}
            className="w-full pl-9 pr-3 py-2 text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>

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
          {HELP_CATEGORIES.map((cat) => {
            const isActive = selectedCategory === cat.value
            return (
              <button
                key={cat.value}
                onClick={() => setSelectedCategory(cat.value)}
                className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                  isActive
                    ? 'bg-emerald-600 text-white border-emerald-700 shadow-sm'
                    : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-emerald-50'
                }`}
              >
                {t(cat.key, cat.value)}
              </button>
            )
          })}
        </div>
      </div>

      {/* Contacts Grid */}
      {loading ? (
        <div className="p-10 text-center text-sm text-gray-400">{t('loading')}</div>
      ) : contacts.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center text-sm text-gray-500">
          {t('no_contacts_found')}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {contacts.map((c) => (
            <div
              key={c.id}
              className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between gap-3"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-bold text-gray-900 text-sm sm:text-base leading-snug">
                    {c.name}
                  </h3>
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0 max-w-[55%] truncate">
                    <Tag className="w-3 h-3 shrink-0" />
                    <span className="truncate">{getCategoryLabel(c.category)}</span>
                  </span>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-gray-600">
                  <MapPin className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>{c.location}</span>
                </div>

                {c.notes && (
                  <div className="flex items-start gap-1.5 text-xs text-gray-600 bg-gray-50 rounded-xl p-2.5 border border-gray-100">
                    <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0 mt-0.5" />
                    <p className="leading-relaxed">{c.notes}</p>
                  </div>
                )}
              </div>

              <div className="pt-2.5 border-t border-gray-100 flex items-center justify-between gap-2">
                <span className="text-sm font-bold text-gray-800 tracking-wide">
                  {c.phone}
                </span>
                <a
                  href={`tel:${c.phone.replace(/\s+/g, '')}`}
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

      {/* Add Contact Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 bg-emerald-50/70">
              <h2 className="text-base font-bold text-gray-800">{t('add_contact_title')}</h2>
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
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('name')} *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('category')} *</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  {HELP_CATEGORIES.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {t(cat.key, cat.value)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('phone')} *</label>
                  <input
                    type="text"
                    required
                    placeholder="+91 98450 00000"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-700 block mb-1">{t('location')} *</label>
                  <input
                    type="text"
                    required
                    placeholder="Shivamogga / Sirsi"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    className="w-full text-xs sm:text-sm bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-gray-700 block mb-1">{t('notes')}</label>
                <textarea
                  rows={2}
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
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
