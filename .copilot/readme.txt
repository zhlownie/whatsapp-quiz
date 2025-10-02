Project: WhatsApp Quiz Game

Overview:
A lightweight, interactive 5-question quiz about Singapore that users can play directly on WhatsApp using Twilio's free Sandbox. The backend is a Python Flask app deployed on Render.com. No phone number registration or business verification is required—ideal for personal use or small-group testing.

Core Behavior:
- User sends "join <sandbox-key>" to Twilio's sandbox number to opt in
- User sends "START" to begin the quiz
- Bot asks questions sequentially: Q1 → Q2 → Q3 → Q4 → Q5
- After each answer (A/B/C/D), user gets immediate feedback + moves to next question
- After Q5, bot shows final score, percentage, and a fun message
- Game resets automatically—user can type "START" again to replay

Data Structure:
- All quiz content is stored in `questions.json` (NOT hardcoded in Python)
- Each question object includes:
    - "question": string
    - "options": list of 4 strings (A, B, C, D)
    - "answer": single letter ("A", "B", etc.)
    - "hint": optional string (for future "HINT" command)
    - "explanation": fun fact shown after answering
- Example:
    {
      "question": "What is Singapore's national flower?",
      "options": ["A) Vanda Miss Joaquim", "B) Hibiscus", ...],
      "answer": "A",
      "hint": "It's a type of orchid.",
      "explanation": "Chosen in 1981 for its resilience..."
    }

Technical Stack:
- Language: Python 3.10+
- Web Framework: Flask (only external dependency)
- Hosting: Render.com (free tier)
- WhatsApp API: Twilio Sandbox (no-cost, no approval needed)
- Session Management: In-memory dictionary (key = sender's WhatsApp number from 'From' field)
- No database (state resets on app restart—acceptable for demo)

File Structure:
- app.py: Main Flask app with /whatsapp webhook
- questions.json: Quiz content (editable by non-developers)
- requirements.txt: Only "Flask==3.0.3"
- .copilot/readme.txt: This file (for AI context)

Deployment:
- Push to GitHub
- Create Web Service on Render.com
- Build Command: pip install -r requirements.txt
- Start Command: python app.py
- Port: 3000 (app uses os.environ.get('PORT', 3000))
- Set Twilio webhook URL to: https://<your-app>.onrender.com/whatsapp

Important Notes for AI Assistance:
- NEVER hardcode questions in app.py—always load from questions.json
- ALWAYS return TwiML XML (not plain text) in webhook responses
- Use built-in `json` module—no extra dependencies needed
- Keep logic simple and stateless where possible
- Future features may include: HINT command, image replies, PostgreSQL for scores

This project is designed to be minimal, educational, and easy to extend.


whatsapp-quiz/
├── .copilot/
│   └── readme.txt   ← this file
├── app.py
├── questions.json
├── requirements.txt
└── README.md


