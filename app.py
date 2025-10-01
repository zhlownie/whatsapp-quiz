import os
import json
from flask import Flask, request, Response
from xml.sax.saxutils import escape

app = Flask(__name__)

# In-memory session store: { from_number: { index: int, score: int } }
sessions = {}


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
        if not isinstance(opts, list) or len(opts) != 4 or not all(isinstance(o, str) for o in opts):
            raise ValueError(f"Question {i}: 'options' must be a list of 4 strings")
        ans = q.get("answer")
        if not isinstance(ans, str) or ans.upper() not in ("A", "B", "C", "D"):
            raise ValueError(f"Question {i}: 'answer' must be one of A/B/C/D")
        # Normalize answer to uppercase for grading
        q["answer"] = ans.upper()
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
    letters = ["A", "B", "C", "D"]

    rendered_options = []
    for idx, opt in enumerate(q["options"]):
        letter = letters[idx]
        if sandbox_number:
            rendered_options.append(
                f"{opt} — tap: https://wa.me/{sandbox_number}?text={letter}"
            )
        else:
            rendered_options.append(opt)

    options = "\n".join(rendered_options)  # Expect options already prefixed with A/B/C/D
    return (
        f"Q{i+1}/{len(QUESTIONS)}: {q['question']}\n{options}\n\n"
        "Reply with A, B, C, or D (or 1–4)."
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

    # Commands
    if lower in ("start", "restart"):
        sessions[from_number] = {"index": 0, "score": 0}
        welcome = (
            f"Welcome to the Singapore Quiz! You will get {len(QUESTIONS)} questions.\n\n"
            + format_question(0)
        )
        return twiml(welcome)

    if lower in ("help", "?"):
        return twiml(
            "Send START to begin. Answer with A–D or 1–4. Send START anytime to restart. Send HINT for a clue."
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

    # Normalize and validate answer
    norm = normalize_answer(body)
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
    next_q = format_question(state["index"])
    return twiml(f"{feedback}{expl_line}\n\n{next_q}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    app.run(host="0.0.0.0", port=port)
