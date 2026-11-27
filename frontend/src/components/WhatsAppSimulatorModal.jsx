import React, { useState, useRef, useEffect } from 'react'
import {
  MessageSquare, Send, Mic, MicOff, Camera, Image as ImageIcon,
  Play, Pause, Volume2, Bot, User, CheckCircle, AlertCircle, RefreshCw, X, Sparkles
} from 'lucide-react'
import { whatsappApi } from '../api/client'

const SAMPLE_CHATS = [
  { label: 'Paddy Price', type: 'text', text: "What is today's paddy price in Davangere APMC?" },
  { label: 'Areca Advisory', type: 'text', text: 'ಅಡಿಕೆ ತೋಟಕ್ಕೆ ಈಗ ಯಾವ ಗೊಬ್ಬರ ಹಾಕಬೇಕು?' },
  { label: 'Voice Note (ಧ್ವನಿ)', type: 'audio', text: 'ಭತ್ತದ ರೋಗದ ಬಗ್ಗೆ ಸಲಹೆ ನೀಡಿ' },
  { label: 'Leaf Blight Photo', type: 'image', caption: 'Leaf spots disease on tomato', sample: '/samples/sample_leaf_blight.jpg' },
  { label: 'Fertilizer Bottle', type: 'image', caption: 'Check fertilizer dosage per acre', sample: '/samples/sample_pesticide.jpg' },
  { label: 'Soil Sample', type: 'image', caption: 'Red laterite soil sample test', sample: '/samples/sample_soil.jpg' },
]

