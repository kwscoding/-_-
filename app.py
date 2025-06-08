from flask import Flask, render_template, request, redirect, jsonify, session, url_for
import json
import os
import random

app = Flask(__name__)
app.secret_key = "random-secret-key"
DATA_PATH = "vocab.json"
WRONG_NOTE_PATH = "wrong_note.json"

def load_vocab():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_vocab(words):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

def load_wrong_note():
    if os.path.exists(WRONG_NOTE_PATH):
        with open(WRONG_NOTE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_wrong_note(note):
    with open(WRONG_NOTE_PATH, "w", encoding="utf-8") as f:
        json.dump(note, f, ensure_ascii=False, indent=2)

@app.route("/")
def index():
    words = load_vocab()
    q = request.args.get("q", "").strip()
    filter_mode = request.args.get("filter", "all")
    sort_mode = request.args.get("sort", "recent")
    filtered = []
    for w in words:
        if q and not (
            q.lower() in w["word"].lower() or
            q in w["meaning"] or
            q in w.get("example", "") or
            q in w.get("tags", "")
        ):
            continue
        if filter_mode == "memorized" and not w.get("memorized", False):
            continue
        if filter_mode == "not_memorized" and w.get("memorized", False):
            continue
        filtered.append(w)
    if sort_mode == "alpha":
        filtered.sort(key=lambda x: x["word"].lower())
    elif sort_mode == "memorized":
        filtered.sort(key=lambda x: (not x.get("memorized", False), x["word"].lower()))
    else:
        pass
    memorized_cnt = sum(1 for w in filtered if w.get("memorized", False))
    return render_template("index.html", words=filtered, total=len(filtered), memorized=memorized_cnt,
                           q=q, filter_mode=filter_mode, sort_mode=sort_mode)

@app.route("/add", methods=["GET", "POST"])
def add_word():
    if request.method == "POST":
        word = request.form["word"].strip()
        meaning = request.form["meaning"].strip()
        example = request.form.get("example", "").strip()
        pos = request.form.get("pos", "").strip()
        tags = request.form.get("tags", "").strip()
        words = load_vocab()
        if any(w["word"].lower() == word.lower() for w in words):
            return render_template("add_word.html", error="이미 등록된 단어입니다!", word=word, meaning=meaning, example=example, pos=pos, tags=tags)
        words.append({"word": word, "meaning": meaning, "example": example, "pos": pos, "tags": tags, "memorized": False})
        save_vocab(words)
        return redirect("/")
    return render_template("add_word.html", error=None)

@app.route("/edit/<word>", methods=["GET", "POST"])
def edit_word(word):
    words = load_vocab()
    entry = next((w for w in words if w["word"] == word), None)
    if not entry:
        return redirect("/")
    if request.method == "POST":
        entry["meaning"] = request.form["meaning"].strip()
        entry["example"] = request.form.get("example", "").strip()
        entry["pos"] = request.form.get("pos", "").strip()
        entry["tags"] = request.form.get("tags", "").strip()
        save_vocab(words)
        return redirect("/")
    return render_template("add_word.html", edit=True, **entry)

@app.route("/delete/<word>", methods=["POST"])
def delete_word(word):
    words = load_vocab()
    words = [w for w in words if w["word"] != word]
    save_vocab(words)
    return jsonify(success=True)

@app.route("/memorize/<word>", methods=["POST"])
def memorize(word):
    words = load_vocab()
    for w in words:
        if w["word"] == word:
            w["memorized"] = True
    save_vocab(words)
    return jsonify(success=True)

@app.route("/reset", methods=["POST"])
def reset_memorized():
    words = load_vocab()
    for w in words:
        w["memorized"] = False
    save_vocab(words)
    return redirect("/")

@app.route("/bulk_add", methods=["GET", "POST"])
def bulk_add():
    if request.method == "POST":
        bulk = request.form["bulkwords"]
        words = load_vocab()
        for line in bulk.strip().split("\n"):
            parts = [x.strip() for x in line.strip().split(",")]
            if len(parts) >= 2:
                w = {"word": parts[0], "meaning": parts[1], "example": parts[2] if len(parts) > 2 else "",
                     "pos": parts[3] if len(parts) > 3 else "", "tags": parts[4] if len(parts) > 4 else "", "memorized": False}
                if not any(ww["word"].lower() == w["word"].lower() for ww in words):
                    words.append(w)
        save_vocab(words)
        return redirect("/")
    return render_template("bulk_add.html")

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    words = load_vocab()
    if not words:
        return render_template("quiz.html", word=None)
    if request.method == "GET":
        problems = random.sample(words, min(20, len(words)))
        session["quiz_problems"] = problems
        session["quiz_idx"] = 0
        session["quiz_score"] = 0
        session["quiz_user_answers"] = []
        return redirect(url_for("quiz"))
    problems = session.get("quiz_problems", [])
    idx = session.get("quiz_idx", 0)
    score = session.get("quiz_score", 0)
    user_answers = session.get("quiz_user_answers", [])
    word = problems[idx]["word"]
    real_meanings = [m.strip() for m in problems[idx]["meaning"].split(",")]
    user_meaning = request.form["user_meaning"].strip()
    is_correct = any(
        user_meaning.lower().replace(" ", "") == rm.lower().replace(" ", "")
        for rm in real_meanings
    )
    if is_correct:
        score += 1
    wrong_note = load_wrong_note()
    if not is_correct:
        note = wrong_note.get(word, {"count": 0, "word": word, "meaning": problems[idx]["meaning"], "your_answer": "", "recent_wrong": ""})
        note["count"] += 1
        note["recent_wrong"] = user_meaning
        wrong_note[word] = note
        save_wrong_note(wrong_note)
    user_answers.append({
        "word": word,
        "your_answer": user_meaning,
        "meanings": problems[idx]["meaning"],
        "is_correct": is_correct
    })
    idx += 1
    session["quiz_idx"] = idx
    session["quiz_score"] = score
    session["quiz_user_answers"] = user_answers
    if idx >= len(problems):
        return redirect(url_for("quiz_result"))
    else:
        return render_template("quiz.html", word=problems[idx]["word"])

@app.route("/quiz_result")
def quiz_result():
    problems = session.get("quiz_problems", [])
    user_answers = session.get("quiz_user_answers", [])
    score = session.get("quiz_score", 0)
    return render_template(
        "quiz_result.html",
        total=len(problems),
        score=score,
        user_answers=user_answers
    )

@app.route("/wrong_note")
def wrong_note():
    note = load_wrong_note()
    items = sorted(note.values(), key=lambda x: -x["count"])
    return render_template("wrong_note.html", wrong_list=items)

@app.route("/wrong_note/quiz", methods=["GET", "POST"])
def wrong_note_quiz():
    note = load_wrong_note()
    wrong_words = [w for w in note]
    if not wrong_words:
        return render_template("quiz.html", word=None)
    if request.method == "GET":
        wrong_probs = random.sample(wrong_words, min(20, len(wrong_words)))
        words = load_vocab()
        problems = [next((w for w in words if w["word"] == ww), {"word": ww, "meaning": note[ww]["meaning"], "example": "", "pos": "", "tags": "", "memorized": False}) for ww in wrong_probs]
        session["quiz_problems"] = problems
        session["quiz_idx"] = 0
        session["quiz_score"] = 0
        session["quiz_user_answers"] = []
        session["wrong_note_mode"] = True
        return redirect(url_for("wrong_note_quiz"))
    return quiz()

@app.route("/wrong_note/delete/<word>", methods=["POST"])
def wrong_note_delete(word):
    note = load_wrong_note()
    if word in note:
        note.pop(word)
        save_wrong_note(note)
    return jsonify(success=True)

@app.route("/flashcard")
def flashcard():
    words = load_vocab()
    if not words:
        return render_template("flashcard.html", word=None)
    idx = int(request.args.get("idx", "0"))
    order = request.args.get("order", "random")
    if order == "random":
        if "flashcard_order" not in session:
            session["flashcard_order"] = random.sample(range(len(words)), len(words))
        order_list = session["flashcard_order"]
    else:
        order_list = list(range(len(words)))
    if idx >= len(words):
        idx = 0
    card_idx = order_list[idx]
    word = words[card_idx]
    total = len(words)
    return render_template("flashcard.html", word=word, idx=idx, total=total, order=order)

@app.route("/generate_example", methods=["POST"])
def generate_example():
    word = request.json.get("word")
    meaning = request.json.get("meaning")
    example_en = f"I want to {word} this problem."
    example_ko = f"나는 이 문제를 {meaning} 싶다."
    return jsonify({"example_en": example_en, "example_ko": example_ko})

# 발음(TTS)은 프론트 Web Speech API 활용 (JS)
if __name__ == "__main__":
    app.run(debug=True)
