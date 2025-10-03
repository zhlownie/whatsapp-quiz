Project: WhatsApp Quiz Game

Overview:
Lightweight WhatsApp quiz about Singapore. Works in two modes:
- Sandbox (text replies via TwiML)
- Production (interactive Quick Reply buttons via Twilio Content API)

Backend is a minimal Python Flask app deployed on Render.com. No DB; ideal for demos and small tests.

Core Behavior:
- User sends START to begin
- Bot asks questions sequentially and gives immediate feedback
- Final score and fun message at the end; user can START again to replay
- Sandbox: user types the exact option text
- Production: user taps one of up to 3 Quick Reply buttons (button titles match option text)

Data Structure (questions.json):
- All quiz content lives in questions.json (NOT hardcoded)
- Each question object includes:
  - "question": string
  - "options": list of 3 strings (clean text, no "A)" prefixes)
  - "answer": string (must exactly equal one of the options)
  - "hint": optional string (shown on HINT)
  - "explanation": optional string (shown after answering)
  - "image_url": optional string path to a local static asset (e.g., "/static/images/merlion.jpg") used in production templates

Example:
{
  "question": "What is the national flower of Singapore?",
  "options": ["Vanda Miss Joaquim", "Hibiscus", "Lotus"],
  "answer": "Vanda Miss Joaquim",
  "hint": "It's a type of orchid.",
  "explanation": "Chosen in 1981 for its resilience..."
}

Technical Stack:
- Language: Python 3.10+
- Web Framework: Flask
- WhatsApp API: Twilio (Sandbox for text; production sender for buttons)
- Hosting: Render.com (free tier)
- Session Management: In-memory dict keyed by From (resets on app restart)
- Dependencies: Flask, twilio (see requirements.txt)

File Structure:
- app.py: Flask app with /whatsapp webhook; TwiML for Sandbox; Content API for production
- questions.json: Quiz content (editable by non-developers)
- static/images/: Local images referenced by questions via image_url
- requirements.txt: Flask + twilio
- README.md: Setup, deployment, and modes
- .github/copilot-instructions.md: This file (for AI guidance)

Deployment:
- Push to GitHub
- Create Web Service on Render.com
  - Build Command: pip install -r requirements.txt
  - Start Command: python app.py
  - Port: 3000 (or environment PORT)
- Set Twilio webhook URL to: https://<your-app>.onrender.com/whatsapp

Production Interactive (Twilio Content API):
- Create a Content Template in Twilio Console → Content → Templates (channel: WhatsApp)
- Include variables used by the app:
  - {{1}} = question text (required)
  - Optional media/image variable (e.g., {{2}}) if your template supports an image
  - {{btn1_title}}, {{btn2_title}}, {{btn3_title}} = Quick Reply button titles
- Required environment variables:
  - TWILIO_ACCOUNT_SID
  - TWILIO_AUTH_TOKEN
  - TWILIO_FROM (e.g., whatsapp:+1XXXXXXXXXX)
  - TWILIO_CONTENT_SID_BUTTONS (approved Content SID)
  - USE_TWILIO_INTERACTIVE=1 to enable interactive mode
- In interactive mode, the webhook returns HTTP 200 and sends outbound messages via Twilio REST. In Sandbox mode, it returns TwiML.

Important Notes for AI Assistance:
- Do NOT hardcode questions in app.py—always load from questions.json
- Keep options as clean text (3 items) and ensure "answer" exactly matches one option
- For Sandbox mode, return TwiML XML; for production interactive, send via Content API and return 200 OK
- Images: questions may include image_url as a path under /static. The app serves /static and builds a public URL for templates. If deployment hostname changes, ensure image URLs resolve (consider an env var for base URL if modifying)
- Only standard libs + Flask + twilio—avoid adding dependencies unless requested
- State is in-memory and resets on restart (acceptable for demo)
- No letter shortcuts (A/B/C). Users select/tap exact option text. Do not reintroduce mapping unless explicitly asked

This project is intentionally minimal and easy to extend. Future ideas: score persistence, richer content, analytics.


your-repo/
├── app.py
├── questions.json          # (with optional image_url on some questions)
├── static/
│   └── images/
│       └── merlion.jpg
├── requirements.txt
├── README.md
└── .github/
    └── copilot-instructions.md


