import React, { useState, useEffect } from 'react'
import {
  Newspaper, TrendingUp, Tractor, CloudRain, Tag, Landmark,
  ShieldCheck, Gauge, Sparkles, SunMedium, Search, Clock,
  ArrowRight, CheckCircle2, Bookmark, Share2, Filter, Volume2
} from 'lucide-react'
import { newsApi } from '../api/client'

const CATEGORY_ICONS = {
  TrendingUp: TrendingUp,
  Tractor: Tractor,
  CloudRain: CloudRain,
  Tag: Tag,
  Landmark: Landmark,
  ShieldCheck: ShieldCheck,
  Gauge: Gauge,
  Sparkles: Sparkles,
  SunMedium: SunMedium,
}

const BADGE_COLORS = {
  emerald: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  blue:    'bg-blue-100 text-blue-800 border-blue-200',
  sky:     'bg-sky-100 text-sky-800 border-sky-200',
  rose:    'bg-rose-100 text-rose-800 border-rose-200',
  purple:  'bg-purple-100 text-purple-800 border-purple-200',
  amber:   'bg-amber-100 text-amber-800 border-amber-200',
  teal:    'bg-teal-100 text-teal-800 border-teal-200',
  indigo:  'bg-indigo-100 text-indigo-800 border-indigo-200',
  yellow:  'bg-yellow-100 text-yellow-800 border-yellow-200',
}

