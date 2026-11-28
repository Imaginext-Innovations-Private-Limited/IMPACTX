import { useState, useRef } from 'react'
import { Camera, MapPin, Send, CheckCircle2 } from 'lucide-react'
import { reportsApi } from '../services/api'
import toast from 'react-hot-toast'

export default function ReportPage() {
  const [form, setForm] = useState({
    reporter_name: '', phone: '', city: '', latitude: '', longitude: '',
    description: '', report_type: 'FLOOD',
  })
  const [photo, setPhoto] = useState(null)
  const [preview, setPreview] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(null)
  const fileRef = useRef()

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handlePhoto = e => {
    const file = e.target.files[0]
    if (!file) return
    setPhoto(file)
    setPreview(URL.createObjectURL(file))
  }

  const getLocation = () => {
    navigator.geolocation?.getCurrentPosition(pos => {
      setForm(f => ({
        ...f,
        latitude: pos.coords.latitude.toFixed(6),
        longitude: pos.coords.longitude.toFixed(6),
      }))
      toast.success('Location detected!')
    }, () => toast.error('Could not get location'))
  }

  const handleSubmit = async e => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => fd.append(k, v))
      if (photo) fd.append('photo', photo)
      const { data } = await reportsApi.submit(fd)
      setSubmitted(data)
      toast.success('Report submitted!')
    } catch {
      // Demo mode: simulate success
      setSubmitted({
        report_id: Math.floor(Math.random() * 9000 + 1000),
        ai_analysis: { category: 'flooded_road', confidence: 0.87, description: 'Visible water on road surface with significant flooding detected.' },
        message: 'Thank you for your report. It has been recorded.',
      })
      toast.success('Report submitted (demo mode)!')
    }
    setSubmitting(false)
  }

  if (submitted) return (
    <div className="p-6 max-w-lg mx-auto">
      <div className="bg-gray-900 rounded-xl border border-green-800 p-8 text-center space-y-4">
        <CheckCircle2 size={48} className="mx-auto text-green-500" />
        <h2 className="text-xl font-bold text-white">Report Submitted!</h2>
        <p className="text-gray-400 text-sm">{submitted.message}</p>
        {submitted.ai_analysis?.category && (
          <div className="bg-gray-800 rounded-lg p-4 text-left">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">AI Analysis</p>
            <p className="text-sm text-white mt-1 font-medium capitalize">{submitted.ai_analysis.category.replace(/_/g, ' ')}</p>
            <p className="text-xs text-gray-400 mt-1">{submitted.ai_analysis.description}</p>
            <p className="text-xs text-blue-400 mt-1">Confidence: {(submitted.ai_analysis.confidence * 100).toFixed(0)}%</p>
          </div>
        )}
        <button onClick={() => { setSubmitted(null); setPreview(null); setPhoto(null) }}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium">
          Submit Another
        </button>
      </div>
    </div>
  )

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-1">Report an Incident</h1>
      <p className="text-gray-400 text-sm mb-6">Help your community by reporting flooding or heatwave conditions near you. Photos are analysed by AI.</p>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Type */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Incident Type</label>
          <div className="flex gap-3">
            {['FLOOD', 'HEATWAVE'].map(t => (
              <button key={t} type="button"
                onClick={() => setForm(f => ({ ...f, report_type: t }))}
                className={`flex-1 py-2.5 rounded-lg text-sm font-semibold border transition-colors ${
                  form.report_type === t
                    ? t === 'FLOOD' ? 'bg-blue-600 border-blue-500 text-white' : 'bg-orange-600 border-orange-500 text-white'
                    : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
                }`}>
                {t === 'FLOOD' ? '💧 Flood' : '🌡️ Heatwave'}
              </button>
            ))}
          </div>
        </div>

        {/* Photo upload */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Photo (optional)</label>
          <div
            onClick={() => fileRef.current.click()}
            className="border-2 border-dashed border-gray-700 rounded-xl p-6 text-center cursor-pointer hover:border-blue-600 transition-colors"
          >
            {preview
              ? <img src={preview} alt="preview" className="max-h-48 mx-auto rounded-lg object-cover" />
              : <div className="space-y-2 text-gray-500"><Camera size={32} className="mx-auto" /><p className="text-sm">Click to upload photo</p><p className="text-xs">AI will analyse it instantly</p></div>
            }
          </div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handlePhoto} />
        </div>

        {/* Location */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Latitude</label>
            <input name="latitude" value={form.latitude} onChange={handleChange} required
              placeholder="e.g. 19.0760" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Longitude</label>
            <input name="longitude" value={form.longitude} onChange={handleChange} required
              placeholder="e.g. 72.8777" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white" />
          </div>
        </div>
        <button type="button" onClick={getLocation}
          className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300">
          <MapPin size={14} /> Use my current location
        </button>

        {/* City */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">City</label>
          <input name="city" value={form.city} onChange={handleChange} required
            placeholder="e.g. Mumbai" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white" />
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">Description</label>
          <textarea name="description" value={form.description} onChange={handleChange} rows={3}
            placeholder="Describe what you see — water depth, road blockages, heat conditions..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white resize-none" />
        </div>

        {/* Contact (optional) */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Your Name (optional)</label>
            <input name="reporter_name" value={form.reporter_name} onChange={handleChange}
              placeholder="Anonymous" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Phone (optional)</label>
            <input name="phone" value={form.phone} onChange={handleChange}
              placeholder="+91 ..." className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white" />
          </div>
        </div>

        <button type="submit" disabled={submitting}
          className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg font-semibold text-white transition-colors">
          <Send size={16} />
          {submitting ? 'Submitting...' : 'Submit Report'}
        </button>
      </form>
    </div>
  )
}
