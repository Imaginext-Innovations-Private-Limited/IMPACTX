FasalSaarathi — New Modules Transfer Package (Login, Insurance, Passbook)
=============================================================================

This folder contains ONLY the newly created and modified files needed to add
the 3 new modules (+ Mandi UI/GPS fixes) into an existing FasalSaarathi
project on another laptop, preserving the exact directory structure.

No ".env", API keys, passwords, "__pycache__", ".pyc", ".db", or ".git"
files are included.

-----------------------------------------------------------------------------
1. NEW MODULES INCLUDED
-----------------------------------------------------------------------------
1) Module 1: Picture-PIN Login & Farmer Profile
   - Passwordless 4-icon Picture-PIN registration and login (hashed with
     Werkzeug PBKDF2 in SQLite `data/fasalsaarathi_users.db`).
   - Field Farmer vs. Terrace Grower persona selection + 1-tap Guest Demo.
   - Header profile badge, My Farm Profile edit modal, and per-user location
     isolation across account switches.
   - 6-language support: English, Kannada, Hindi, Tamil, Telugu, Marathi.

2) Module 3: PMFBY Crop Insurance Shield & Weather-Loss Alerts
   - PMFBY premium & coverage calculator (Kharif 2%, Rabi 1.5%,
     Horticulture/Commercial 5%) across 15 crops and 6 languages.
   - Live 72-hour extreme weather trigger checking Open-Meteo hail/storm
     WMO codes (95, 96, 99), heavy rain (>= 40 mm), and strong wind gusts.
   - Insured crop Policy Vault and One-Click Claim Evidence Dossier
     (bundles damage photo, GPS, timestamp, weather snapshot, and checklist).

3) Module 4: Farm Passbook (Daily Briefing & Quick Replies)
   - Unified daily briefing combining Profile, Live Weather, Kitchen Waste
     & Compost savings, Crop Insurance status, and APMC Mandi rates.
   - Two-way quick-reply chips (log 1kg kitchen waste, check insurance alert,
     check mandi rate, refresh morning briefing) + free-text replies.
   - Built-in voice playback via `/api/tts` across all 6 languages.

4) Agro Tools Fix (Included in static/js/app.js & templates/index.html)
   - Fixes horizontal clipping in the APMC Mandi Tool card and syncs Mandi
     GPS auto-detection when location is empty.

-----------------------------------------------------------------------------
2. FILES INCLUDED (17 Code/Config Files + This README.txt)
-----------------------------------------------------------------------------
Modified Existing Files (4):
  - app.py                  (Registers auth_bp, insurance_bp, passbook_bp)
  - templates/index.html    (Header profile pill/modal, Crop Shield & Passbook
                             tabs, script tags, Agro Tools min-w-0 fix)
  - static/js/app.js        (Mandi card wrapping & GPS auto-sync)
  - .gitignore              (Ignores data/fasalsaarathi_users.db & uploads)

Newly Created Backend Files (6):
  - tools/auth_tool.py
  - tools/insurance_tool.py
  - tools/passbook_tool.py
  - routes/auth_routes.py
  - routes/insurance_routes.py
  - routes/passbook_routes.py

Newly Created Frontend Files (4):
  - templates/login.html
  - static/js/auth.js
  - static/js/insurance.js
  - static/js/passbook.js

Newly Created Automated Tests (3):
  - tests/test_auth_tool.py
  - tests/test_insurance_tool.py
  - tests/test_passbook_tool.py

-----------------------------------------------------------------------------
3. HOW TO MERGE INTO YOUR EXISTING PROJECT ON ANOTHER LAPTOP
-----------------------------------------------------------------------------
1. Copy ALL folders/files inside "FasalSaarathi_New_Features" (except
   README.txt if you want to keep your original README.md) and paste them
   directly into the root of your existing FasalSaarathi project folder,
   choosing "Replace files in destination" when asked.
2. Dependencies: No new pip packages are required beyond your existing
   requirements.txt (Flask, Werkzeug, Pillow, Requests).
   If not yet installed:
     pip install -r requirements.txt
3. Run the unit tests to verify everything works:
     python -m unittest tests/test_auth_tool.py tests/test_insurance_tool.py tests/test_passbook_tool.py -v
4. Start the app:
     python app.py
   Open http://127.0.0.1:5000 (Login page is at http://127.0.0.1:5000/login).
   Note: `data/fasalsaarathi_users.db` will be created automatically on first run.
