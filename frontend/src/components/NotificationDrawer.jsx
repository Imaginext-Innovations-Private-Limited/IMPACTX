import React, { useState, useEffect } from 'react'
import {
  X, Bell, CheckCircle2, Circle, Clock, ExternalLink, Phone,
  ShieldCheck, Award, Zap, AlertTriangle, ArrowRight, CheckSquare,
  Sparkles, Filter, ChevronDown, ChevronUp
} from 'lucide-react'
import { notificationApi } from '../api/client'

export default function NotificationDrawer({ isOpen, onClose, onUnreadCountChange }) {
  const [activeCategory, setActiveCategory] = useState('all')
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [toggleLoadingKey, setToggleLoadingKey] = useState(null)

  useEffect(() => {
    if (isOpen) {
      fetchNotifications()
    }
  }, [isOpen, activeCategory])

  const fetchNotifications = () => {
    setLoading(true)
    const cat = activeCategory === 'all' ? null : activeCategory
    notificationApi.getAll(cat)
      .then(res => {
        setNotifications(res.data.notifications || [])
        setUnreadCount(res.data.unread_count || 0)
        if (onUnreadCountChange) onUnreadCountChange(res.data.unread_count || 0)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  const handleMarkRead = (id) => {
    notificationApi.markRead(id)
      .then(() => {
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
        setUnreadCount(prev => Math.max(0, prev - 1))
        if (onUnreadCountChange) onUnreadCountChange(Math.max(0, unreadCount - 1))
      })
      .catch(() => {})
  }

  const handleMarkAllRead = () => {
    notificationApi.markAllRead()
      .then(() => {
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
        setUnreadCount(0)
        if (onUnreadCountChange) onUnreadCountChange(0)
      })
      .catch(() => {})
  }

  const handleToggleDoc = (notificationId, docKey, currentStatus, e) => {
    e.stopPropagation()
    const newStatus = !currentStatus
    const loadKey = `${notificationId}_${docKey}`
    setToggleLoadingKey(loadKey)

    notificationApi.toggleChecklist(notificationId, docKey, newStatus)
      .then(res => {
        setNotifications(prev => prev.map(n => {
          if (n.id === notificationId) {
            const updatedChecklist = n.checklist.map(item =>
              item.doc_key === docKey ? { ...item, is_completed: newStatus } : item
            )
            const completedCount = updatedChecklist.filter(c => c.is_completed).length
            const pct = Math.round((completedCount / updatedChecklist.length) * 100)
            return {
              ...n,
              checklist: updatedChecklist,
              completed_docs: completedCount,
              doc_progress_pct: pct,
            }
          }
          return n
        }))
        setToggleLoadingKey(null)
      })
      .catch(() => setToggleLoadingKey(null))
  }

  const calculateDaysLeft = (deadlineDateStr) => {
    try {
      const deadline = new Date(deadlineDateStr)
      const now = new Date()
      const diffTime = deadline - now
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      if (diffDays < 0) return 'Expired'
      if (diffDays === 0) return 'Closes Today'
      return `${diffDays} days left`
    } catch {
      return deadlineDateStr
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs transition-opacity">
      {/* Slide-over panel */}
      <div className="w-full sm:max-w-md bg-white h-full shadow-2xl flex flex-col justify-between overflow-hidden animate-in slide-in-from-right duration-200">
        
        {/* Header */}
        <div className="px-5 py-4 bg-gradient-to-r from-emerald-800 to-green-900 text-white flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <Bell className="w-5 h-5 text-emerald-200" />
              {unreadCount > 0 && (
                <span className="absolute -top-1.5 -right-2 bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full ring-2 ring-emerald-900 animate-pulse">
                  {unreadCount}
                </span>
              )}
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-bold leading-tight">Scheme & Relief Alerts</h2>
              <p className="text-[11px] text-emerald-200">ಯೋಜನೆ, ಸಬ್ಸಿಡಿ ಮತ್ತು ಪರಿಹಾರ ಅಧಿಸೂಚನೆಗಳು</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-[11px] bg-white/10 hover:bg-white/20 text-emerald-100 px-2 py-1 rounded-lg transition-colors font-medium"
              >
                Mark all read
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-white/10 text-white/80 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 flex gap-1.5 overflow-x-auto no-scrollbar">
          {[
            { id: 'all', label: 'All Alerts' },
            { id: 'training', label: 'Fellowships' },
            { id: 'subsidies', label: 'Subsidies' },
            { id: 'insurance', label: 'Insurance' },
            { id: 'relief', label: 'Drought/Relief' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveCategory(tab.id)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                activeCategory === tab.id
                  ? 'bg-emerald-700 text-white border-emerald-800 shadow-xs'
                  : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Notifications Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-48 text-gray-400 gap-2">
              <div className="w-6 h-6 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs">Loading official notifications…</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="text-center py-16 text-gray-400 space-y-2">
              <Bell className="w-8 h-8 text-gray-300 mx-auto" />
              <p className="text-sm font-semibold text-gray-600">No active alerts for this category</p>
            </div>
          ) : (
            notifications.map(item => {
              const isExpanded = expandedId === item.id
              const daysLeft = calculateDaysLeft(item.deadline_date)
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    setExpandedId(isExpanded ? null : item.id)
                    if (!item.is_read) handleMarkRead(item.id)
                  }}
                  className={`rounded-2xl border transition-all cursor-pointer p-4 ${
                    !item.is_read
                      ? 'bg-emerald-50/50 border-emerald-300 ring-1 ring-emerald-200 shadow-xs'
                      : 'bg-white border-gray-200 hover:border-gray-300 shadow-xs'
                  }`}
                >
                  {/* Top tags row */}
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                        item.category === 'relief'
                          ? 'bg-rose-100 text-rose-800 border-rose-200'
                          : item.category === 'subsidies'
                          ? 'bg-amber-100 text-amber-800 border-amber-200'
                          : item.category === 'insurance'
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-purple-100 text-purple-800 border-purple-200'
                      }`}>
                        {item.category}
                      </span>
                      {!item.is_read && (
                        <span className="w-2 h-2 rounded-full bg-emerald-600" title="Unread" />
                      )}
                    </div>

                    {/* Deadline Countdown Tag */}
                    <div className="flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                      <Clock className="w-3 h-3 text-rose-600" />
                      <span>{daysLeft}</span>
                    </div>
                  </div>

                  {/* Title */}
                  <h3 className="font-bold text-gray-900 text-sm leading-snug">
                    {item.title}
                  </h3>
                  {item.title_kannada && (
                    <p className="text-xs font-semibold text-emerald-900 mt-0.5">
                      {item.title_kannada}
                    </p>
                  )}

                  {/* Summary */}
                  <p className="text-xs text-gray-600 mt-2 line-clamp-2 leading-relaxed">
                    {item.summary}
                  </p>

                  {/* Benefit amount highlight */}
                  <div className="mt-3 flex items-center justify-between bg-gray-50 p-2 rounded-xl text-xs">
                    <div>
                      <span className="text-[10px] font-bold text-gray-400 uppercase">Benefit</span>
                      <p className="font-bold text-emerald-700">{item.benefit_amount}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] font-bold text-gray-400 uppercase">Deadline</span>
                      <p className="font-semibold text-gray-700">{item.deadline_date}</p>
                    </div>
                  </div>

                  {/* Required Documents Progress Bar */}
                  <div className="mt-3 pt-2.5 border-t border-gray-100">
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <span className="font-semibold text-gray-700 flex items-center gap-1">
                        <CheckSquare className="w-3.5 h-3.5 text-emerald-600" />
                        Documents Ready: {item.completed_docs}/{item.total_docs}
                      </span>
                      <span className="font-bold text-emerald-700">{item.doc_progress_pct}%</span>
                    </div>
                    <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-emerald-600 h-full rounded-full transition-all duration-300"
                        style={{ width: `${item.doc_progress_pct}%` }}
                      />
                    </div>
                  </div>

                  {/* EXPANDABLE SECTION (Checklist, Eligibility & Portals) */}
                  {isExpanded && (
                    <div className="mt-4 pt-3 border-t border-gray-200 space-y-3.5" onClick={e => e.stopPropagation()}>
                      {/* Eligibility Rules */}
                      {item.eligibility_rules?.length > 0 && (
                        <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-3 text-xs space-y-1.5">
                          <p className="font-bold text-emerald-900 uppercase tracking-wide text-[10px]">
                            Eligibility Guidelines:
                          </p>
                          <ul className="space-y-1">
                            {item.eligibility_rules.map((rule, idx) => (
                              <li key={idx} className="flex items-start gap-1.5 text-emerald-950 font-medium">
                                <span className="text-emerald-600 font-bold">•</span>
                                <span>{rule}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* PERSISTENT CHECKLIST */}
                      <div className="bg-white rounded-xl border border-gray-200 p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-bold text-gray-800">
                            Required Documents Checklist (ದಾಖಲೆಗಳ ಪರಿಶೀಲನೆ):
                          </p>
                          <span className="text-[10px] text-gray-400">Click to check off</span>
                        </div>
                        <div className="space-y-1.5">
                          {item.checklist.map(doc => {
                            const isItemLoading = toggleLoadingKey === `${item.id}_${doc.doc_key}`
                            return (
                              <div
                                key={doc.id}
                                onClick={(e) => handleToggleDoc(item.id, doc.doc_key, doc.is_completed, e)}
                                className={`flex items-center justify-between p-2 rounded-lg border text-xs transition-colors cursor-pointer ${
                                  doc.is_completed
                                    ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                                    : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                                }`}
                              >
                                <div className="flex items-center gap-2">
                                  {isItemLoading ? (
                                    <div className="w-4 h-4 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
                                  ) : doc.is_completed ? (
                                    <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                                  ) : (
                                    <Circle className="w-4 h-4 text-gray-300 flex-shrink-0" />
                                  )}
                                  <div>
                                    <div className={`font-semibold ${doc.is_completed ? 'line-through text-emerald-900' : 'text-gray-800'}`}>
                                      {doc.doc_name}
                                    </div>
                                    {doc.doc_name_kannada && (
                                      <div className="text-[10px] text-gray-500">{doc.doc_name_kannada}</div>
                                    )}
                                  </div>
                                </div>
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm ${
                                  doc.is_completed ? 'bg-emerald-200 text-emerald-900' : 'bg-gray-200 text-gray-600'
                                }`}>
                                  {doc.is_completed ? 'READY' : 'PENDING'}
                                </span>
                              </div>
                            )
                          })}
                        </div>
                      </div>

                      {/* Official Authority & External Action Link */}
                      <div className="flex items-center justify-between text-xs pt-1">
                        <div className="text-gray-500 text-[11px] truncate max-w-[190px]">
                          {item.authority}
                        </div>
                        {item.portal_url && (
                          <a
                            href={item.portal_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 font-bold text-emerald-700 hover:text-emerald-800 hover:underline"
                          >
                            Apply on Portal <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>

                      {item.helpline && (
                        <div className="flex items-center gap-1.5 text-xs text-gray-600 bg-gray-50 p-2 rounded-lg">
                          <Phone className="w-3.5 h-3.5 text-emerald-700" />
                          <span>Helpline: <strong>{item.helpline}</strong></span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Expand toggle hint */}
                  <div className="mt-2 text-center">
                    <span className="text-[10px] font-semibold text-gray-400 flex items-center justify-center gap-0.5 hover:text-gray-600">
                      {isExpanded ? (
                        <>Hide Details <ChevronUp className="w-3 h-3" /></>
                      ) : (
                        <>View Checklist & Guidelines <ChevronDown className="w-3 h-3" /></>
                      )}
                    </span>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
          <span>Karnataka Agriculture Official Notifications</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-800 text-white rounded-xl text-xs font-semibold hover:bg-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
