from flask import Flask, render_template, request, redirect, jsonify
import json
import os
import random

app = Flask(__name__)
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

@app.route("/bulk_add", methods=["GET", "POST"])
def bulk_add():
    if request.method == "POST":
        bulk = request.form["bulkwords"]
        words = load_vocab()
        for line in bulk.strip().split("\n"):
            parts = line.strip().split(",")
            if len(parts) >= 2:
                word, meaning = parts[0].strip(), parts[1].strip()
                words.append({"word": word, "meaning": meaning, "memorized": False})
        save_vocab(words)
        return redirect("/")
    return render_template("bulk_add.html")

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

@app.route("/delete/<word>", methods=["POST"])
def delete_word(word):
    words = load_vocab()
    words = [w for w in words if w["word"] != word]
    save_vocab(words)
    return jsonify(success=True)

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    words = load_vocab()
    if not words:
        return render_template("quiz.html", word=None)
    if request.method == "POST":
        word = request.form["word"]
        user_meaning = request.form["user_meaning"].strip()
        real_meaning = next((w["meaning"] for w in words if w["word"] == word), "")
        correct = user_meaning == real_meaning
        return render_template("quiz.html", word=word, correct=correct, real_meaning=real_meaning)
    word = random.choice(words)["word"]
    return render_template("quiz.html", word=word)
    
if __name__ == "__main__":
    app.run(debug=True)