export default function WhatsAppSimulatorModal({ isOpen, onClose }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'bot',
      text: '🌿 *Namaskara! Welcome to KrishiMitra WhatsApp Advisory.*\n\nSend a text query, voice note, or crop/fertilizer photo for instant advisory in Kannada or English.',
      time: 'Just now',
    }
  ])
  const [inputText, setInputText] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeAudioId, setActiveAudioId] = useState(null)
  const [isSimulatedRecording, setIsSimulatedRecording] = useState(false)

  const messagesEndRef = useRef(null)
  const audioPlayerRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (!isOpen) return null

  const handlePlayAudio = (msgId, base64Audio) => {
    if (activeAudioId === msgId) {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
      }
      setActiveAudioId(null)
      return
    }

    try {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
      }
      const audioUrl = base64Audio.startsWith('data:')
        ? base64Audio
        : `data:audio/wav;base64,${base64Audio}`
      const audio = new Audio(audioUrl)
      audioPlayerRef.current = audio
      setActiveAudioId(msgId)
      audio.onended = () => setActiveAudioId(null)
      audio.onerror = () => setActiveAudioId(null)
      audio.play().catch(() => setActiveAudioId(null))
    } catch {
      setActiveAudioId(null)
    }
  }

  const handleSendMessage = async (payloadOverride = null) => {
    const textToSend = payloadOverride ? (payloadOverride.text || payloadOverride.caption || '') : inputText.trim()
    if (!textToSend && !payloadOverride) return

    const userMsgId = 'user_' + Date.now()
    const newMsg = {
      id: userMsgId,
      sender: 'user',
      type: payloadOverride?.type || 'text',
      text: textToSend,
      caption: payloadOverride?.caption,
      imagePreview: payloadOverride?.imagePreview,
      isAudio: payloadOverride?.type === 'audio',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages(prev => [...prev, newMsg])
    if (!payloadOverride) setInputText('')
    setLoading(true)

    try {
      let apiPayload = {}
      if (payloadOverride) {
        apiPayload = { ...payloadOverride }
      } else {
        apiPayload = {
          type: 'text',
          text: textToSend,
          from: '919876543210',
        }
      }

      const res = await whatsappApi.simulate(apiPayload)
      const data = res.data?.result || {}

      const botMsgId = 'bot_' + Date.now()
      const botMsg = {
        id: botMsgId,
        sender: 'bot',
        type: data.type || 'text',
        text: data.reply_text || 'ಧನ್ಯವಾದಗಳು. ನಿಮ್ಮ ಸಂದೇಶವನ್ನು ಸ್ವೀಕರಿಸಲಾಗಿದೆ.',
        audioBase64: data.reply_audio_base64,
        hasVoice: Boolean(data.voice || data.reply_audio_base64),
        scanResult: data.scan_result,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }

      setMessages(prev => [...prev, botMsg])
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: 'bot_err_' + Date.now(),
          sender: 'bot',
          text: '⚠️ Advisory simulator error. Please verify backend service.',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ])
    } finally {
      setLoading(false)
      setIsSimulatedRecording(false)
    }
  }

  const handlePresetClick = async (preset) => {
    if (preset.type === 'text') {
      handleSendMessage({
        type: 'text',
        text: preset.text,
        from: '919876543210',
      })
    } else if (preset.type === 'audio') {
      setIsSimulatedRecording(true)
      setTimeout(() => {
        handleSendMessage({
          type: 'audio',
          from: '919876543210',
          text: `🎤 Simulated Voice Note (${preset.text})`,
        })
      }, 600)
    } else if (preset.type === 'image') {
      try {
        setLoading(true)
        const fetchRes = await fetch(preset.sample)
        const blob = await fetchRes.blob()
        const reader = new FileReader()
        reader.onloadend = () => {
          const base64Data = reader.result.split(',')[1]
          handleSendMessage({
            type: 'image',
            caption: preset.caption,
            image_base64: base64Data,
            imagePreview: preset.sample,
            from: '919876543210',
          })
        }
        reader.readAsDataURL(blob)
      } catch {
        handleSendMessage({
          type: 'image',
          caption: preset.caption,
          from: '919876543210',
        })
      }
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/60 backdrop-blur-xs">
      <div className="bg-[#EFEAE2] w-full max-w-md h-[92vh] max-h-[720px] rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-300">
        
        {/* Top Bar (WhatsApp Green Header) */}
        <div className="bg-[#075E54] text-white px-3 py-2.5 flex items-center justify-between shadow shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="relative shrink-0">
              <div className="w-9 h-9 rounded-full bg-[#128C7E] flex items-center justify-center text-white border border-white/20">
                <Bot className="w-5 h-5" />
              </div>
              <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-400 border-2 border-[#075E54] rounded-full" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold truncate leading-tight flex items-center gap-1.5">
                KrishiMitra Bot
                <span className="text-[10px] bg-green-600/60 px-1 rounded font-normal">WhatsApp AI</span>
              </h2>
              <p className="text-[10px] text-green-200 truncate leading-tight">Meta Graph API v24.0 · +91 98765 43210</p>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => setMessages([messages[0]])}
              className="p-1.5 hover:bg-white/10 rounded-full text-white/80 hover:text-white transition-colors"
              title="Clear chat"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-white/10 rounded-full text-white/80 hover:text-white transition-colors"
              title="Close simulator"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Quick Sample Presets Tray */}
        <div className="bg-[#f0f2f5] border-b border-gray-200 px-2.5 py-1.5 flex items-center gap-1.5 overflow-x-auto shrink-0">
          <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider shrink-0 flex items-center gap-0.5">
            <Sparkles className="w-3 h-3 text-amber-500" /> Test:
          </span>
          <div className="flex items-center gap-1.5 flex-nowrap">
            {SAMPLE_CHATS.map((sc, idx) => (
              <button
                key={idx}
                onClick={() => handlePresetClick(sc)}
                disabled={loading}
                className="px-2 py-0.5 text-[11px] rounded-full bg-white border border-gray-300 hover:border-green-600 hover:text-green-700 hover:bg-green-50 text-gray-700 whitespace-nowrap transition-colors shrink-0 shadow-2xs font-medium"
              >
                {sc.label}
              </button>
            ))}
          </div>
        </div>

        {/* Chat Messages Body */}
        <div className="flex-1 p-3 overflow-y-auto space-y-2.5">
          {messages.map((m) => {
            const isUser = m.sender === 'user'
            return (
              <div
                key={m.id}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 shadow-xs text-xs leading-relaxed relative ${
                    isUser
                      ? 'bg-[#E7FFDB] text-gray-800 rounded-tr-none'
                      : 'bg-white text-gray-800 rounded-tl-none border border-gray-200'
                  }`}
                >
                  {/* Photo Preview if image message */}
                  {m.imagePreview && (
                    <div className="mb-1.5 rounded overflow-hidden border border-black/10">
                      <img src={m.imagePreview} alt="attachment" className="w-full max-h-36 object-cover" />
                    </div>
                  )}

                  {/* Audio note indicator */}
                  {m.isAudio && (
                    <div className="flex items-center gap-1.5 font-medium text-emerald-800 mb-1">
                      <Mic className="w-3.5 h-3.5 text-emerald-600" />
                      <span>{m.text}</span>
                    </div>
                  )}

                  {/* Message body text */}
                  {!m.isAudio && (
                    <div className="whitespace-pre-wrap font-sans break-words">
                      {m.text}
                    </div>
                  )}

                  {/* Voice reply player */}
                  {m.hasVoice && m.audioBase64 && (
                    <div className="mt-2 pt-2 border-t border-gray-200/80 flex items-center justify-between gap-2 bg-emerald-50/70 p-1.5 rounded-md">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <Volume2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        <span className="text-[10px] font-semibold text-emerald-800 truncate">Spoken Voice Reply (Kannada)</span>
                      </div>
                      <button
                        onClick={() => handlePlayAudio(m.id, m.audioBase64)}
                        className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-[10px] flex items-center gap-1 shrink-0 transition-colors"
                      >
                        {activeAudioId === m.id ? (
                          <><Pause className="w-3 h-3" /> Pause</>
                        ) : (
                          <><Play className="w-3 h-3" /> Play Audio</>
                        )}
                      </button>
                    </div>
                  )}

                  <div className="flex items-center justify-end gap-1 mt-1 text-[9px] text-gray-400">
                    <span>{m.time}</span>
                    {isUser && <CheckCircle className="w-2.5 h-2.5 text-blue-500" />}
                  </div>
                </div>
              </div>
            )
          })}

          {loading && (
            <div className="flex items-center gap-2 text-xs text-gray-500 bg-white border border-gray-200 px-3 py-1.5 rounded-lg max-w-[60%] shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>{isSimulatedRecording ? 'Recording voice note...' : 'KrishiMitra AI is replying…'}</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="bg-[#f0f2f5] px-2.5 py-2 flex items-center gap-2 border-t border-gray-300 shrink-0">
          <button
            type="button"
            onClick={() => handlePresetClick(SAMPLE_CHATS[3])}
            className="p-1.5 text-gray-500 hover:text-green-700 hover:bg-gray-200 rounded-full transition-colors shrink-0"
            title="Send sample leaf image"
          >
            <Camera className="w-5 h-5" />
          </button>
          
          <button
            type="button"
            onClick={() => handlePresetClick(SAMPLE_CHATS[2])}
            className={`p-1.5 rounded-full transition-colors shrink-0 ${
              isSimulatedRecording
                ? 'bg-red-500 text-white animate-pulse'
                : 'text-gray-500 hover:text-green-700 hover:bg-gray-200'
            }`}
            title="Simulate Voice Note"
          >
            <Mic className="w-5 h-5" />
          </button>

          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type WhatsApp message..."
            disabled={loading}
            className="flex-1 bg-white border border-gray-300 rounded-full px-3.5 py-1.5 text-xs text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-green-600 min-w-0"
          />

          <button
            onClick={() => handleSendMessage()}
            disabled={loading || !inputText.trim()}
            className="w-8 h-8 rounded-full bg-[#128C7E] hover:bg-[#075E54] text-white flex items-center justify-center shrink-0 disabled:opacity-40 transition-colors shadow-2xs"
            title="Send"
          >
            <Send className="w-3.5 h-3.5 ml-0.5" />
          </button>
        </div>

      </div>
    </div>
  )
}
