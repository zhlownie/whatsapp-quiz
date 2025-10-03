import os
import json
from flask import Flask, request, Response, send_from_directory
from xml.sax.saxutils import escape

# Twilio client
try:
    from twilio.rest import Client
except ImportError:
    Client = None

app = Flask(__name__)
sessions = {}

# Load config from environment
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM")
TWILIO_CONTENT_SID_BUTTONS = os.environ.get("TWILIO_CONTENT_SID_BUTTONS")
TWILIO_CONTENT_SID_IMAGE = os.environ.get("TWILIO_CONTENT_SID_IMAGE")

USE_TWILIO_INTERACTIVE = (
    os.environ.get("USE_TWILIO_INTERACTIVE", "0") == "1"
    and TWILIO_ACCOUNT_SID
    and TWILIO_AUTH_TOKEN
    and TWILIO_FROM
    and TWILIO_CONTENT_SID_BUTTONS
    and TWILIO_CONTENT_SID_IMAGE
)

twilio_client = None
if USE_TWILIO_INTERACTIVE:
    if Client is None:
        raise RuntimeError("Install 'twilio' package")
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def load_questions():
    with open("questions.json", "r", encoding="utf-8") as f:
        return json.load(f)


QUESTIONS = load_questions()


# Serve static files (e.g., static/images/merlion.jpg)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


def twiml(message: str) -> Response:
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(message)}</Message></Response>'
    return Response(xml, mimetype="application/xml")


@app.post("/whatsapp")
def whatsapp():
    from_number = request.form.get("From", "unknown")
    body = (request.form.get("Body") or "").strip()

    if body.lower() in ("start", "restart"):
        sessions[from_number] = {"index": 0, "score": 0}
        welcome = f"Welcome to the Singapore Quiz! {len(QUESTIONS)} questions await. Tap a button to answer."
        if USE_TWILIO_INTERACTIVE:
            send_text(from_number, welcome)
            send_question_interactive(from_number, 0)
            return ("OK", 200)
        else:
            q = QUESTIONS[0]
            options = "\n".join(q["options"])
            return twiml(f"{welcome}\n\n{q['question']}\n{options}")

    if body.lower() == "hint":
        state = sessions.get(from_number)
        if not state:
            return twiml("Send START first.")
        q = QUESTIONS[state["index"]]
        return twiml(q.get("hint", "No hint available."))

    state = sessions.get(from_number)
    if not state:
        return twiml("Send START to begin the quiz.")

    q_index = state["index"]
    current_q = QUESTIONS[q_index]
    user_answer = body.strip()

    if user_answer not in current_q["options"]:
        valid_opts = "\n".join(current_q["options"])
        return twiml(f"Invalid choice. Please select one of:\n{valid_opts}")

    is_correct = (user_answer == current_q["answer"])
    if is_correct:
        state["score"] += 1
        feedback = "✅ Correct!"
    else:
        feedback = f"❌ Incorrect. The answer is: {current_q['answer']}."

    state["index"] += 1
    expl = f"\nℹ️ {current_q.get('explanation', '')}" if current_q.get("explanation") else ""

    if state["index"] >= len(QUESTIONS):
        score = state["score"]
        total = len(QUESTIONS)
        pct = round((score / total) * 100)
        msg = f"{feedback}{expl}\n\nQuiz complete! Score: {score}/{total} ({pct}%)."
        if pct == 100:
            msg += " 🇸🇬 Perfect!"
        sessions.pop(from_number, None)
        return twiml(msg + "\nSend START to play again.")

    if USE_TWILIO_INTERACTIVE:
        send_text(from_number, f"{feedback}{expl}")
        send_question_interactive(from_number, state["index"])
        return ("OK", 200)
    else:
        next_q = QUESTIONS[state["index"]]
        options = "\n".join(next_q["options"])
        return twiml(f"{feedback}{expl}\n\n{next_q['question']}\n{options}")


# --- Twilio outbound helpers ---
def send_text(to_whatsapp: str, body: str):
    twilio_client.messages.create(from_=TWILIO_FROM, to=to_whatsapp, body=body)


def send_question_interactive(to_whatsapp: str, i: int):
    q = QUESTIONS[i]
    
    if "image_url" in q:
        # ✅ MESSAGE 1: Send image using relative path
        twilio_client.messages.create(
            from_=TWILIO_FROM,
            to=to_whatsapp,
            content_sid=TWILIO_CONTENT_SID_IMAGE,
            content_variables=json.dumps({"1": q["image_url"]}, separators=(',', ':'))
        )
        
        # ✅ MESSAGE 2: Send question + buttons
        vars_obj = {
            "1": q["question"],
            "btn1_title": q["options"][0],
            "btn2_title": q["options"][1],
            "btn3_title": q["options"][2]
        }
        twilio_client.messages.create(
            from_=TWILIO_FROM,
            to=to_whatsapp,
            content_sid=TWILIO_CONTENT_SID_BUTTONS,
            content_variables=json.dumps(vars_obj, separators=(',', ':'))
        )
    else:
        # Text-only question
        vars_obj = {"1": q["question"]}
        for idx, btn_text in enumerate(q["options"], start=1):
            vars_obj[f"btn{idx}_title"] = btn_text
        twilio_client.messages.create(
            from_=TWILIO_FROM,
            to=to_whatsapp,
            content_sid=TWILIO_CONTENT_SID_BUTTONS,
            content_variables=json.dumps(vars_obj, separators=(',', ':'))
        )


@app.get("/")
def health():
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)