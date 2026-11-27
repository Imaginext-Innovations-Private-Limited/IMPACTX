import React, { useState, useRef, useEffect } from 'react'
import {
  Mic, MicOff, Send, Volume2, VolumeX, Square, X, Loader2,
  MessageCircle, Zap, AlertCircle, RotateCcw, MapPin
} from 'lucide-react'
import { voiceApi } from '../api/client'
import { useI18n, LANGUAGES } from '../context/I18nContext'
import { useLocationContext } from '../context/LocationContext'

const AGRICULTURAL_KEYTERMS = [
  "APMC", "mandi", "paddy", "arecanut", "NPK", "urea",
  "DAP", "fungicide", "blight", "PM-KISAN", "KCC", "acre", "barrel"
]

const LANG_BCP47 = {
  kn: 'kn-IN',
  hi: 'hi-IN',
  ta: 'ta-IN',
  te: 'te-IN',
  mr: 'mr-IN',
  en: 'en-IN',
}

const RECORDING_CAP_SECONDS = 28

const PLACEHOLDERS = {
  kn: 'ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ…',
  hi: 'अपना सवाल टाइप करें…',
  ta: 'உங்கள் கேள்வியை தட்டச்சு செய்யுங்கள்…',
  te: 'మీ ప్రశ్న టైప్ చేయండి…',
  mr: 'तुमचा प्रश्न टाइप करा…',
  en: 'Ask your farming question…',
}

