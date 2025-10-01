# WhatsApp Quiz Game (Flask + Twilio Sandbox)

A lightweight 5-question quiz about Singapore that runs on WhatsApp via Twilio's Sandbox. Backend is a minimal Flask app (no DB) intended for demos and learning.

## Features
- Start with `START`, optional `HELP` for instructions
- Sequential Q&A with immediate feedback and explanations
- Final summary with score and percentage, then reset
- Questions are editable in `questions.json` (no code changes needed)

## Tech
- Python 3.10+
- Flask (only dependency)
- Twilio WhatsApp Sandbox
- Deployable on Render.com free tier

## Project Structure
```
whatsapp-quiz/
├── app.py            # Flask app with /whatsapp webhook (TwiML responses)
├── questions.json    # Quiz content (editable)
├── requirements.txt  # Flask==3.0.3
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

## Deploy to Render
- Push this repo to GitHub
- Create a new Web Service in Render
  - Build Command: `pip install -r requirements.txt`
  - Start Command: `python app.py`
  - Environment: `PORT=3000` (the app also respects Render-assigned PORT)
- Set Twilio webhook to: `https://<your-app>.onrender.com/whatsapp`

## Notes
- Sessions are in-memory (by sender phone); they reset on server restarts
- Always returns TwiML XML (no plain text endpoints for WhatsApp)
- Future ideas: `HINT` command using the optional `hint` field, Redis for persistence, images

---
Questions are defined in `questions.json`. Keep each `options` list at 4 items labeled like `"A) ..."`, `"B) ..."`, etc., and make `answer` one of `A/B/C/D`.
