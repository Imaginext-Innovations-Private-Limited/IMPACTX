/**
 * FasalSaarathi — Module 4: WhatsApp-Style Farm Passbook UI & Voice Note Bubble (6 Languages)
 */
document.addEventListener("DOMContentLoaded", () => {
    const langSelect = document.getElementById("langSelect");
    const chatFeed = document.getElementById("pbChatFeed");
    const locInput = document.getElementById("pbLocationInput");
    const replyInput = document.getElementById("pbReplyInput");
    const sendBtn = document.getElementById("pbSendBtn");
    const refreshBtn = document.getElementById("pbRefreshBriefBtn");
    const clearBtn = document.getElementById("pbClearBtn");

    const statWaste = document.getElementById("pbStatWaste");
    const statIns = document.getElementById("pbStatIns");
    const statLoc = document.getElementById("pbStatLoc");

    let pbAudio = null;
    let initialLoaded = false;
    let lastLoadedLang = null;

    const PB_I18N = {
        en: {
            nav: "Passbook", title: "FasalSaarathi Farm Passbook", sub: "online • Daily Weather, Compost, Insurance & Mandi Voice Briefing",
            refresh: "Get Today's Briefing", playNote: "Play Voice Note",
            wasteLbl: "♻️ Kitchen Waste", insLbl: "🛡️ Crop Shield", locLbl: "📍 Farm Location",
            savedUnit: "saved", activeUnit: "Active", farmDefault: "Your Farm",
            chipWaste: "♻️ Added 1kg Kitchen Waste", chipIns: "🛡️ Check Insurance Alert", chipMandi: "💰 Today's Mandi Rate", chipBrief: "☀️ Morning Briefing",
            locPh: "Location (optional)", replyPh: "Reply in chat (e.g. Added 2 kg peels, Onion rate)...",
            emptyMsg: "Tap Get Today's Briefing or a quick reply below",
        },
        kn: {
            nav: "ಪಾಸ್‌ಬುಕ್", title: "ಫಸಲ್ ಸಾರಥಿ ಫಾರ್ಮ್ ಪಾಸ್‌ಬುಕ್", sub: "ಆನ್‌ಲೈನ್ • ದೈನಂದಿನ ಹವಾಮಾನ, ಗೊಬ್ಬರ, ವಿಮೆ ಮತ್ತು ಮಂಡಿ ಮಾಹಿತಿ",
            refresh: "ಇಂದಿನ ಮಾಹಿತಿ ಪಡೆಯಿರಿ", playNote: "ಧ್ವನಿ ಸಂದೇಶ ಕೇಳಿ",
            wasteLbl: "♻️ ಅಡುಗೆ ತ್ಯಾಜ್ಯ", insLbl: "🛡️ ಬೆಳೆ ವಿಮೆ", locLbl: "📍 ನಿಮ್ಮ ಸ್ಥಳ",
            savedUnit: "ಉಳಿತಾಯ", activeUnit: "ಸಕ್ರಿಯ", farmDefault: "ನಿಮ್ಮ ಹೊಲ",
            chipWaste: "♻️ 1 ಕೆ.ಜಿ ಅಡುಗೆ ತ್ಯಾಜ್ಯ ಸೇರಿದೆ", chipIns: "🛡️ ವಿಮೆ ಎಚ್ಚರಿಕೆ ನೋಡಿ", chipMandi: "💰 ಇಂದಿನ ಮಂಡಿ ದರ", chipBrief: "☀️ ಬೆಳಗಿನ ವರದಿ",
            locPh: "ಸ್ಥಳ (ಐಚ್ಛಿಕ)", replyPh: "ಇಲ್ಲಿ ಉತ್ತರಿಸಿ (ಉದಾ: 2 ಕೆ.ಜಿ ಸಿಪ್ಪೆ, ಈರುಳ್ಳಿ ದರ)...",
            emptyMsg: "ಕೆಳಗಿನ 'ಇಂದಿನ ಮಾಹಿತಿ ಪಡೆಯಿರಿ' ಒತ್ತಿ",
        },
        hi: {
            nav: "पासबुक", title: "फसल सारथी फ़ार्म पासबुक", sub: "ऑनलाइन • दैनिक मौसम, खाद, बीमा और मंडी वॉइस अपडेट",
            refresh: "आज की रिपोर्ट पाएं", playNote: "वॉइस नोट सुनें",
            wasteLbl: "♻️ रसोई कचरा", insLbl: "🛡️ फसल बीमा", locLbl: "📍 खेत का स्थान",
            savedUnit: "बचत", activeUnit: "सक्रिय", farmDefault: "आपका खेत",
            chipWaste: "♻️ 1 किलो रसोई कचरा जोड़ा", chipIns: "🛡️ बीमा अलर्ट जांचें", chipMandi: "💰 आज का मंडी भाव", chipBrief: "☀️ सुबह की रिपोर्ट",
            locPh: "लोकेशन (वैकल्पिक)", replyPh: "चैट में लिखें (जैसे: 2 किलो छिलके, प्याज का भाव)...",
            emptyMsg: "नीचे 'आज की रिपोर्ट पाएं' दबाएं",
        },
        ta: {
            nav: "பாஸ்புக்", title: "பசல் சாரதி பண்ணை பாஸ்புக்", sub: "ஆன்லைன் • தினசரி வானிலை, உரம், காப்பீடு & சந்தை தகவல்",
            refresh: "இன்றைய தகவல் பெறு", playNote: "குரல் செய்தி கேள்",
            wasteLbl: "♻️ சமையலறை கழிவு", insLbl: "🛡️ பயிர் காப்பீடு", locLbl: "📍 பண்ணை இடம்",
            savedUnit: "சேமிப்பு", activeUnit: "செயலில்", farmDefault: "உங்கள் பண்ணை",
            chipWaste: "♻️ 1 கிலோ கழிவு சேர்த்தேன்", chipIns: "🛡️ காப்பீட்டு எச்சரிக்கை", chipMandi: "💰 இன்றைய சந்தை விலை", chipBrief: "☀️ காலை அறிக்கை",
            locPh: "ஊர் (விருப்பம்)", replyPh: "அரட்டையில் எழுதவும் (எ.கா: 2 கிலோ கழிவு, வெங்காய விலை)...",
            emptyMsg: "கீழே உள்ள பொத்தானை அழுத்தவும்",
        },
        te: {
            nav: "పాస్‌బుక్", title: "ఫసల్ సారథి ఫార్మ్ పాస్‌బుక్", sub: "ఆన్‌లైన్ • రోజువారీ వాతావరణం, ఎరువు, బీమా & మండీ వాయిస్ నోట్",
            refresh: "నేటి రిపోర్ట్ పొందండి", playNote: "వాయిస్ నోట్ వినండి",
            wasteLbl: "♻️ వంటగది వ్యర్థాలు", insLbl: "🛡️ పంట బీమా", locLbl: "📍 పొలం స్థలం",
            savedUnit: "ఆదా", activeUnit: "యాక్టివ్", farmDefault: "మీ పొలం",
            chipWaste: "♻️ 1 కిలో వ్యర్థం వేశాను", chipIns: "🛡️ బీమా అలర్ట్ చూడండి", chipMandi: "💰 నేటి మండీ ధర", chipBrief: "☀️ ఉదయం రిపోర్ట్",
            locPh: "ఊరు (ఐచ్ఛికం)", replyPh: "చాట్‌లో రాయండి (ఉదా: 2 కిలోల తొక్కలు, ఉల్లి ధర)...",
            emptyMsg: "కింద 'నేటి రిపోర్ట్ పొందండి' నొక్కండి",
        },
        mr: {
            nav: "पासबुक", title: "फसल सारथी फार्म पासबुक", sub: "ऑनलाईन • दैनिक हवामान, खत, विमा व बाजारभाव व्हॉइस अपडेट",
            refresh: "आजचा अहवाल मिळवा", playNote: "व्हॉइस नोट ऐका",
            wasteLbl: "♻️ स्वयंपाकघर कचरा", insLbl: "🛡️ पीक विमा", locLbl: "📍 शेताचे ठिकाण",
            savedUnit: "बचत", activeUnit: "सक्रिय", farmDefault: "तुमचे शेत",
            chipWaste: "♻️ 1 किलो कचरा टाकला", chipIns: "🛡️ विमा इशारा तपासा", chipMandi: "💰 आजचा बाजारभाव", chipBrief: "☀️ सकाळचा अहवाल",
            locPh: "गाव (ऐच्छिक)", replyPh: "चॅटमध्ये लिहा (उदा: 2 किलो कचरा, कांदा भाव)...",
            emptyMsg: "खालील बटण दाबा",
        },
    };

    function lang() {
        return (langSelect && langSelect.value) || "en";
    }

    function esc(s) {
        return String(s || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    let lastStats = null;

    function updateStats(stats) {
        if (stats) lastStats = stats;
        const s = lastStats || { waste_kg: 0, saved_inr: 0, active_policies: 0, location: "" };
        const t = PB_I18N[lang()] || PB_I18N.en;
        if (statWaste) statWaste.textContent = `${s.waste_kg ?? 0} kg (₹${s.saved_inr ?? 0} ${t.savedUnit})`;
        if (statIns) statIns.textContent = `${s.active_policies ?? 0} ${t.activeUnit}`;
        if (statLoc) statLoc.textContent = s.location || t.farmDefault;
    }

    function applyI18n() {
        const t = PB_I18N[lang()] || PB_I18N.en;
        const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        set("navPassbookLabel", t.nav);
        set("pbTitle", t.title);
        set("pbSubtitle", t.sub);
        set("pbRefreshLabel", t.refresh);
        set("pbStatWasteLbl", t.wasteLbl);
        set("pbStatInsLbl", t.insLbl);
        set("pbStatLocLbl", t.locLbl);
        set("pbChipWaste", t.chipWaste);
        set("pbChipIns", t.chipIns);
        set("pbChipMandi", t.chipMandi);
        set("pbChipBrief", t.chipBrief);
        set("pbEmptyBanner", t.emptyMsg);
        if (locInput) locInput.placeholder = t.locPh;
        if (replyInput) replyInput.placeholder = t.replyPh;
        updateStats(null);
    }

    function playVoiceNote(text, btn) {
        if (!text) return;
        if (pbAudio) {
            pbAudio.pause();
            pbAudio = null;
        }
        const origHtml = btn ? btn.innerHTML : "";
        if (btn) btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1"></i>...`;

        fetch("/api/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, lang: lang() }),
        })
            .then(r => {
                if (!r.ok) throw new Error("fallback");
                return r.blob();
            })
            .then(blob => {
                const url = URL.createObjectURL(blob);
                pbAudio = new Audio(url);
                if (btn) btn.innerHTML = `<i class="fa-solid fa-volume-high mr-1"></i>▶`;
                pbAudio.onended = () => { if (btn) btn.innerHTML = origHtml; };
                pbAudio.play().catch(() => { if (btn) btn.innerHTML = origHtml; });
            })
            .catch(() => {
                if ("speechSynthesis" in window) {
                    const u = new SpeechSynthesisUtterance(text);
                    u.onend = () => { if (btn) btn.innerHTML = origHtml; };
                    window.speechSynthesis.speak(u);
                } else if (btn) {
                    btn.innerHTML = origHtml;
                }
            });
    }

    function formatTime(isoStr) {
        if (!isoStr) return "Now";
        try {
            const d = new Date(isoStr);
            return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        } catch (_) {
            return "Now";
        }
    }

    function appendBubble(msg) {
        if (!chatFeed || !msg) return;
        const isUser = msg.sender === "user";
        const t = PB_I18N[lang()] || PB_I18N.en;
        const wrap = document.createElement("div");
        wrap.className = isUser ? "flex justify-end" : "flex justify-start";

        const timeStr = formatTime(msg.created_at);
        const bodyHtml = esc(msg.text || "").replace(/\n/g, "<br>");

        if (isUser) {
            wrap.innerHTML = `
                <div class="max-w-[82%] bg-[#d9fdd3] text-gray-900 rounded-2xl rounded-tr-none px-3.5 py-2 shadow-xs border border-emerald-200 space-y-1">
                    <div class="text-xs leading-relaxed font-medium">${bodyHtml}</div>
                    <div class="text-[10px] text-gray-500 text-right">${timeStr} <span class="text-sky-600 font-bold">✓✓</span></div>
                </div>
            `;
        } else {
            const bubbleId = `pb_play_${Math.random().toString(36).slice(2, 9)}`;
            wrap.innerHTML = `
                <div class="max-w-[88%] bg-white text-gray-900 rounded-2xl rounded-tl-none px-3.5 py-2.5 shadow-xs border border-gray-200 space-y-2">
                    <div class="text-xs leading-relaxed">${bodyHtml}</div>
                    <div class="flex items-center justify-between gap-3 pt-1.5 border-t border-gray-100">
                        <button type="button" id="${bubbleId}" class="px-2.5 py-1 rounded-full bg-emerald-50 hover:bg-emerald-100 text-emerald-900 border border-emerald-200 text-[11px] font-bold flex items-center space-x-1.5 transition">
                            <i class="fa-solid fa-play text-[10px]"></i>
                            <span>${esc(t.playNote)}</span>
                            <span class="text-[10px] text-emerald-700 font-mono">━━━━━━</span>
                        </button>
                        <span class="text-[10px] text-gray-400">${timeStr} ✓✓</span>
                    </div>
                </div>
            `;
            setTimeout(() => {
                const btn = document.getElementById(bubbleId);
                if (btn) btn.addEventListener("click", () => playVoiceNote(msg.speech_text || msg.text, btn));
            }, 0);
        }

        chatFeed.appendChild(wrap);
        chatFeed.scrollTop = chatFeed.scrollHeight;
    }

    async function fetchDailyBriefing(save = true) {
        if (!chatFeed) return;
        const currLang = lang();
        lastLoadedLang = currLang;
        const loc = (locInput && locInput.value.trim()) || "";
        const params = new URLSearchParams({ language: currLang, save: save ? "true" : "false" });
        if (loc) params.set("location", loc);

        try {
            const resp = await fetch(`/api/passbook/daily?${params.toString()}`);
            const data = await resp.json();
            if (data && data.status === "success") {
                updateStats(data.stats);
                appendBubble(data.message);
            }
        } catch (_) {}
    }

    async function loadHistoryOrInit() {
        if (!chatFeed) return;
        const currLang = lang();
        try {
            const resp = await fetch("/api/passbook/history");
            const data = await resp.json();
            const msgs = (data && data.messages) || [];
            chatFeed.innerHTML = "";
            let lastMsgLang = null;
            if (msgs.length > 0) {
                msgs.forEach(appendBubble);
                const lastBot = [...msgs].reverse().find(m => m.sender === "bot" && m.metadata);
                if (lastBot && lastBot.metadata) {
                    updateStats(lastBot.metadata);
                    lastMsgLang = lastBot.metadata.lang || null;
                }
            }
            // Fetch a fresh briefing in the active language if history is empty or was in another language
            if (msgs.length === 0 || lastMsgLang !== currLang) {
                await fetchDailyBriefing(true);
            }
            lastLoadedLang = currLang;
            initialLoaded = true;
        } catch (_) {}
    }

    async function sendReply(action, text) {
        const loc = (locInput && locInput.value.trim()) || "";
        try {
            const resp = await fetch("/api/passbook/reply", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: action || "",
                    text: text || "",
                    location: loc || null,
                    language: lang(),
                }),
            });
            const data = await resp.json();
            if (data && data.status === "success") {
                appendBubble(data.user_message);
                appendBubble(data.bot_message);
                updateStats(data.stats);
            }
        } catch (_) {}
    }

    document.querySelectorAll(".pb-quick-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            sendReply(btn.getAttribute("data-action"), "");
        });
    });

    if (sendBtn && replyInput) {
        const doSend = () => {
            const txt = replyInput.value.trim();
            if (!txt) return;
            replyInput.value = "";
            sendReply("", txt);
        };
        sendBtn.addEventListener("click", doSend);
        replyInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") doSend();
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => fetchDailyBriefing(true));
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", async () => {
            await fetch("/api/passbook/clear", { method: "POST" });
            if (chatFeed) chatFeed.innerHTML = "";
            await fetchDailyBriefing(true);
        });
    }

    // Load Passbook history when user opens the Passbook tab (and refresh in new language if changed)
    const pbTabBtn = document.querySelector('.nav-tab[data-target="tab-passbook"]');
    if (pbTabBtn) {
        pbTabBtn.addEventListener("click", () => {
            if (!initialLoaded) {
                loadHistoryOrInit();
            } else if (lastLoadedLang !== lang()) {
                fetchDailyBriefing(true);
            }
        });
    }

    if (langSelect) {
        langSelect.addEventListener("change", () => {
            applyI18n();
            if (initialLoaded && lastLoadedLang !== lang()) {
                fetchDailyBriefing(true);
            }
        });
    }
    applyI18n();
});
