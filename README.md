# WhatsApp Quiz Game (Flask + Twilio)

A lightweight 5-question quiz about Singapore that runs on WhatsApp using Twilio. It supports:

- Sandbox text replies (returns TwiML)
- Production interactive Quick Reply buttons via Twilio Content API (optional)

Backend is a minimal Flask app (no DB) intended for demos and learning.

## Features
- Start with `START`, optional `HELP` for instructions
- Sequential Q&A with immediate feedback and explanations
- Final summary with score and percentage, then reset
- Questions are editable in `questions.json` (no code changes needed)
- Optional interactive buttons (Quick Replies) when using a production WhatsApp sender + Content API

## Tech
- Python 3.10+
- Flask + Twilio Python SDK
- Twilio WhatsApp (Sandbox for text; production sender for buttons)
- Deployable on Render.com free tier

## Project Structure
```
whatsapp-quiz/
├── app.py            # Flask app with /whatsapp webhook (TwiML + optional interactive buttons)
├── questions.json    # Quiz content (editable)
├── requirements.txt  # Flask + twilio
└── README.md
```

## Local Run (Windows PowerShell)
```powershell
cd c:\copilot_projects\whatsapp-quiz
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PORT=3000
python app.py
```

## Expose Locally and Connect Twilio Sandbox
1) Start a tunnel (ngrok or similar)
```powershell
npx ngrok http 3000
```
2) In Twilio Console → Messaging → Try it out → WhatsApp Sandbox
- Join the sandbox by sending the join code to the WhatsApp number
- Set "When a message comes in" (POST) to: `https://YOUR_NGROK_ID.ngrok.io/whatsapp`

3) Test in WhatsApp
- Send `START`
- Answer with `A`, `B`, `C`, or `D`

## Modes: Sandbox vs. Production

- Sandbox (default):
  - No real buttons in the WhatsApp Sandbox UI; users reply with A/B/C (or 1/2/3)
  - App responds with TwiML text messages only

- Production Interactive (optional):
  - Uses Twilio Content API to send WhatsApp messages with up to 3 Quick Reply buttons
  - App auto-enables buttons when all required credentials are present (see below). You can force-disable with `USE_TWILIO_INTERACTIVE=0`.

## Production Interactive Setup (Twilio Content API)

1) Create a Content Template (Twilio Console → Content → Templates):
   - Channel: WhatsApp
   - Body text: include a variable for the question, e.g. `{{1}}`
   - Add up to 3 Quick Reply buttons. For dynamic button titles, define variables for each, e.g. `{{btn1_title}}`, `{{btn2_title}}`, `{{btn3_title}}`
   - Submit for approval and note the resulting Content SID (e.g. `HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

2) Set environment variables (locally or in your host, e.g., Render):
   - `TWILIO_ACCOUNT_SID` = your Account SID
   - `TWILIO_AUTH_TOKEN` = your Auth Token
   - `TWILIO_FROM` = your approved WhatsApp sender, e.g. `whatsapp:+1XXXXXXXXXX`
   - `TWILIO_CONTENT_SID_BUTTONS` = the approved Content SID from step 1
   - Optional: `USE_TWILIO_INTERACTIVE=0` to force text-only mode

3) How variables are passed (example):

```jsonc
{
  "1": "Which year did Singapore gain full independence?",
  "btn1_title": "A) 1959",
  "btn2_title": "B) 1963",
  "btn3_title": "C) 1965"
}
```

The app builds this `content_variables` JSON for each question and sends it with `content_sid=TWILIO_CONTENT_SID_BUTTONS`.

## Deploy to Render
- Push this repo to GitHub
- Create a new Web Service in Render
  - Build Command: `pip install -r requirements.txt`
  - Start Command: `python app.py`
  - Environment: `PORT=3000` (the app also respects Render-assigned PORT)
- Set Twilio webhook to: `https://<your-app>.onrender.com/whatsapp`
- For interactive buttons in production, also add the env vars listed above (Account SID, Auth Token, From, Content SID). The app auto-enables buttons if these are set.

## Notes
- Sessions are in-memory (by sender phone); they reset on server restarts
- In Sandbox, the app responds with TwiML text; in production with Content API configured, it sends interactive Quick Reply buttons
- You can force-disable buttons with `USE_TWILIO_INTERACTIVE=0` if needed

---
Questions are defined in `questions.json`. For interactive buttons, keep each question to 3 options and set `"quick_replies": ["A","B","C"]`. The app will map those to up to three Quick Reply buttons in production; in Sandbox, users reply with `A/B/C` (or `1/2/3`).

## Troubleshooting

- No buttons show up in WhatsApp
  - You’re likely on the Sandbox or missing Content API config. Verify env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`, `TWILIO_CONTENT_SID_BUTTONS`.
  - Ensure your WhatsApp sender is approved (non-sandbox) and the Content Template is approved for WhatsApp.
  - Set `USE_TWILIO_INTERACTIVE=1` to force-enable (or `0` to disable) for testing.

- “The From phone number is not a valid WhatsApp sender”
  - `TWILIO_FROM` must be in the format `whatsapp:+<number>` and be a provisioned WhatsApp sender in your account.

- Template variables don’t render or show curly braces
  - Confirm your Content Template includes the variables used by this app: `{{1}}`, `{{btn1_title}}`, `{{btn2_title}}`, `{{btn3_title}}`.
  - The app sends `content_variables` as a JSON string with keys `"1"`, `"btn1_title"`, etc.

- Wrong or inconsistent answer matching
  - In production buttons mode, the app sends clean option text as button titles and also matches typed `A/B/C`.
  - In Sandbox text mode, reply with `A/B/C` (or `1/2/3`). Use `HINT` when available.

- Nothing happens after sending START
  - Check Twilio webhook URL points to `/whatsapp` and is reachable (ngrok or deployed URL).
  - Look at server logs for the `>>> INCOMING WEBHOOK PAYLOAD:` line to confirm the webhook fires.

- Render deploy succeeds but env changes don’t take effect
  - Redeploy after updating environment variables. Some platforms require a restart to apply env changes.
