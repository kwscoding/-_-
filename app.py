from flask import Flask, render_template, request, redirect, session, url_for
import json
import os
import random

app = Flask(__name__)
app.secret_key = "random-secret-key"
DATA_PATH = "vocab.json"

def load_vocab():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_vocab(words):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

@app.route("/")
def index():
    words = load_vocab()
    return render_template("index.html", words=words)

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    words = load_vocab()
    if not words:
        return render_template("quiz.html", word=None)

    # 새 퀴즈 시작: session 초기화 & 1번 문제 바로 보여줌
    if "quiz_problems" not in session or "quiz_idx" not in session or request.method == "GET":
        problems = random.sample(words, min(20, len(words)))
        session["quiz_problems"] = problems
        session["quiz_idx"] = 0
        session["quiz_score"] = 0
        session["quiz_user_answers"] = []
        return render_template("quiz.html", word=problems[0]["word"], feedback=None, answer=None, idx=0, total=len(problems))

    # POST: 채점 + 피드백 + 다음/결과 버튼 제공
    problems = session.get("quiz_problems", [])
    idx = session.get("quiz_idx", 0)
    score = session.get("quiz_score", 0)
    user_answers = session.get("quiz_user_answers", [])

    # 이미 끝났으면 결과로
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

    # 마지막 문제면 "최종 결과로"로 바뀜
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
    return render_template("quiz.html", word=word, feedback=None, answer=None, idx=idx, total=len(problems))

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

if __name__ == "__main__":
    app.run(debug=True)
