/**
 * FasalSaarathi — Module 1: Header Profile Pill, Quick Farm Profile Modal & Per-User Context Sync
 * Ensures switching accounts never leaks the previous user's cached location from localStorage.
 */
document.addEventListener("DOMContentLoaded", () => {
    const authHeaderBtn = document.getElementById("authHeaderBtn");
    const authHeaderText = document.getElementById("authHeaderText");
    const profileModal = document.getElementById("profileModal");
    const closeProfileModalBtn = document.getElementById("closeProfileModalBtn");
    const saveProfileBtn = document.getElementById("saveProfileBtn");
    const logoutProfileBtn = document.getElementById("logoutProfileBtn");
    const profileModalAlert = document.getElementById("profileModalAlert");
    const langSelect = document.getElementById("langSelect");

    const STORAGE_KEYS = ["kv_weather_loc", "kv_soil_loc", "kv_mandi_loc", "kv_mandi_crop"];
    const LOCATION_INPUT_IDS = ["toolWeatherLoc", "toolSoilDist", "toolMandiLoc", "terraceLoc", "insWeatherLoc", "pbLocationInput"];
    let activeUser = null;

    function clearStoredToolState() {
        try {
            STORAGE_KEYS.forEach(k => localStorage.removeItem(k));
        } catch (_) {}
    }

    function syncStorageForUser(user) {
        clearStoredToolState();
        try {
            if (user && user.user_id) {
                localStorage.setItem("kv_active_user_id", user.user_id);
                const loc = (user.location_query || "").trim();
                if (loc) {
                    localStorage.setItem("kv_weather_loc", loc);
                    localStorage.setItem("kv_soil_loc", loc);
                    localStorage.setItem("kv_mandi_loc", loc);
                }
            } else {
                localStorage.removeItem("kv_active_user_id");
            }
        } catch (_) {}
    }

    function setLocationInputs(loc, forceOverwrite) {
        LOCATION_INPUT_IDS.forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            if (forceOverwrite || (loc && !el.value.trim())) {
                el.value = loc || "";
            }
        });
    }

    function resetToolCropsOnSwitch() {
        const soilCrop = document.getElementById("toolSoilCrop");
        if (soilCrop) soilCrop.value = "general";
        const mandiCrop = document.getElementById("toolMandiCrop");
        if (mandiCrop) mandiCrop.value = "Tomato";
    }

    function refreshAgroToolsForLocation(loc) {
        if (loc) {
            ["testWeatherBtn", "testSoilBtn", "testMandiBtn"].forEach(id => {
                const btn = document.getElementById(id);
                if (btn) btn.click();
            });
        } else {
            ["toolWeatherOutput", "toolSoilOutput"].forEach(id => {
                const box = document.getElementById(id);
                if (box) {
                    box.innerHTML = '<div class="text-xs text-gray-500 p-2">Enter your village, city, PIN, or tap GPS to fetch live data.</div>';
                }
            });
            const mandiBtn = document.getElementById("testMandiBtn");
            if (mandiBtn) mandiBtn.click();
        }
    }

    function applyUserContext(user) {
        let prevUid = "";
        try { prevUid = localStorage.getItem("kv_active_user_id") || ""; } catch (_) {}
        const currUid = user ? user.user_id : "";
        const accountChanged = prevUid !== currUid;

        activeUser = user;
        if (!authHeaderBtn || !authHeaderText) return;

        if (!user) {
            authHeaderText.textContent = "Login";
            authHeaderBtn.setAttribute("data-logged-in", "false");
            if (accountChanged) {
                syncStorageForUser(null);
                resetToolCropsOnSwitch();
                setLocationInputs("", true);
                refreshAgroToolsForLocation("");
            }
            return;
        }

        const icon = user.persona === "terrace" ? "🪴" : "🌾";
        const locPart = user.location_query ? ` • ${user.location_query}` : "";
        authHeaderText.textContent = `${icon} ${user.name}${locPart}`;
        authHeaderBtn.setAttribute("data-logged-in", "true");

        if (accountChanged) {
            syncStorageForUser(user);
            resetToolCropsOnSwitch();
        }

        // Sync global language with app.js
        if (langSelect && user.language && langSelect.value !== user.language) {
            langSelect.value = user.language;
            langSelect.dispatchEvent(new Event("change"));
        }

        // Always enforce the current user's location when switching accounts (even if empty)
        const userLoc = (user.location_query || "").trim();
        setLocationInputs(userLoc, accountChanged);
        if (accountChanged) {
            refreshAgroToolsForLocation(userLoc);
        }

        // Highlight persona-relevant tab subtly
        const terraceTab = document.querySelector('.nav-tab[data-target="tab-terrace"]');
        const toolsTab = document.querySelector('.nav-tab[data-target="tab-tools"]');
        const insTab = document.querySelector('.nav-tab[data-target="tab-insurance"]');
        if (terraceTab && toolsTab) {
            terraceTab.classList.toggle("ring-2", user.persona === "terrace");
            terraceTab.classList.toggle("ring-amber-400", user.persona === "terrace");
            toolsTab.classList.toggle("ring-2", user.persona === "farmer");
            toolsTab.classList.toggle("ring-amber-400", user.persona === "farmer");
            if (insTab) {
                insTab.classList.toggle("ring-2", user.persona === "farmer");
                insTab.classList.toggle("ring-amber-400", user.persona === "farmer");
            }
        }
    }

    function openProfileModal() {
        if (!profileModal || !activeUser) return;
        document.getElementById("profName").value = activeUser.name || "";
        document.getElementById("profPersona").value = activeUser.persona || "farmer";
        document.getElementById("profLocation").value = activeUser.location_query || "";
        document.getElementById("profLang").value = activeUser.language || (langSelect ? langSelect.value : "en");
        if (profileModalAlert) profileModalAlert.className = "hidden";
        profileModal.classList.remove("hidden");
        profileModal.classList.add("flex");
    }

    function closeProfileModal() {
        if (!profileModal) return;
        profileModal.classList.add("hidden");
        profileModal.classList.remove("flex");
    }

    if (authHeaderBtn) {
        authHeaderBtn.addEventListener("click", (e) => {
            if (activeUser) {
                e.preventDefault();
                openProfileModal();
            } else {
                const lang = langSelect ? langSelect.value : "en";
                authHeaderBtn.href = `/login?lang=${encodeURIComponent(lang)}`;
            }
        });
    }

    if (closeProfileModalBtn) {
        closeProfileModalBtn.addEventListener("click", closeProfileModal);
    }

    if (profileModal) {
        profileModal.addEventListener("click", (e) => {
            if (e.target === profileModal) closeProfileModal();
        });
    }

    if (saveProfileBtn) {
        saveProfileBtn.addEventListener("click", async () => {
            const payload = {
                name: document.getElementById("profName").value.trim(),
                persona: document.getElementById("profPersona").value,
                location_query: document.getElementById("profLocation").value.trim(),
                language: document.getElementById("profLang").value,
            };
            try {
                const resp = await fetch("/api/auth/profile", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                const data = await resp.json();
                if (resp.ok && data.status === "success") {
                    syncStorageForUser(data.user);
                    setLocationInputs(data.user.location_query || "", true);
                    refreshAgroToolsForLocation((data.user.location_query || "").trim());
                    applyUserContext(data.user);
                    closeProfileModal();
                } else if (profileModalAlert) {
                    profileModalAlert.textContent = data.message || "Could not save profile.";
                    profileModalAlert.className = "rounded-xl px-3 py-2 text-xs font-semibold bg-red-50 text-red-800 border border-red-200";
                }
            } catch (_) {
                if (profileModalAlert) {
                    profileModalAlert.textContent = "Network error saving profile.";
                    profileModalAlert.className = "rounded-xl px-3 py-2 text-xs font-semibold bg-red-50 text-red-800 border border-red-200";
                }
            }
        });
    }

    if (logoutProfileBtn) {
        logoutProfileBtn.addEventListener("click", async () => {
            await fetch("/api/auth/logout", { method: "POST" });
            clearStoredToolState();
            try { localStorage.removeItem("kv_active_user_id"); } catch (_) {}
            window.location.href = "/login";
        });
    }

    // Persist language switch if user is logged in
    if (langSelect) {
        langSelect.addEventListener("change", () => {
            if (activeUser && activeUser.language !== langSelect.value) {
                fetch("/api/auth/profile", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ language: langSelect.value }),
                }).then(r => r.json()).then(d => {
                    if (d && d.status === "success") activeUser = d.user;
                }).catch(() => {});
            }
        });
    }

    // Load current session user on startup
    fetch("/api/auth/me")
        .then(r => r.json())
        .then(data => {
            if (data && data.authenticated && data.user) {
                applyUserContext(data.user);
            } else {
                applyUserContext(null);
            }
        })
        .catch(() => applyUserContext(null));
});
