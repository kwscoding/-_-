from flask import Flask, render_template, request, redirect, url_for, session
import json, os, random

app = Flask(__name__)
app.secret_key = "random-secret-key"
DATA_PATH = "vocab.json"
WRONG_PATH = "wrong_note.json"

# ---------------------
def load_vocab():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_vocab(words):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

def load_wrong():
    if os.path.exists(WRONG_PATH):
        with open(WRONG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_wrong(wrong):
    with open(WRONG_PATH, "w", encoding="utf-8") as f:
        json.dump(wrong, f, ensure_ascii=False, indent=2)

# ---------------------
@app.route("/")
def index():
    q = request.args.get("q", "")
    filter_mode = request.args.get("filter", "all")
    sort_mode = request.args.get("sort", "recent")
    words = load_vocab()

    # 검색/필터/정렬
    if q:
        words = [w for w in words if q.lower() in w["word"].lower() or q in w["meaning"] or q in w.get("example","") or q in w.get("tags","")]
    if filter_mode == "memorized":
        words = [w for w in words if w.get("memorized", False)]
    elif filter_mode == "not_memorized":
        words = [w for w in words if not w.get("memorized", False)]
    if sort_mode == "alpha":
        words = sorted(words, key=lambda x: x["word"])
    elif sort_mode == "memorized":
        words = sorted(words, key=lambda x: x.get("memorized", False))
    else:
        words = list(reversed(words))
    total = len(load_vocab())
    memorized = sum(1 for w in load_vocab() if w.get("memorized", False))
    return render_template("index.html", words=words, q=q, filter_mode=filter_mode, sort_mode=sort_mode, total=total, memorized=memorized)

@app.route("/add", methods=["GET", "POST"])
def add_word():
    if request.method == "POST":
        word = request.form["word"].strip()
        meaning = request.form["meaning"].strip()
        if not word or not meaning:
            return render_template("add_word.html", error="단어와 뜻을 입력하세요.")
        example = request.form.get("example", "").strip()
        pos = request.form.get("pos", "").strip()
        tags = request.form.get("tags", "").strip()
        words = load_vocab()
        if any(w["word"] == word for w in words):
            return render_template("add_word.html", error="이미 존재하는 단어입니다.", word=word, meaning=meaning, example=example, pos=pos, tags=tags)
        words.append({"word": word, "meaning": meaning, "example": example, "pos": pos, "tags": tags, "memorized": False})
        save_vocab(words)
        return redirect(url_for("index"))
    return render_template("add_word.html", error=None)

@app.route("/edit/<word>", methods=["GET", "POST"])
def edit_word(word):
    words = load_vocab()
    w = next((w for w in words if w["word"] == word), None)
    if not w:
        return "단어를 찾을 수 없습니다.", 404
    if request.method == "POST":
        w["meaning"] = request.form["meaning"].strip()
        w["example"] = request.form.get("example", "").strip()
        w["pos"] = request.form.get("pos", "").strip()
        w["tags"] = request.form.get("tags", "").strip()
        save_vocab(words)
        return redirect(url_for("index"))
    return render_template("add_word.html", edit=True, word=w["word"], meaning=w["meaning"], example=w.get("example",""), pos=w.get("pos",""), tags=w.get("tags",""), error=None)

@app.route("/delete/<word>", methods=["POST"])
def delete_word(word):
    words = load_vocab()
    words = [w for w in words if w["word"] != word]
    save_vocab(words)
    return ("",204)

@app.route("/memorize/<word>", methods=["POST"])
def memorize(word):
    words = load_vocab()
    for w in words:
        if w["word"] == word:
            w["memorized"] = True
    save_vocab(words)
    return ("",204)

@app.route("/reset", methods=["POST"])
def reset_memorized():
    words = load_vocab()
    for w in words:
        w["memorized"] = False
    save_vocab(words)
    return redirect(url_for("index"))

@app.route("/bulk_add", methods=["GET", "POST"])
def bulk_add():
    if request.method == "POST":
        bulk = request.form["bulkwords"]
        words = load_vocab()
        for line in bulk.strip().split("\n"):
            cols = [c.strip() for c in line.split(",")]
            if len(cols) < 2:
                continue
            word, meaning = cols[0], cols[1]
            example = cols[2] if len(cols) > 2 else ""
            pos = cols[3] if len(cols) > 3 else ""
            tags = cols[4] if len(cols) > 4 else ""
            if any(w["word"] == word for w in words):
                continue
            words.append({"word": word, "meaning": meaning, "example": example, "pos": pos, "tags": tags, "memorized": False})
        save_vocab(words)
        return redirect(url_for("index"))
    return render_template("bulk_add.html")

# -------------------- 퀴즈 기능 (즉시 채점 + 다음문제/결과)
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    words = load_vocab()
    if not words:
        return render_template("quiz.html", word=None)

    # 새 퀴즈 시작 or 퀴즈 재시작(GET)
    if "quiz_problems" not in session or "quiz_idx" not in session or request.method == "GET":
        problems = random.sample(words, min(20, len(words)))
        session["quiz_problems"] = problems
        session["quiz_idx"] = 0
        session["quiz_score"] = 0
        session["quiz_user_answers"] = []
        return render_template("quiz.html", word=problems[0]["word"], feedback=None, answer=None, idx=0, total=len(problems), next_action=None, next_url=None)

    # POST: 정답 채점 & 피드백
    problems = session.get("quiz_problems", [])
    idx = session.get("quiz_idx", 0)
    score = session.get("quiz_score", 0)
    user_answers = session.get("quiz_user_answers", [])

    if idx >= len(problems):
        return redirect(url_for("quiz_result"))

    word = problems[idx]["word"]
    real_meanings = [m.strip() for m in problems[idx]["meaning"].split(",")]
    user_meaning = request.form["user_meaning"].strip()
    is_correct = any(
        user_meaning.lower().replace(" ", "") == rm.lower().replace(" ", "")
        for rm in real_meanings
    )
    feedback = "정답입니다! 🎉" if is_correct else "오답입니다! 😥"
    answer = problems[idx]["meaning"]

    if is_correct:
        score += 1

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

    # 오답노트 기록
    wrong = load_wrong()
    if not is_correct:
        # 오답노트 중복 체크, 횟수 기록
        found = next((w for w in wrong if w["word"] == word), None)
        if found:
            found["count"] += 1
            found["recent_wrong"] = user_meaning
        else:
            wrong.append({"word": word, "meaning": problems[idx-1]["meaning"], "count": 1, "recent_wrong": user_meaning})
        save_wrong(wrong)

    # 다음문제 or 최종결과
    if idx >= len(problems):
        next_action = "result"
        next_url = url_for("quiz_result")
    else:
        next_action = "next"
        next_url = url_for("quiz_next")

    return render_template("quiz.html",
        word=word,
        feedback=feedback,
        answer=answer,
        idx=idx-1,
        total=len(problems),
        next_action=next_action,
        next_url=next_url
    )

@app.route("/quiz_next", methods=["GET"])
def quiz_next():
    problems = session.get("quiz_problems", [])
    idx = session.get("quiz_idx", 0)
    if idx >= len(problems):
        return redirect(url_for("quiz_result"))
    word = problems[idx]["word"]
    return render_template("quiz.html", word=word, feedback=None, answer=None, idx=idx, total=len(problems), next_action=None, next_url=None)

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

# -------------------- 플래시카드/오답노트
@app.route("/flashcard")
def flashcard():
    words = load_vocab()
    order = request.args.get("order","rand")
    idx = int(request.args.get("idx","0"))
    if not words:
        return render_template("flashcard.html", word=None, idx=0, total=0, order=order)
    seq = words if order=="seq" else random.sample(words, len(words))
    if idx >= len(seq): idx = 0
    return render_template("flashcard.html", word=seq[idx], idx=idx, total=len(seq), order=order)

@app.route("/wrong_note")
def wrong_note():
    wrong = load_wrong()
    return render_template("wrong_note.html", wrong_list=wrong)

@app.route("/wrong_note/delete/<word>", methods=["POST"])
def wrong_note_delete(word):
    wrong = load_wrong()
    wrong = [w for w in wrong if w["word"] != word]
    save_wrong(wrong)
    return ("",204)

@app.route("/wrong_note/quiz")
def wrong_note_quiz():
    wrong = load_wrong()
    # 오답만 문제로!
    if not wrong:
        return redirect(url_for("wrong_note"))
    session["quiz_problems"] = random.sample(wrong, len(wrong))
    session["quiz_idx"] = 0
    session["quiz_score"] = 0
    session["quiz_user_answers"] = []
    return redirect(url_for("quiz"))

if __name__ == "__main__":
    app.run(debug=True)