/** Play base64 WAV audio returned by Sarvam TTS */
function playAudioBase64(b64) {
  try {
    const binary = atob(b64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    const blob = new Blob([bytes], { type: 'audio/wav' })
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    audio.onended = () => URL.revokeObjectURL(url)
    audio.play().catch(() => {})
    return audio
  } catch {
    return null
  }
}

/** Browser speech synthesis fallback when TTS audio is not returned */
function speakText(text, langCode) {
  if (!window.speechSynthesis) return false
  const cleanText = (text || '').replace(/[*#_`~>|]/g, '').replace(/\s+/g, ' ').trim()
  if (!cleanText) return false

  const langPrefix = (langCode || 'en').toLowerCase().split('-')[0]
  const voices = window.speechSynthesis.getVoices()
  const matchingVoice = voices.find((v) => v.lang && v.lang.toLowerCase().startsWith(langPrefix))

  if (langPrefix !== 'en' && !matchingVoice) {
    // Never let an English browser voice read Kannada/Indic text
    return false
  }

  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(cleanText)
  utter.lang = LANG_BCP47[langPrefix] || 'en-IN'
  if (matchingVoice) {
    utter.voice = matchingVoice
  }
  utter.rate = 0.92
  window.speechSynthesis.speak(utter)
  return true
}

export default function VoiceAssistant({ initialQuery = null, autoOpen = false }) {
  const [expanded, setExpanded] = useState(autoOpen)
  const { lang, setLang, t } = useI18n()
  const { location } = useLocationContext()
  const [text, setText] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [loading, setLoading] = useState(false)
  const [conversation, setConversation] = useState([])
  const [apiStatus, setApiStatus] = useState('ready') // 'ready' | 'live' | 'error'
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [speakingMsgId, setSpeakingMsgId] = useState(null)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [liveTranscript, setLiveTranscript] = useState('')
  const [micLevel, setMicLevel] = useState(0)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const wantRecordingRef = useRef(false)
  const bottomRef = useRef(null)
  const speechRecognitionRef = useRef(null)
  const audioRef = useRef(null)
  const recordingTimerRef = useRef(null)
  const recordingStartTimeRef = useRef(0)
  const stopDelayTimerRef = useRef(null)
  const liveTranscriptRef = useRef('')
  const audioContextRef = useRef(null)
  const analyserRafRef = useRef(null)

  useEffect(() => {
    if (initialQuery) {
      setExpanded(true)
      submitTextInternal(initialQuery, lang)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery])

  useEffect(() => {
    const handleVoiceEvent = (e) => {
      const prompt = e.detail?.prompt
      if (prompt) {
        setExpanded(true)
        submitTextInternal(prompt, lang)
      }
    }
    window.addEventListener('farmAdvisor:voiceQuery', handleVoiceEvent)
    return () => window.removeEventListener('farmAdvisor:voiceQuery', handleVoiceEvent)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, location])

  const stopAllAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      audioRef.current = null
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
    setIsSpeaking(false)
    setSpeakingMsgId(null)
  }

  useEffect(() => {
    if (!expanded) {
      stopAllAudio()
    }
  }, [expanded])

  useEffect(() => {
    return () => {
      stopAllAudio()
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation, loading])

  // ─── Core: submit text query ────────────────────────────────────────────────
  const submitTextInternal = async (queryText, currentLang, isRetry = false) => {
    if (!queryText.trim()) return
    setLoading(true)
    if (!isRetry) {
      setConversation(prev => [...prev, { role: 'user', text: queryText }])
    }
    try {
      const bcpLang = LANG_BCP47[currentLang] || currentLang || 'kn-IN'
      const r = await voiceApi.textQuery(queryText, bcpLang, AGRICULTURAL_KEYTERMS, location)
      const data = r.data
      const responseText = data.reply_text || data.response || data.response_text
      if (!responseText) {
        throw new Error('Empty response returned by Gemini.')
      }
      const speechText = data.speech_text || responseText
      const audioB64 = data.audio_base64 || null
      setApiStatus('live')

      const msgId = conversation.length + (isRetry ? 0 : 1)
      stopAllAudio()
      if (audioB64) {
        const audio = playAudioBase64(audioB64)
        audioRef.current = audio
        if (audio) {
          setIsSpeaking(true)
          setSpeakingMsgId(msgId)
          audio.onended = () => {
            setIsSpeaking(false)
            setSpeakingMsgId(null)
          }
        }
      } else {
        const spoke = speakText(speechText, (data.language || currentLang).slice(0, 2))
        setIsSpeaking(spoke)
        setSpeakingMsgId(spoke ? msgId : null)
      }

      setConversation(prev => [
        ...prev,
        {
          role: 'assistant',
          text: responseText,
          speech_text: speechText,
          audio_b64: audioB64,
          status: 'live',
          detectedLang: data.language,
        }
      ])
    } catch (err) {
      setApiStatus('error')
      const detail = err.response?.data?.detail || err.message || 'Live Gemini service is temporarily unavailable.'
      setConversation(prev => [
        ...prev,
        {
          role: 'error',
          text: `Live AI error: ${detail}`,
          retryType: 'text',
          retryPayload: { queryText, currentLang },
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  // ─── Microphone (MediaRecorder + simultaneous SpeechRecognition) ──────────
  const stopAudioMeter = () => {
    if (analyserRafRef.current) {
      cancelAnimationFrame(analyserRafRef.current)
      analyserRafRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {})
      audioContextRef.current = null
    }
    setMicLevel(0)
  }

  const startAudioMeter = (stream) => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      if (!AudioCtx) return
      const ctx = new AudioCtx()
      audioContextRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      const dataArray = new Uint8Array(analyser.frequencyBinCount)

      const tick = () => {
        if (!wantRecordingRef.current) return
        analyser.getByteFrequencyData(dataArray)
        let sum = 0
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i]
        const avg = sum / dataArray.length
        setMicLevel(Math.min(100, Math.round((avg / 128) * 100)))
        analyserRafRef.current = requestAnimationFrame(tick)
      }
      analyserRafRef.current = requestAnimationFrame(tick)
    } catch {
      // Ignore Web Audio API errors
    }
  }

  const startSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return null
    try {
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.maxAlternatives = 1
      recognition.lang = LANG_BCP47[lang] || 'en-IN'
      recognition.onresult = (e) => {
        let combined = ''
        for (let i = 0; i < e.results.length; i++) {
          combined += e.results[i][0].transcript
        }
        const cleaned = combined.trim()
        liveTranscriptRef.current = cleaned
        setLiveTranscript(cleaned)
        setText(cleaned)
      }
      recognition.onerror = () => {}
      recognition.start()
      return recognition
    } catch {
      return null
    }
  }

  const startRecording = async () => {
    stopAllAudio()
    if (stopDelayTimerRef.current) {
      clearTimeout(stopDelayTimerRef.current)
      stopDelayTimerRef.current = null
    }
    wantRecordingRef.current = true
    setIsRecording(true)
    setRecordingSeconds(0)
    setLiveTranscript('')
    liveTranscriptRef.current = ''
    chunksRef.current = []
    recordingStartTimeRef.current = Date.now()

    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current)
    recordingTimerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - recordingStartTimeRef.current) / 1000)
      setRecordingSeconds(elapsed)
      if (elapsed >= RECORDING_CAP_SECONDS) {
        stopRecording()
      }
    }, 500)

    // Run SpeechRecognition simultaneously for real-time live text
    speechRecognitionRef.current = startSpeechRecognition()

    if (navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined') {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
          },
        })
        if (!wantRecordingRef.current) {
          stream.getTracks().forEach(tr => tr.stop())
          return
        }
        startAudioMeter(stream)
        const recorder = new MediaRecorder(stream)
        mediaRecorderRef.current = recorder
        recorder.ondataavailable = e => {
          if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
        }
        recorder.onstop = async () => {
          stopAudioMeter()
          stream.getTracks().forEach(tr => tr.stop())
          const durationMs = Date.now() - recordingStartTimeRef.current
          const capturedBrowserTranscript = liveTranscriptRef.current.trim()
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })

          if (durationMs < 600) {
            setLiveTranscript('')
            setText('')
            setConversation(prev => [
              ...prev,
              { role: 'error', text: 'Recording too short (< 0.6s). Hold or tap mic and speak your question.' }
            ])
            return
          }

          if (blob.size > 0) {
            setText('')
            setLiveTranscript('')
            await sendAudioBlob(blob, false, capturedBrowserTranscript)
          }
        }
        recorder.start()
        return
      } catch {
        // Fall through if getUserMedia fails
      }
    }

    if (speechRecognitionRef.current) {
      return
    }

    setIsRecording(false)
    wantRecordingRef.current = false
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current)
      recordingTimerRef.current = null
    }
    setConversation(prev => [
      ...prev,
      { role: 'error', text: 'Microphone access denied or unavailable in this browser.' }
    ])
  }

  const stopRecording = () => {
    if (!wantRecordingRef.current) return
    wantRecordingRef.current = false
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current)
      recordingTimerRef.current = null
    }
    setIsRecording(false)
    setRecordingSeconds(0)

    // 350ms delay before stopping MediaRecorder so the last word is never clipped
    stopDelayTimerRef.current = setTimeout(() => {
      try {
        speechRecognitionRef.current?.stop()
      } catch {
        // ignore
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
    }, 350)
  }

  const handleMicPointerDown = (e) => {
    e.preventDefault()
    if (loading) return
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const handleMicPointerUp = (e) => {
    e.preventDefault()
    if (!isRecording) return
    // If held for > 300ms, treat as Hold-to-Talk and stop on release; otherwise stay in Tap-to-Talk mode
    if (Date.now() - recordingStartTimeRef.current > 300) {
      stopRecording()
    }
  }

  const sendAudioBlob = async (blob, isRetry = false, browserTranscript = '') => {
    setLoading(true)
    const fd = new FormData()
    fd.append('audio', blob, 'recording.webm')
    fd.append('language', LANG_BCP47[lang] || 'auto')
    if (browserTranscript) {
      fd.append('browser_transcript', browserTranscript)
    }
    fd.append('keyterms', JSON.stringify(AGRICULTURAL_KEYTERMS))
    if (location?.lat != null) fd.append('lat', String(location.lat))
    if (location?.lon != null) fd.append('lon', String(location.lon))
    if (location?.location_name) fd.append('location_name', location.location_name)

    try {
      const r = await voiceApi.voiceQuery(fd)
      const data = r.data
      const transcript = data.transcript || data.transcription || browserTranscript
      const responseText = data.reply_text || data.response || data.response_text
      if (!responseText) {
        throw new Error('Incomplete response from Sarvam STT / Gemini.')
      }
      const speechText = data.speech_text || responseText
      const audioB64 = data.audio_base64 || null
      const detectedLang = data.language || LANG_BCP47[lang]
      setApiStatus('live')

      const msgId = conversation.length + (isRetry ? 0 : 1)
      stopAllAudio()
      if (audioB64) {
        const audio = playAudioBase64(audioB64)
        audioRef.current = audio
        if (audio) {
          setIsSpeaking(true)
          setSpeakingMsgId(msgId)
          audio.onended = () => {
            setIsSpeaking(false)
            setSpeakingMsgId(null)
          }
        }
      } else {
        const spoke = speakText(speechText, detectedLang.slice(0, 2))
        setIsSpeaking(spoke)
        setSpeakingMsgId(spoke ? msgId : null)
      }

      setConversation(prev => [
        ...prev,
        ...(isRetry ? [] : [{
          role: 'user',
          text: transcript,
          isTranscript: true,
          detectedLang,
        }]),
        {
          role: 'assistant',
          text: responseText,
          speech_text: speechText,
          audio_b64: audioB64,
          status: 'live',
          detectedLang,
        }
      ])
    } catch (err) {
      setApiStatus('error')
      const detail = err.response?.data?.detail || err.message || 'Could not transcribe or answer audio.'
      setConversation(prev => [
        ...prev,
        {
          role: 'error',
          text: `Voice query failed: ${detail}`,
          retryType: 'audio',
          retryPayload: blob,
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleRetry = (errMsg, idx) => {
    setConversation(prev => prev.filter((_, i) => i !== idx))
    if (errMsg.retryType === 'text' && errMsg.retryPayload) {
      submitTextInternal(errMsg.retryPayload.queryText, errMsg.retryPayload.currentLang, true)
    } else if (errMsg.retryType === 'audio' && errMsg.retryPayload) {
      sendAudioBlob(errMsg.retryPayload, true)
    }
  }

  const sendText = async () => {
    if (!text.trim()) return
    const q = text.trim()
    setText('')
    await submitTextInternal(q, lang)
  }

  const replayMessage = (msg, idx) => {
    if (isSpeaking && speakingMsgId === idx) {
      stopAllAudio()
      return
    }
    stopAllAudio()
    setIsSpeaking(true)
    setSpeakingMsgId(idx)
    if (msg.audio_b64) {
      const audio = playAudioBase64(msg.audio_b64)
      audioRef.current = audio
      if (audio) {
        audio.onended = () => {
          setIsSpeaking(false)
          setSpeakingMsgId(null)
        }
      } else {
        setIsSpeaking(false)
        setSpeakingMsgId(null)
      }
    } else {
      const spoke = speakText(msg.speech_text || msg.text, (msg.detectedLang || lang).slice(0, 2))
      if (spoke) {
        setTimeout(() => {
          setIsSpeaking(false)
          setSpeakingMsgId(null)
        }, 3000)
      } else {
        setIsSpeaking(false)
        setSpeakingMsgId(null)
      }
    }
  }

  const currentLang = LANGUAGES.find(l => l.code === lang)

  return (
    <>
      {/* Floating mic button */}
      {!expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="fixed bottom-20 right-4 z-30 w-14 h-14 rounded-full bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-900/40 flex items-center justify-center transition-transform hover:scale-105 active:scale-95"
          aria-label="Open voice assistant"
        >
          <Mic className="w-6 h-6" />
        </button>
      )}

      {/* Expanded panel */}
      {expanded && (
        <div className="fixed bottom-0 left-0 right-0 z-30 sm:bottom-6 sm:right-4 sm:left-auto sm:w-96">
          <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl border border-gray-200 flex flex-col max-h-[82vh]">

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-green-700 rounded-t-2xl">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Mic className="w-4 h-4 text-white shrink-0" />
                  <span className="text-white font-semibold text-sm truncate">{t('voice_title')}</span>
                  <span className="text-green-200 text-xs shrink-0">{currentLang?.name}</span>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-green-100 mt-0.5 truncate">
                  <MapPin className="w-3 h-3 shrink-0" />
                  <span className="truncate">
                    {location?.location_name || 'Location not set (pick in header)'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {isSpeaking && (
                  <button
                    onClick={stopAllAudio}
                    className="flex items-center gap-1 text-xs px-2 py-1 rounded-full font-semibold bg-red-500 hover:bg-red-600 text-white shadow-sm transition-colors"
                    title={t('stop_audio')}
                  >
                    <Square className="w-3 h-3 fill-current" />
                    <span>{t('stop_audio')}</span>
                  </button>
                )}
                <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${
                  apiStatus === 'error'
                    ? 'bg-red-500/40 text-red-100'
                    : 'bg-green-500/30 text-green-100'
                }`}>
                  {apiStatus === 'error' ? <AlertCircle className="w-3 h-3" /> : <Zap className="w-3 h-3" />}
                  {apiStatus === 'error' ? 'Error' : 'Live AI'}
                </span>
                <button
                  onClick={() => {
                    stopAllAudio()
                    setExpanded(false)
                  }}
                  className="text-white/70 hover:text-white p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Language selector */}
            <div className="px-3 py-2 border-b bg-green-50 flex gap-1.5 overflow-x-auto">
              {LANGUAGES.map(l => (
                <button
                  key={l.code}
                  onClick={() => setLang(l.code)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors
                    ${lang === l.code ? 'bg-green-600 text-white' : 'bg-white text-gray-600 border hover:bg-green-100'}`}
                >
                  {l.name}
                </button>
              ))}
            </div>

            {/* Conversation history */}
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-[160px]">
              {conversation.length === 0 && (
                <div className="flex flex-col items-center justify-center h-32 text-center text-gray-400 gap-2">
                  <MessageCircle className="w-10 h-10 text-green-200" />
                  <p className="text-sm">Ask anything about farming in {currentLang?.label}</p>
                  <p className="text-xs opacity-60">ಬೆಲೆ, ರೋಗ, ಬೆಳೆ, ಹವಾಮಾನ, ಸರ್ಕಾರಿ ಯೋಜನೆ…</p>
                </div>
              )}
              {conversation.map((msg, i) => {
                if (msg.role === 'error') {
                  return (
                    <div key={i} className="bg-red-50 border border-red-200 rounded-xl p-2.5 text-xs text-red-800 space-y-1.5">
                      <div className="flex items-start gap-1.5">
                        <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                        <span>{msg.text}</span>
                      </div>
                      {msg.retryType && (
                        <button
                          onClick={() => handleRetry(msg, i)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-red-600 hover:bg-red-700 text-white font-semibold text-[11px] transition-colors"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Retry
                        </button>
                      )}
                    </div>
                  )
                }

                return (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-green-600 text-white rounded-br-sm'
                        : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                    }`}>
                      {msg.role === 'user' && (
                        <div className="flex items-center justify-between gap-2 text-[10px] text-green-100 font-semibold mb-1 border-b border-green-500/40 pb-0.5">
                          <span>{msg.isTranscript ? '🎙️ You asked:' : 'You asked:'}</span>
                          {msg.detectedLang && <span className="bg-green-700/70 px-1.5 rounded">{msg.detectedLang}</span>}
                        </div>
                      )}
                      {msg.role === 'assistant' && (
                        <div className="text-[10px] text-green-700 font-semibold mb-1 border-b border-gray-200 pb-0.5">
                          Farm Advisor:
                        </div>
                      )}
                      <div className="whitespace-pre-wrap">{msg.text}</div>
                      {msg.role === 'assistant' && (
                        <div className="flex items-center gap-1.5 mt-1.5">
                          <button
                            onClick={() => replayMessage(msg, i)}
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold transition-colors ${
                              isSpeaking && speakingMsgId === i
                                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                                : 'text-gray-500 hover:text-green-600 hover:bg-green-50'
                            }`}
                            title={isSpeaking && speakingMsgId === i ? t('stop_audio') : 'Listen'}
                          >
                            {isSpeaking && speakingMsgId === i ? (
                              <>
                                <Square className="w-3 h-3 fill-current" />
                                <span>{t('stop_audio')}</span>
                              </>
                            ) : (
                              <>
                                <Volume2 className="w-3.5 h-3.5" />
                                <span>Listen</span>
                              </>
                            )}
                          </button>
                          <span className="text-[9px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full font-semibold flex items-center gap-0.5">
                            <Zap className="w-2.5 h-2.5" />Live Gemini
                          </span>
                          {msg.detectedLang && (
                            <span className="text-[9px] text-gray-400">{msg.detectedLang}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
              {isRecording && (
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-br-sm px-3 py-2 text-sm bg-green-50 border border-green-200 text-green-900">
                    <div className="flex items-center gap-2 text-[10px] font-semibold text-green-700 mb-1">
                      <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-ping" />
                      <span>Listening live…</span>
                      <div className="flex items-end gap-0.5 h-3 ml-auto">
                        {[0.3, 0.6, 1, 0.7, 0.4].map((scale, idx) => (
                          <span
                            key={idx}
                            className="w-1 bg-green-600 rounded-full transition-all duration-75"
                            style={{ height: `${Math.max(20, Math.min(100, micLevel * scale))}%` }}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="whitespace-pre-wrap text-xs">
                      {liveTranscript || 'Speak your question clearly…'}
                    </div>
                  </div>
                </div>
              )}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-2 flex items-center gap-2 text-xs text-gray-500">
                    <Loader2 className="w-4 h-4 animate-spin text-green-600" />
                    <span>Transcribing & querying live Gemini…</span>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input bar */}
            <div className="px-3 py-3 border-t bg-gray-50 rounded-b-2xl">
              <div className="flex items-center gap-2">
                <button
                  onPointerDown={handleMicPointerDown}
                  onPointerUp={handleMicPointerUp}
                  disabled={loading}
                  className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                    isRecording
                      ? 'bg-red-500 text-white animate-pulse'
                      : 'bg-green-600 text-white hover:bg-green-500'
                  }`}
                  title="Tap or hold to record voice"
                >
                  {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>

                <input
                  type="text"
                  value={text}
                  onChange={e => setText(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendText()}
                  placeholder={PLACEHOLDERS[lang] || t('voice_placeholder')}
                  disabled={loading || isRecording}
                  className="flex-1 rounded-full border border-gray-200 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-400"
                />

                <button
                  onClick={sendText}
                  disabled={!text.trim() || loading}
                  className="flex-shrink-0 w-10 h-10 rounded-full bg-green-600 text-white flex items-center justify-center hover:bg-green-500 disabled:opacity-40 transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              <p className="text-center text-xs text-gray-400 mt-1.5">
                {isRecording
                  ? `🔴 Recording (${recordingSeconds}s / ${RECORDING_CAP_SECONDS}s cap)… release to send`
                  : 'Hold mic or type · Sarvam saaras:v4 + Live Gemini'}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
