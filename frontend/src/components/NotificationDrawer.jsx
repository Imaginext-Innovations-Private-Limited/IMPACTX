import React, { useState, useEffect, useMemo } from 'react'
import {
  X, Bell, CheckCircle2, Circle, Clock, ExternalLink, Phone,
  CheckSquare, ChevronDown, ChevronUp
} from 'lucide-react'
import { schemesApi } from '../api/client'
import { useLocation } from '../context/LocationContext'
import { useI18n } from '../context/I18nContext'

const DRAWER_I18N = {
  en: {
    title: 'Scheme & Relief Alerts',
    subtitle: 'Schemes, Subsidies & Relief Notifications',
    markAllRead: 'Mark all read',
    all: 'All Alerts',
    fellowships: 'Fellowships',
    subsidies: 'Subsidies',
    insurance: 'Insurance',
    drought: 'Drought/Relief',
    loading: 'Loading official notifications…',
    empty: 'No active alerts for this category',
    benefit: 'Benefit',
    deadline: 'Deadline',
    docsReady: 'Documents Ready',
    checklistTitle: 'Required Documents Checklist',
    clickCheck: 'Click to check off',
    ready: 'READY',
    pending: 'PENDING',
    applyPortal: 'Apply on Portal',
    helpline: 'Helpline',
    hideDetails: 'Hide Details',
    viewDetails: 'View Checklist & Guidelines',
    close: 'Close',
    daysLeft: 'days left',
    footerSuffix: 'Agriculture Official Notifications',
  },
  hi: {
    title: 'योजना और राहत अलर्ट',
    subtitle: 'योजनाएं, सब्सिडी और राहत सूचनाएं',
    markAllRead: 'सभी को पढ़ा हुआ चिह्नित करें',
    all: 'सभी अलर्ट',
    fellowships: 'फ़ेलोशिप',
    subsidies: 'सब्सिडी',
    insurance: 'फसल बीमा',
    drought: 'सूखा/राहत',
    loading: 'आधिकारिक सूचनाएं लोड हो रही हैं…',
    empty: 'इस श्रेणी के लिए कोई सक्रिय अलर्ट नहीं',
    benefit: 'लाभ',
    deadline: 'अंतिम तिथि',
    docsReady: 'तैयार दस्तावेज़',
    checklistTitle: 'आवश्यक दस्तावेज़ सूची',
    clickCheck: 'चुनने के लिए क्लिक करें',
    ready: 'तैयार',
    pending: 'लंबित',
    applyPortal: 'पोर्टल पर आवेदन करें',
    helpline: 'हेल्पलाइन',
    hideDetails: 'विवरण छिपाएं',
    viewDetails: 'दस्तावेज़ सूची और विवरण देखें',
    close: 'बंद करें',
    daysLeft: 'दिन शेष',
    footerSuffix: 'कृषि आधिकारिक सूचनाएं',
  },
  kn: {
    title: 'ಯೋಜನೆ ಮತ್ತು ಪರಿಹಾರ ಅಧಿಸೂಚನೆಗಳು',
    subtitle: 'ಯೋಜನೆ, ಸಬ್ಸಿಡಿ ಮತ್ತು ಪರಿಹಾರ ಅಧಿಸೂಚನೆಗಳು',
    markAllRead: 'ಎಲ್ಲವನ್ನೂ ಓದಲಾಗಿದೆ ಎಂದು ಗುರುತಿಸಿ',
    all: 'ಎಲ್ಲಾ ಅಧಿಸೂಚನೆಗಳು',
    fellowships: 'ಫೆಲೋಶಿಪ್‌ಗಳು',
    subsidies: 'ಸಬ್ಸಿಡಿಗಳು',
    insurance: 'ಬೆಳೆ ವಿಮೆ',
    drought: 'ಬರ/ಪರಿಹಾರ',
    loading: 'ಅಧಿಕೃತ ಅಧಿಸೂಚನೆಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ…',
    empty: 'ಈ ವರ್ಗಕ್ಕೆ ಯಾವುದೇ ಸಕ್ರಿಯ ಅಧಿಸೂಚನೆಗಳಿಲ್ಲ',
    benefit: 'ಪ್ರಯೋಜನ',
    deadline: 'ಕೊನೆಯ ದಿನಾಂಕ',
    docsReady: 'ದಾಖಲೆಗಳು ಸಿದ್ಧ',
    checklistTitle: 'ಅಗತ್ಯ ದಾಖಲೆಗಳ ಪರಿಶೀಲನಾ ಪಟ್ಟಿ',
    clickCheck: 'ಗುರುತಿಸಲು ಕ್ಲಿಕ್ ಮಾಡಿ',
    ready: 'ಸಿದ್ಧ',
    pending: 'ಬಾಕಿ',
    applyPortal: 'ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ',
    helpline: 'ಸಹಾಯವಾಣಿ',
    hideDetails: 'ವಿವರಗಳನ್ನು ಮರೆಮಾಡಿ',
    viewDetails: 'ದಾಖಲೆ ಪಟ್ಟಿ ಮತ್ತು ಮಾರ್ಗಸೂಚಿ ನೋಡಿ',
    close: 'ಮುಚ್ಚಿ',
    daysLeft: 'ದಿನಗಳು ಬಾಕಿ',
    footerSuffix: 'ಕೃಷಿ ಅಧಿಕೃತ ಅಧಿಸೂಚನೆಗಳು',
  },
  te: {
    title: 'పథకాలు & సహాయక హెచ్చరికలు',
    subtitle: 'పథకాలు, సబ్సిడీలు & సహాయక సమాచారం',
    markAllRead: 'అన్నీ చదివినట్లు గుర్తించు',
    all: 'అన్ని హెచ్చరికలు',
    fellowships: 'ఫెలోషిప్‌లు',
    subsidies: 'సబ్సిడీలు',
    insurance: 'పంట బీమా',
    drought: 'కరువు/సహాయం',
    loading: 'అధికారిక ప్రకటనలు లోడ్ అవుతున్నాయి…',
    empty: 'ఈ విభాగంలో చురుకైన హెచ్చరికలు లేవు',
    benefit: 'ప్రయోజనం',
    deadline: 'చివరి తేదీ',
    docsReady: 'పత్రాలు సిద్ధం',
    checklistTitle: 'అవసరమైన పత్రాల జాబితా',
    clickCheck: 'టిక్ చేయడానికి క్లిక్ చేయండి',
    ready: 'సిద్ధం',
    pending: 'పెండింగ్',
    applyPortal: 'పోర్టల్‌లో దరఖాస్తు చేయండి',
    helpline: 'హెల్ప్‌లైన్',
    hideDetails: 'వివరాలు దాచు',
    viewDetails: 'పత్రాల జాబితా & మార్గదర్శకాలు చూడండి',
    close: 'మూసివేయండి',
    daysLeft: 'రోజులు మిగిలాయి',
    footerSuffix: 'వ్యవసాయ అధికారిక ప్రకటనలు',
  },
  ta: {
    title: 'திட்டங்கள் & நிவாரண அறிவிப்புகள்',
    subtitle: 'திட்டங்கள், மானியங்கள் & நிவாரணத் தகவல்கள்',
    markAllRead: 'அனைத்தையும் படித்ததாகக் குறி',
    all: 'அனைத்தும்',
    fellowships: 'உதவித்தொகை',
    subsidies: 'மானியங்கள்',
    insurance: 'பயிர் காப்பீடு',
    drought: 'வறட்சி/நிவாரணம்',
    loading: 'அதிகாரப்பூர்வ அறிவிப்புகள் ஏற்றப்படுகின்றன…',
    empty: 'இந்தப் பிரிவில் செயலில் உள்ள அறிவிப்புகள் இல்லை',
    benefit: 'பயன்',
    deadline: 'கடைசி தேதி',
    docsReady: 'ஆவணங்கள் தயார்',
    checklistTitle: 'தேவையான ஆவணங்கள் பட்டியல்',
    clickCheck: 'குறிக்க கிளிக் செய்யவும்',
    ready: 'தயார்',
    pending: 'நிலுவையில்',
    applyPortal: 'போர்ட்டலில் விண்ணப்பிக்கவும்',
    helpline: 'உதவி எண்',
    hideDetails: 'விவரங்களை மறை',
    viewDetails: 'ஆவணப் பட்டியல் & வழிகாட்டுதல்கள்',
    close: 'மூடு',
    daysLeft: 'நாட்கள் உள்ளன',
    footerSuffix: 'வேளாண்மை அதிகாரப்பூர்வ அறிவிப்புகள்',
  },
  mr: {
    title: 'योजना व मदत सूचना',
    subtitle: 'योजना, अनुदान आणि मदत अधिसूचना',
    markAllRead: 'सर्व वाचलेले चिन्हांकित करा',
    all: 'सर्व सूचना',
    fellowships: 'फेलोशिप',
    subsidies: 'अनुदान',
    insurance: 'पीक विमा',
    drought: 'दुष्काळ/मदत',
    loading: 'अधिकृत सूचना लोड होत आहेत…',
    empty: 'या श्रेणीसाठी कोणतीही सक्रिय सूचना नाही',
    benefit: 'लाभ',
    deadline: 'अंतिम तारीख',
    docsReady: 'कागदपत्रे तयार',
    checklistTitle: 'आवश्यक कागदपत्रे यादी',
    clickCheck: 'निवडण्यासाठी क्लिक करा',
    ready: 'तयार',
    pending: 'प्रलंबित',
    applyPortal: 'पोर्टलवर अर्ज करा',
    helpline: 'हेल्पलाइन',
    hideDetails: 'तपशील लपवा',
    viewDetails: 'कागदपत्रे यादी व मार्गदर्शक तत्त्वे पहा',
    close: 'बंद करा',
    daysLeft: 'दिवस शिल्लक',
    footerSuffix: 'कृषी अधिकृत सूचना',
  },
  ml: {
    title: 'പദ്ധതി & ദുരിതാശ്വാസ അറിയിപ്പുകൾ',
    subtitle: 'പദ്ധതികൾ, സബ്സിഡികൾ & ദുരിതാശ്വാസ മുന്നറിയിപ്പുകൾ',
    markAllRead: 'എല്ലാം വായിച്ചതായി അടയാളപ്പെടുത്തുക',
    all: 'എല്ലാ അറിയിപ്പുകളും',
    fellowships: 'ഫെല്ലോഷിപ്പുകൾ',
    subsidies: 'സബ്സിഡികൾ',
    insurance: 'വിള ഇൻഷുറൻസ്',
    drought: 'വരൾച്ച/ദുരിതാശ്വാസം',
    loading: 'ഔദ്യോഗിക അറിയിപ്പുകൾ ലോഡ് ചെയ്യുന്നു…',
    empty: 'ഈ വിഭാഗത്തിൽ സജീവ അറിയിപ്പുകളില്ല',
    benefit: 'ആനുകൂല്യം',
    deadline: 'അവസാന തീയതി',
    docsReady: 'രേഖകൾ തയ്യാർ',
    checklistTitle: 'ആവശ്യമായ രേഖകളുടെ പട്ടിക',
    clickCheck: 'അടയാളപ്പെടുത്താൻ ക്ലിക്ക് ചെയ്യുക',
    ready: 'തയ്യാർ',
    pending: 'ബാക്കിയുണ്ട്',
    applyPortal: 'പോർട്ടലിൽ അപേക്ഷിക്കുക',
    helpline: 'ഹെൽപ്പ്‌ലൈൻ',
    hideDetails: 'വിവരങ്ങൾ മറയ്ക്കുക',
    viewDetails: 'രേഖകളുടെ പട്ടികയും നിർദ്ദേശങ്ങളും കാണുക',
    close: 'അടയ്ക്കുക',
    daysLeft: 'ദിവസം ബാക്കി',
    footerSuffix: 'കാർഷിക ഔദ്യോഗിക അറിയിപ്പുകൾ',
  },
  bn: {
    title: 'প্রকল্প ও ত্রাণ সতর্কতা',
    subtitle: 'প্রকল্প, ভর্তুকি ও ত্রাণ বিজ্ঞপ্তি',
    markAllRead: 'সবগুলো পঠিত হিসেবে চিহ্নित করুন',
    all: 'সব সতর্কতা',
    fellowships: 'ফেলোশিপ',
    subsidies: 'ভর্তুকি',
    insurance: 'ফসল বীমা',
    drought: 'খরা/ত্রাণ',
    loading: 'সরকারি বিজ্ঞপ্তি লোড হচ্ছে…',
    empty: 'এই বিভাগে কোনো সক্রিয় সতর্কতা নেই',
    benefit: 'সুবিধা',
    deadline: 'শেষ তারিখ',
    docsReady: 'নথি প্রস্তুত',
    checklistTitle: 'প্রয়োজনীয় নথির তালিকা',
    clickCheck: 'টিক দিতে ক্লিক করুন',
    ready: 'প্রস্তুত',
    pending: 'বাকি',
    applyPortal: 'পোর্টালে আবেদন করুন',
    helpline: 'হেল্পলাইন',
    hideDetails: 'বিবরণ লুকান',
    viewDetails: 'নথির তালিকা ও নির্দেশিকা দেখুন',
    close: 'বন্ধ করুন',
    daysLeft: 'দিন বাকি',
    footerSuffix: 'কৃষি সরকারি বিজ্ঞপ্তি',
  },
  gu: {
    title: 'યોજના અને રાહત ચેતવણીઓ',
    subtitle: 'યોજનાઓ, સબસિડી અને રાહત સૂચનાઓ',
    markAllRead: 'બધું વાંચેલું ચિહ્નિત કરો',
    all: 'બધી ચેતવણીઓ',
    fellowships: 'ફેલોશિપ',
    subsidies: 'સબસિડી',
    insurance: 'પાક વીમો',
    drought: 'દુષ્કાળ/રાહત',
    loading: 'સત્તાવાર સૂચનાઓ લોડ થઈ રહી છે…',
    empty: 'આ શ્રેણી માટે કોઈ સક્રિય ચેતવણી નથી',
    benefit: 'લાભ',
    deadline: 'અંતિમ તારીખ',
    docsReady: 'દસ્તાવેજો તૈયાર',
    checklistTitle: 'જરૂરી દસ્તાવેજોની યાદી',
    clickCheck: 'પસંદ કરવા ક્લિક કરો',
    ready: 'તૈયાર',
    pending: 'બાકી',
    applyPortal: 'પોર્ટલ પર અરજી કરો',
    helpline: 'હેલ્પલાઇન',
    hideDetails: 'વિગતો છુપાવો',
    viewDetails: 'દસ્તાવેજ યાદી અને માર્ગદર્શિકા જુઓ',
    close: 'બંધ કરો',
    daysLeft: 'દિવસ બાકી',
    footerSuffix: 'કૃષિ સત્તાવાર સૂચનાઓ',
  },
  pa: {
    title: 'ਸਕੀਮ ਅਤੇ ਰਾਹਤ ਅਲਰਟ',
    subtitle: 'ਸਕੀਮਾਂ, ਸਬਸਿਡੀਆਂ ਅਤੇ ਰਾਹਤ ਸੂਚਨਾਵਾਂ',
    markAllRead: 'ਸਭ ਪੜ੍ਹੇ ਹੋਏ ਮਾਰਕ ਕਰੋ',
    all: 'ਸਾਰੇ ਅਲਰਟ',
    fellowships: 'ਫੈਲੋਸ਼ਿਪ',
    subsidies: 'ਸਬਸਿਡੀਆਂ',
    insurance: 'ਫਸਲ ਬੀਮਾ',
    drought: 'ਸੋਕਾ/ਰਾਹਤ',
    loading: 'ਅਧਿਕਾਰਤ ਸੂਚਨਾਵਾਂ ਲੋਡ ਹੋ ਰਹੀਆਂ ਹਨ…',
    empty: 'ਇਸ ਸ਼੍ਰੇਣੀ ਲਈ ਕੋਈ ਸਰਗਰਮ ਅਲਰਟ ਨਹੀਂ',
    benefit: 'ਲਾਭ',
    deadline: 'ਆਖਰੀ ਮਿਤੀ',
    docsReady: 'ਦਸਤਾਵੇਜ਼ ਤਿਆਰ',
    checklistTitle: 'ਲੋੜੀਂਦੇ ਦਸਤਾਵੇਜ਼ਾਂ ਦੀ ਸੂਚੀ',
    clickCheck: 'ਚੁਣਨ ਲਈ ਕਲਿੱਕ ਕਰੋ',
    ready: 'ਤਿਆਰ',
    pending: 'ਬਾਕੀ',
    applyPortal: 'ਪੋਰਟਲ ਤੇ ਅਰਜ਼ੀ ਦਿਓ',
    helpline: 'ਹੈਲਪਲਾਈਨ',
    hideDetails: 'ਵੇਰਵੇ ਲੁਕਾਓ',
    viewDetails: 'ਦਸਤਾਵੇਜ਼ ਸੂਚੀ ਅਤੇ ਦਿਸ਼ਾ-ਨਿਰਦੇਸ਼ ਦੇਖੋ',
    close: 'ਬੰਦ ਕਰੋ',
    daysLeft: 'ਦਿਨ ਬਾਕੀ',
    footerSuffix: 'ਖੇਤੀਬਾੜੀ ਅਧਿਕਾਰਤ ਸੂਚਨਾਵਾਂ',
  },
}