export default function NewsPage({ onAskVoice }) {
  const [categories, setCategories] = useState([])
  const [selectedCatId, setSelectedCatId] = useState(null) // null = all
  const [articles, setArticles] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [activeArticleModal, setActiveArticleModal] = useState(null)

  // Fetch categories
  useEffect(() => {
    newsApi.getCategories()
      .then(res => setCategories(res.data))
      .catch(() => {})
  }, [])

  // Fetch articles
  useEffect(() => {
    setLoading(true)
    newsApi.getArticles(selectedCatId, search)
      .then(res => {
        setArticles(res.data.articles || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [selectedCatId, search])

  const renderCatIcon = (iconName, className = 'w-4 h-4') => {
    const Comp = CATEGORY_ICONS[iconName] || Newspaper
    return <Comp className={className} />
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
          <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center text-purple-700">
            <Newspaper className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-gray-800">
              Agri-Only Curated News & Insights
            </h1>
            <p className="text-xs text-gray-500">
              ಕೃಷಿ ಸಮಾಚಾರ · Strictly 9 Essential Farm Topics for Karnataka Farmers
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search news & schemes…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-gray-50 border border-gray-200 rounded-xl text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
      </div>

      {/* STRICT 9 CATEGORY FILTER PILLS */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-purple-600" />
            Select Agricultural Topic ({categories.length})
          </span>
          {selectedCatId && (
            <button
              onClick={() => setSelectedCatId(null)}
              className="text-xs text-purple-600 font-semibold hover:underline"
            >
              Show All Topics
            </button>
          )}
        </div>

        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
          <button
            onClick={() => setSelectedCatId(null)}
            className={`flex-shrink-0 px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
              selectedCatId === null
                ? 'bg-purple-700 text-white border-purple-800 shadow-sm'
                : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
            }`}
          >
            All 9 Topics
          </button>

          {categories.map(cat => {
            const isSelected = selectedCatId === cat.id
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCatId(cat.id)}
                className={`flex-shrink-0 flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-all border ${
                  isSelected
                    ? 'bg-purple-700 text-white border-purple-800 shadow-sm font-semibold'
                    : 'bg-white text-gray-700 border-gray-200 hover:bg-purple-50 hover:border-purple-200'
                }`}
              >
                <span className={isSelected ? 'text-white' : 'text-purple-600'}>
                  {renderCatIcon(cat.icon, 'w-3.5 h-3.5')}
                </span>
                <span>{cat.name}</span>
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  isSelected ? 'bg-purple-900 text-white' : 'bg-gray-100 text-gray-500'
                }`}>
                  {cat.article_count}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* ARTICLES LIST */}
      {loading ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 flex flex-col items-center justify-center text-gray-400 gap-3">
          <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm">Fetching verified agricultural news articles…</p>
        </div>
      ) : articles.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center text-gray-400 space-y-2">
          <p className="text-sm font-semibold text-gray-600">No articles found matching your filter.</p>
          <button
            onClick={() => { setSelectedCatId(null); setSearch('') }}
            className="text-xs text-purple-600 font-medium underline"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {articles.map(article => {
            const badgeClass = BADGE_COLORS[article.badge_color] || BADGE_COLORS.emerald
            return (
              <article
                key={article.id}
                onClick={() => setActiveArticleModal(article)}
                className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm hover:shadow-md hover:border-purple-300 transition-all cursor-pointer flex flex-col justify-between group"
              >
                <div>
                  {/* Category Pill & Read Time */}
                  <div className="flex items-center justify-between gap-2 mb-2.5">
                    <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${badgeClass} flex items-center gap-1.5`}>
                      {renderCatIcon(article.icon, 'w-3 h-3')}
                      <span className="truncate max-w-[200px]">{article.category_name}</span>
                    </span>
                    <span className="text-[11px] text-gray-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {article.read_time}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="font-bold text-gray-800 text-sm sm:text-base leading-snug group-hover:text-purple-700 transition-colors">
                    {article.title}
                  </h3>
                  {article.title_kannada && (
                    <p className="text-xs font-semibold text-purple-900 mt-1 line-clamp-1">
                      {article.title_kannada}
                    </p>
                  )}

                  {/* Summary */}
                  <p className="text-xs text-gray-600 mt-2 line-clamp-2 leading-relaxed">
                    {article.summary}
                  </p>

                  {/* Key Takeaways Preview */}
                  {article.key_takeaways?.length > 0 && (
                    <div className="mt-3 bg-gray-50 rounded-xl p-2.5 space-y-1">
                      <p className="text-[10px] font-bold uppercase text-gray-500 tracking-wider">
                        Key Takeaways:
                      </p>
                      {article.key_takeaways.slice(0, 2).map((takeaway, idx) => (
                        <div key={idx} className="flex items-start gap-1.5 text-xs text-gray-700">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          <span className="line-clamp-1">{takeaway}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                  {/* Footer */}
                  <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
                    <span className="truncate max-w-[140px]">{article.source}</span>
                    <div className="flex items-center gap-2">
                      {article.voice_query_prompt && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            triggerVoiceWithPrompt(article.voice_query_prompt)
                          }}
                          className="px-2.5 py-1 rounded-lg bg-purple-50 text-purple-700 hover:bg-purple-100 font-semibold flex items-center gap-1 text-[11px]"
                          title="Ask Voice Advisor about this article"
                        >
                          <Volume2 className="w-3.5 h-3.5" />
                          <span>Ask Voice</span>
                        </button>
                      )}
                      <span className="flex items-center gap-1 font-semibold text-purple-600 group-hover:translate-x-1 transition-transform">
                        Read <ArrowRight className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>
              </article>
            )
          })}
        </div>
      )}

      {/* ARTICLE DETAIL MODAL */}
      {activeArticleModal && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm p-0 sm:p-4">
          <div className="w-full sm:max-w-2xl bg-white rounded-t-3xl sm:rounded-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="px-5 py-4 bg-purple-800 text-white flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-200">
                {activeArticleModal.category_name}
              </span>
              <button
                onClick={() => setActiveArticleModal(null)}
                className="p-1 rounded-full text-white/80 hover:text-white hover:bg-white/10"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 sm:p-6 overflow-y-auto space-y-4">
              <div>
                <span className="text-xs text-gray-400">
                  {activeArticleModal.published_date} · {activeArticleModal.source} · {activeArticleModal.read_time}
                </span>
                <h2 className="text-lg sm:text-xl font-bold text-gray-900 mt-1">
                  {activeArticleModal.title}
                </h2>
                {activeArticleModal.title_kannada && (
                  <p className="text-sm font-semibold text-purple-900 mt-1">
                    {activeArticleModal.title_kannada}
                  </p>
                )}
              </div>

              <div className="bg-purple-50 border border-purple-100 rounded-xl p-3 text-xs text-purple-950 font-medium">
                {activeArticleModal.summary}
              </div>

              {activeArticleModal.content && (
                <div className="text-sm text-gray-700 leading-relaxed space-y-2">
                  <p>{activeArticleModal.content}</p>
                </div>
              )}

              {activeArticleModal.key_takeaways?.length > 0 && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-2">
                  <p className="text-xs font-bold text-emerald-800 uppercase tracking-wide">
                    Farmer Action Points:
                  </p>
                  <ul className="space-y-1.5">
                    {activeArticleModal.key_takeaways.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-emerald-950 font-medium">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-5 py-3 bg-gray-50 border-t border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-500">
              <span>Category {activeArticleModal.category_id} of 9 · Farm Advisor News</span>
              <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                {activeArticleModal.voice_query_prompt && (
                  <button
                    onClick={() => {
                      triggerVoiceWithPrompt(activeArticleModal.voice_query_prompt)
                      setActiveArticleModal(null)
                    }}
                    className="px-3.5 py-1.5 bg-purple-700 text-white rounded-lg hover:bg-purple-800 font-semibold flex items-center gap-1.5 shadow-sm"
                  >
                    <Volume2 className="w-3.5 h-3.5" />
                    Ask Voice Advisor in My Language
                  </button>
                )}
                <button
                  onClick={() => setActiveArticleModal(null)}
                  className="px-4 py-1.5 bg-gray-800 text-white rounded-lg hover:bg-gray-700 font-medium"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
