from flask import Flask, render_template, request, redirect, jsonify
import json
import os

app = Flask(__name__)
DATA_PATH = "vocab.json"

# 단어장 데이터 불러오기
def load_vocab():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 단어장 저장
def save_vocab(words):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

@app.route("/")
def index():
    words = load_vocab()
    return render_template("index.html", words=words)

@app.route("/add", methods=["GET", "POST"])
def add_word():
    if request.method == "POST":
        word = request.form["word"]
        meaning = request.form["meaning"]
        words = load_vocab()
        words.append({"word": word, "meaning": meaning, "memorized": False})
        save_vocab(words)
        return redirect("/")
    return render_template("add_word.html")

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

if __name__ == "__main__":
    app.run(debug=True)