export default function NotificationDrawer({ isOpen, onClose, onUnreadCountChange }) {
  const { location } = useLocation()
  const { language } = useI18n()

  const state = location?.state || 'Karnataka'
  const district = location?.district || ''
  const location_name = location?.location_name || location?.name || ''

  const shortLang = (language || 'en').split('-')[0].toLowerCase()
  const labels = useMemo(() => DRAWER_I18N[shortLang] || DRAWER_I18N.en, [shortLang])
  const langParam = language && !language.includes('-') ? `${language}-IN` : (language || 'en-IN')

  const [activeCategory, setActiveCategory] = useState('all')
  const [schemes, setSchemes] = useState([])
  const [resolvedState, setResolvedState] = useState(state)
  const [readIds, setReadIds] = useState({})
  const [checkedDocs, setCheckedDocs] = useState({})
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    if (isOpen) {
      setLoading(true)
    }

    schemesApi.getSchemes(
      { state, district, location_name, category: activeCategory, language: langParam },
      controller.signal
    )
      .then(res => {
        const list = res.data.schemes || []
        setSchemes(list)
        setResolvedState(res.data.state || state)
        const unread = list.filter(item => !readIds[item.id]).length
        if (onUnreadCountChange) onUnreadCountChange(unread)
        setLoading(false)
      })
      .catch(() => {
        setLoading(false)
      })

    return () => controller.abort()
  }, [isOpen, activeCategory, state, district, location_name, language])

  const unreadCount = useMemo(
    () => schemes.filter(item => !readIds[item.id]).length,
    [schemes, readIds]
  )

  const handleMarkRead = (id) => {
    setReadIds(prev => {
      if (prev[id]) return prev
      const next = { ...prev, [id]: true }
      const newUnread = schemes.filter(item => !next[item.id]).length
      if (onUnreadCountChange) onUnreadCountChange(newUnread)
      return next
    })
  }

  const handleMarkAllRead = () => {
    const next = { ...readIds }
    schemes.forEach(item => { next[item.id] = true })
    setReadIds(next)
    if (onUnreadCountChange) onUnreadCountChange(0)
  }

  const handleToggleDoc = (schemeId, docName, e) => {
    e.stopPropagation()
    const key = `${schemeId}::${docName}`
    setCheckedDocs(prev => ({ ...prev, [key]: !prev[key] }))
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs transition-opacity">
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
              <h2 className="text-sm sm:text-base font-bold leading-tight">{labels.title}</h2>
              <p className="text-[11px] text-emerald-200">{labels.subtitle}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-[11px] bg-white/10 hover:bg-white/20 text-emerald-100 px-2 py-1 rounded-lg transition-colors font-medium"
              >
                {labels.markAllRead}
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
            { id: 'all', label: labels.all },
            { id: 'fellowships', label: labels.fellowships },
            { id: 'subsidies', label: labels.subsidies },
            { id: 'insurance', label: labels.insurance },
            { id: 'drought', label: labels.drought },
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
              <p className="text-xs">{labels.loading}</p>
            </div>
          ) : schemes.length === 0 ? (
            <div className="text-center py-16 text-gray-400 space-y-2">
              <Bell className="w-8 h-8 text-gray-300 mx-auto" />
              <p className="text-sm font-semibold text-gray-600">{labels.empty}</p>
            </div>
          ) : (
            schemes.map(item => {
              const isExpanded = expandedId === item.id
              const isRead = !!readIds[item.id]
              const docs = item.documents_required || []
              const completedDocs = docs.filter(d => checkedDocs[`${item.id}::${d}`]).length
              const docPct = docs.length > 0 ? Math.round((completedDocs / docs.length) * 100) : 0

              return (
                <div
                  key={item.id}
                  onClick={() => {
                    setExpandedId(isExpanded ? null : item.id)
                    if (!isRead) handleMarkRead(item.id)
                  }}
                  className={`rounded-2xl border transition-all cursor-pointer p-4 ${
                    !isRead
                      ? 'bg-emerald-50/50 border-emerald-300 ring-1 ring-emerald-200 shadow-xs'
                      : 'bg-white border-gray-200 hover:border-gray-300 shadow-xs'
                  }`}
                >
                  {/* Top tags row */}
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                        item.category === 'drought'
                          ? 'bg-rose-100 text-rose-800 border-rose-200'
                          : item.category === 'subsidies'
                          ? 'bg-amber-100 text-amber-800 border-amber-200'
                          : item.category === 'insurance'
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-purple-100 text-purple-800 border-purple-200'
                      }`}>
                        {item.category}
                      </span>
                      {!isRead && (
                        <span className="w-2 h-2 rounded-full bg-emerald-600" title="Unread" />
                      )}
                    </div>

                    <div className="flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                      <Clock className="w-3 h-3 text-rose-600" />
                      <span>{item.days_left} {labels.daysLeft}</span>
                    </div>
                  </div>

                  {/* Title */}
                  <h3 className="font-bold text-gray-900 text-sm leading-snug">
                    {item.title}
                  </h3>
                  {item.localized_title && item.localized_title !== item.title && (
                    <p className="text-xs font-semibold text-emerald-900 mt-0.5">
                      {item.localized_title}
                    </p>
                  )}

                  {/* Description */}
                  <p className="text-xs text-gray-600 mt-2 line-clamp-2 leading-relaxed">
                    {item.description}
                  </p>

                  {/* Benefit & Deadline */}
                  <div className="mt-3 flex items-center justify-between bg-gray-50 p-2 rounded-xl text-xs">
                    <div>
                      <span className="text-[10px] font-bold text-gray-400 uppercase">{labels.benefit}</span>
                      <p className="font-bold text-emerald-700">{item.benefit}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] font-bold text-gray-400 uppercase">{labels.deadline}</span>
                      <p className="font-semibold text-gray-700">{item.deadline}</p>
                    </div>
                  </div>

                  {/* Required Documents Progress Bar */}
                  <div className="mt-3 pt-2.5 border-t border-gray-100">
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <span className="font-semibold text-gray-700 flex items-center gap-1">
                        <CheckSquare className="w-3.5 h-3.5 text-emerald-600" />
                        {labels.docsReady}: {completedDocs}/{docs.length}
                      </span>
                      <span className="font-bold text-emerald-700">{docPct}%</span>
                    </div>
                    <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-emerald-600 h-full rounded-full transition-all duration-300"
                        style={{ width: `${docPct}%` }}
                      />
                    </div>
                  </div>

                  {/* EXPANDABLE SECTION */}
                  {isExpanded && (
                    <div className="mt-4 pt-3 border-t border-gray-200 space-y-3.5" onClick={e => e.stopPropagation()}>
                      {/* Checklist */}
                      <div className="bg-white rounded-xl border border-gray-200 p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-bold text-gray-800">{labels.checklistTitle}:</p>
                          <span className="text-[10px] text-gray-400">{labels.clickCheck}</span>
                        </div>
                        <div className="space-y-1.5">
                          {docs.map(docName => {
                            const isChecked = !!checkedDocs[`${item.id}::${docName}`]
                            return (
                              <div
                                key={docName}
                                onClick={(e) => handleToggleDoc(item.id, docName, e)}
                                className={`flex items-center justify-between p-2 rounded-lg border text-xs transition-colors cursor-pointer ${
                                  isChecked
                                    ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                                    : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                                }`}
                              >
                                <div className="flex items-center gap-2">
                                  {isChecked ? (
                                    <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                                  ) : (
                                    <Circle className="w-4 h-4 text-gray-300 flex-shrink-0" />
                                  )}
                                  <span className={`font-semibold ${isChecked ? 'line-through text-emerald-900' : 'text-gray-800'}`}>
                                    {docName}
                                  </span>
                                </div>
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-sm ${
                                  isChecked ? 'bg-emerald-200 text-emerald-900' : 'bg-gray-200 text-gray-600'
                                }`}>
                                  {isChecked ? labels.ready : labels.pending}
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
                            {labels.applyPortal} <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>

                      {item.helpline && (
                        <div className="flex items-center gap-1.5 text-xs text-gray-600 bg-gray-50 p-2 rounded-lg">
                          <Phone className="w-3.5 h-3.5 text-emerald-700" />
                          <span>{labels.helpline}: <strong>{item.helpline}</strong></span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Expand toggle hint */}
                  <div className="mt-2 text-center">
                    <span className="text-[10px] font-semibold text-gray-400 flex items-center justify-center gap-0.5 hover:text-gray-600">
                      {isExpanded ? (
                        <>{labels.hideDetails} <ChevronUp className="w-3 h-3" /></>
                      ) : (
                        <>{labels.viewDetails} <ChevronDown className="w-3 h-3" /></>
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
          <span>{resolvedState} {labels.footerSuffix}</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-800 text-white rounded-xl text-xs font-semibold hover:bg-gray-700"
          >
            {labels.close}
          </button>
        </div>
      </div>
    </div>
  )
}
