# Meta WhatsApp Cloud API — Two-Way Voice Notes Setup Guide

KrishiMitra (Farm Advisor) supports live, two-way WhatsApp voice notes powered by:
- **Sarvam AI `saaras:v4` Speech-to-Text (STT)** with agricultural domain terminology and automatic Indic language detection.
- **Gemini 2.5 Flash + 5 Agricultural Tools** for real-time Mandi prices, weather advisories, dairy procurement rates, farm finances, and government scheme deadlines.
- **Sarvam AI `bulbul:v3` Text-to-Speech (TTS)** for spoken farm advisory responses.
- **FFmpeg Opus conversion** converting spoken replies to mono `audio/ogg` (`24k` bitrate, `<= 512 KB`) for the native WhatsApp inline voice-note player bubble.
- **Concise follow-up text summary** with key prices, spray timings, and dosages.

---

## 1. Configure Environment Variables (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and configure your API keys:

```bash
# Google Gemini API key (for agricultural reasoning & tool calling)
GEMINI_API_KEY="AIzaSy..."

# Sarvam AI API key (for Indic STT saaras:v4 & TTS bulbul:v3)
SARVAM_API_KEY="your_sarvam_api_key_here"

# Meta WhatsApp Cloud API credentials
WHATSAPP_VERIFY_TOKEN=krishimitra_verify
WHATSAPP_ACCESS_TOKEN="EAA..."
WHATSAPP_PHONE_NUMBER_ID="109876543210987"
```

---

## 2. Start the Backend & Expose via Public Tunnel

Meta WhatsApp Cloud API webhooks require a publicly accessible HTTPS endpoint.

### Start the FastAPI backend:
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Expose port 8000 using ngrok:
```bash
ngrok http 8000
```
*Note the HTTPS forwarding URL, e.g., `https://xyz-abc.ngrok-free.app`.*

### Alternatively, expose using Cloudflare Tunnel:
```bash
cloudflared tunnel --url http://localhost:8000
```
*Note the trycloudflare HTTPS URL, e.g., `https://abc-123.trycloudflare.com`.*

---

## 3. Register the Webhook in Meta Developer Portal

1. Navigate to the [Meta for Developers Console](https://developers.facebook.com/apps/).
2. Select your WhatsApp App and click **WhatsApp** > **Configuration** in the left sidebar.
3. In the **Webhook** section, click **Edit**:
   - **Callback URL:** `https://<YOUR_TUNNEL_URL>/api/whatsapp/webhook`
   - **Verify Token:** `krishimitra_verify` (matching `WHATSAPP_VERIFY_TOKEN`)
4. Click **Verify and Save**. Meta will send a `GET` challenge to `/api/whatsapp/webhook` and verify the handshake.
5. In the Webhook fields list, click **Manage** and subscribe to **`messages`**.

---

## 4. Test Live Two-Way Voice Notes

1. Save your test phone number in the Meta WhatsApp Developer test dashboard under **To**.
2. Open WhatsApp on your phone and send a voice note asking:
   > *"What is the current paddy price in Davangere APMC?"* (or speak in Kannada: *"ದಾವಣಗೆರೆ ಎಪಿಎಂಸಿಯಲ್ಲಿ ಇವತ್ತಿನ ಭತ್ತದ ಧಾರಣೆ ಎಷ್ಟಿದೆ?"*)
3. The backend executes:
   - Reads incoming `audio` webhook payload and sends a **read receipt**.
   - Retrieves media metadata from `GET /v26.0/{media_id}` and downloads the raw OGG audio bytes.
   - Transcribes query using Sarvam AI `saaras:v4` with agricultural domain keyterms.
   - Executes Gemini tool calling for APMC mandi rates.
   - Synthesizes spoken reply via Sarvam AI TTS in the matching language.
   - Converts audio to mono `audio/ogg` (Opus, `24k` bitrate) using FFmpeg.
   - Uploads to `POST /v26.0/{phone_number_id}/media` and sends a native voice-note bubble (`voice: true`).
   - Sends a concise text summary with prices and dosages.

---

## 5. Offline & Local Simulation

You can test the entire voice note workflow locally without Meta credentials using the simulation endpoint:

```bash
curl -X POST http://localhost:8000/api/whatsapp/simulate \
  -H "Content-Type: application/json" \
  -d '{"type": "audio", "from": "919876543210"}'
```
Returns:
```json
{
  "status": "success",
  "result": {
    "type": "audio",
    "transcript": "...",
    "reply_text": "...",
    "reply_audio_base64": "...",
    "voice": true,
    "summary_text": "..."
  }
}
```
