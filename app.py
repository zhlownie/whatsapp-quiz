import os
import json
from flask import Flask, request, Response
from xml.sax.saxutils import escape
from typing import List, Tuple

# Twilio client (only used when USE_TWILIO_INTERACTIVE=1)
try:
    from twilio.rest import Client  # type: ignore
except ImportError:
    Client = None

app = Flask(__name__)

# In-memory session store: { from_number: { index: int, score: int } }
sessions = {}

# Production interactive config (disabled by default)
USE_TWILIO_INTERACTIVE = os.environ.get("USE_TWILIO_INTERACTIVE", "0") == "1"
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM")  # e.g., 'whatsapp:+14155551234'
TWILIO_CONTENT_SID_BUTTONS = os.environ.get("TWILIO_CONTENT_SID_BUTTONS")  # Content template SID

twilio_client = None
if USE_TWILIO_INTERACTIVE:
    if Client is None:
        raise RuntimeError("twilio package not installed. Add twilio to requirements.txt")
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM):
        raise RuntimeError("Interactive mode requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM")
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def load_questions():
    """Load and validate questions from questions.json.

    Expected schema per item:
    - question: str
    - options: list[str] of length 4
    - answer: str in {A,B,C,D} (case-insensitive)
    - hint: Optional[str]
    - explanation: Optional[str]
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "questions.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or not data:
        raise ValueError("questions.json must be a non-empty list of questions")

    for i, q in enumerate(data, start=1):
        if not isinstance(q, dict):
            raise ValueError(f"Question {i}: must be an object")
        if not isinstance(q.get("question"), str):
            raise ValueError(f"Question {i}: 'question' must be a string")
        opts = q.get("options")
        if not isinstance(opts, list) or not (2 <= len(opts) <= 4) or not all(isinstance(o, str) for o in opts):
            raise ValueError(f"Question {i}: 'options' must be a list of 2..4 strings")
        ans = q.get("answer")
        allowed_letters = ["A", "B", "C", "D"][: len(opts)]
        if not isinstance(ans, str) or ans.upper() not in allowed_letters:
            raise ValueError(f"Question {i}: 'answer' must be one of {', '.join(allowed_letters)}")
        # Normalize answer to uppercase for grading
        q["answer"] = ans.upper()
        # Optional quick_replies subset (<=3) for production buttons
        qr = q.get("quick_replies")
        if qr is not None:
            if not isinstance(qr, list) or not all(isinstance(x, str) for x in qr):
                raise ValueError(f"Question {i}: 'quick_replies' must be a list of strings if present")
            seen = set()
            qr_norm: List[str] = []
            for x in qr:
                u = x.upper().strip()
                if u in allowed_letters and u not in seen:
                    qr_norm.append(u)
                    seen.add(u)
            if len(qr_norm) == 0 or len(qr_norm) > 3:
                raise ValueError(f"Question {i}: 'quick_replies' must contain 1..3 unique letters within {allowed_letters}")
            q["quick_replies"] = qr_norm
        if "hint" in q and not isinstance(q["hint"], str):
            raise ValueError(f"Question {i}: 'hint' must be a string if present")
        if "explanation" in q and not isinstance(q["explanation"], str):
            raise ValueError(f"Question {i}: 'explanation' must be a string if present")

    return data


QUESTIONS = load_questions()


def format_question(i: int) -> str:
    q = QUESTIONS[i]
    # Optional tap-to-prefill links (set SANDBOX_NUMBER=14155238886 on Render)
    sandbox_number = os.environ.get("SANDBOX_NUMBER")  # digits only, no '+'
    allowed = ["A", "B", "C", "D"][: len(q["options"])]

    rendered_options = []
    for idx, opt in enumerate(q["options"]):
        letter = allowed[idx]
        if sandbox_number:
            rendered_options.append(
                f"{opt} — tap: https://wa.me/{sandbox_number}?text={letter}"
            )
        else:
            rendered_options.append(opt)

    options = "\n".join(rendered_options)
    return (
        f"Q{i+1}/{len(QUESTIONS)}: {q['question']}\n{options}\n\n"
        f"Reply with A–{allowed[-1]} (or 1–{len(allowed)})."
    )


def normalize_answer(text: str):
    """
    Normalize user input to 'A'|'B'|'C'|'D' or None if invalid.
    Accepts: a/A/a)/a., 1/2/3/4, trims whitespace.
    """
    if not text:
        return None
    s = text.strip().lower()

    # Map digits 1-4 to letters
    digit_map = {"1": "A", "2": "B", "3": "C", "4": "D"}
    if s in digit_map:
        return digit_map[s]

    # Accept forms like 'a', 'a)', 'a.', 'a:' etc.
    if s and s[0] in ("a", "b", "c", "d"):
        first = s[0]
        if len(s) == 1 or s[1] in (")", ".", ":", "-", " "):
            return first.upper()

    return None


def twiml(message: str) -> Response:
    """Return a TwiML XML response with a single Message node."""
    xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        f"<Response><Message>{escape(message)}</Message></Response>"
    )
    return Response(xml, mimetype="application/xml")


@app.get("/")
def health():
    return "OK", 200


@app.post("/whatsapp")
def whatsapp():
    from_number = request.form.get("From", "unknown")
    body = (request.form.get("Body") or "").strip()
    lower = body.lower()
    # Interactive payloads (production buttons)
    button_payload = request.form.get("ButtonPayload") or request.form.get("buttonPayload")

    # Commands
    if lower in ("start", "restart"):
        sessions[from_number] = {"index": 0, "score": 0}
        welcome_text = f"Welcome to the Singapore Quiz! You will get {len(QUESTIONS)} questions."
        if USE_TWILIO_INTERACTIVE:
            send_text(from_number, welcome_text)
            send_question_interactive(from_number, 0)
            return ("OK", 200)
        else:
            return twiml(welcome_text + "\n\n" + format_question(0))

    if lower in ("help", "?"):
        return twiml(
            "Send START to begin. In production: tap buttons. In sandbox: reply with A–D or 1–4. Send HINT for a clue."
        )

    # Optional: HINT command
    if lower == "hint":
        state = sessions.get(from_number)
        if not state:
            return twiml("Send START to begin the quiz.")
        q_index = state["index"]
        hint = QUESTIONS[q_index].get("hint")
        return twiml(hint if hint else "No hint available for this question.")

    # Require a session
    state = sessions.get(from_number)
    if not state:
        return twiml("Send START to begin the quiz. Answer with A, B, C, or D.")

    # Normalize and validate answer (prefer interactive payload if present)
    raw_answer = (button_payload or body)
    norm = normalize_answer(raw_answer)
    if not norm:
        return twiml("Please reply with A–D or 1–4. Send HINT for a clue, or START to restart.")

    # Grade current question
    q_index = state["index"]
    correct_letter = QUESTIONS[q_index]["answer"]  # already uppercase
    is_correct = (norm == correct_letter)
    if is_correct:
        state["score"] += 1
        feedback = "✅ Correct!"
    else:
        feedback = f"❌ Not quite. Correct answer: {correct_letter}."

    # Advance index
    state["index"] += 1

    # Optional explanation
    expl = QUESTIONS[q_index].get("explanation")
    expl_line = f"\nℹ️ {expl}" if expl else ""

    # Finished?
    if state["index"] >= len(QUESTIONS):
        score = state["score"]
        total = len(QUESTIONS)
        pct = round((score / total) * 100)
        if pct == 100:
            fun = "Perfect! 🇸🇬🌟"
        elif pct >= 80:
            fun = "Great job! 🎉"
        elif pct >= 50:
            fun = "Nice effort! 👍"
        else:
            fun = "Keep practicing! 💪"
        # Reset session
        sessions.pop(from_number, None)
        return twiml(
            f"{feedback}{expl_line}\n\nQuiz complete! Score: {score}/{total} ({pct}%). {fun}\nSend START to play again."
        )

    # Next question
    if USE_TWILIO_INTERACTIVE:
        send_text(from_number, f"{feedback}{expl_line}")
        send_question_interactive(from_number, state["index"])
        return ("OK", 200)
    else:
        next_q = format_question(state["index"])
        return twiml(f"{feedback}{expl_line}\n\n{next_q}")


# ----- Outbound helpers for production interactive mode -----
def send_text(to_whatsapp: str, body: str):
    assert twilio_client is not None
    twilio_client.messages.create(from_=TWILIO_FROM, to=to_whatsapp, body=body)


def send_buttons(to_whatsapp: str, title: str, body: str, buttons: List[Tuple[str, str]]):
    """Send Quick Reply buttons via Twilio Content API (max 3)."""
    assert twilio_client is not None
    if not TWILIO_CONTENT_SID_BUTTONS:
        lines = "\n".join([f"- {t}" for _, t in buttons])
        return send_text(to_whatsapp, f"{title}\n\n{body}\n\n{lines}")

    vars_obj = {"title": title, "body": body}
    for idx, (btn_id, btn_title) in enumerate(buttons, start=1):
        vars_obj[f"btn{idx}_id"] = btn_id
        vars_obj[f"btn{idx}_title"] = btn_title

    twilio_client.messages.create(
        from_=TWILIO_FROM,
        to=to_whatsapp,
        content_sid=TWILIO_CONTENT_SID_BUTTONS,
        content_variables=json.dumps(vars_obj),
    )


def send_question_interactive(to_whatsapp: str, i: int):
    q = QUESTIONS[i]
    title = f"Q{i+1}/{len(QUESTIONS)}"
    body = q["question"]
    allowed = ["A", "B", "C", "D"][: len(q["options"])]
    letters = q.get("quick_replies") or allowed[:3]
    buttons: List[Tuple[str, str]] = []
    for letter in letters:
        idx = allowed.index(letter)
        buttons.append((letter, q["options"][idx]))
    send_buttons(to_whatsapp, title, body, buttons)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
