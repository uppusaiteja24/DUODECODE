from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-deployment"
DB_PATH = Path(__file__).with_name("brainbridge.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                teach_topics TEXT DEFAULT '',
                learn_topics TEXT DEFAULT ''
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                message TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(requester_id) REFERENCES users(id),
                FOREIGN KEY(receiver_id) REFERENCES users(id)
            )
        """)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def clean_topics(value):
    # Keep a simple comma-separated list and remove empty entries.
    return ", ".join(dict.fromkeys(
        item.strip() for item in value.split(",") if item.strip()
    ))

def topic_list(value):
    return [x.strip().casefold() for x in (value or "").split(",") if x.strip()]

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "Student")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email, and a password with at least 6 characters.", "error")
            return render_template("register.html")
        if role not in ("Student", "Teacher / Mentor"):
            role = "Student"
        try:
            with get_db() as db:
                db.execute(
                    "INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)",
                    (name, email, generate_password_hash(password), role)
                )
            flash("Account created! Please log in and complete your learning profile.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    with get_db() as db:
        me = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        sent = db.execute("SELECT COUNT(*) AS n FROM requests WHERE requester_id=?", (uid,)).fetchone()["n"]
        received = db.execute("SELECT COUNT(*) AS n FROM requests WHERE receiver_id=? AND status='Pending'", (uid,)).fetchone()["n"]
        all_users = db.execute("SELECT * FROM users WHERE id<>?", (uid,)).fetchall()
    my_teach = set(topic_list(me["teach_topics"]))
    my_learn = set(topic_list(me["learn_topics"]))
    suggestions = []
    for person in all_users:
        their_teach = set(topic_list(person["teach_topics"]))
        their_learn = set(topic_list(person["learn_topics"]))
        shared = sorted((my_learn & their_teach) | (my_teach & their_learn))
        if shared:
            suggestions.append({"person": person, "topics": shared})
    suggestions.sort(key=lambda x: len(x["topics"]), reverse=True)
    return render_template("dashboard.html", me=me, suggestions=suggestions[:4],
                           sent=sent, received=received)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    uid = session["user_id"]
    with get_db() as db:
        me = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if request.method == "POST":
            teach = clean_topics(request.form.get("teach_topics", ""))
            learn = clean_topics(request.form.get("learn_topics", ""))
            db.execute("UPDATE users SET teach_topics=?, learn_topics=? WHERE id=?",
                       (teach, learn, uid))
            flash("Your learning profile has been updated.", "success")
            return redirect(url_for("dashboard"))
    return render_template("profile.html", me=me)

@app.route("/matches")
@login_required
def matches():
    uid = session["user_id"]
    with get_db() as db:
        me = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        people = db.execute("SELECT * FROM users WHERE id<>?", (uid,)).fetchall()
    my_teach = set(topic_list(me["teach_topics"]))
    my_learn = set(topic_list(me["learn_topics"]))
    results = []
    for person in people:
        their_teach = set(topic_list(person["teach_topics"]))
        their_learn = set(topic_list(person["learn_topics"]))
        topics_to_learn = sorted(my_learn & their_teach)
        topics_to_teach = sorted(my_teach & their_learn)
        if topics_to_learn or topics_to_teach:
            results.append({
                "person": person,
                "learn": topics_to_learn,
                "teach": topics_to_teach
            })
    return render_template("matches.html", results=results)

@app.route("/request/<int:receiver_id>", methods=["POST"])
@login_required
def send_request(receiver_id):
    uid = session["user_id"]
    topic = request.form.get("topic", "").strip()
    message = request.form.get("message", "").strip()
    if not topic:
        flash("Please choose a topic for the learning request.", "error")
        return redirect(url_for("matches"))
    if receiver_id == uid:
        flash("You cannot send a request to yourself.", "error")
        return redirect(url_for("matches"))
    with get_db() as db:
        receiver = db.execute("SELECT id FROM users WHERE id=?", (receiver_id,)).fetchone()
        if not receiver:
            flash("That user could not be found.", "error")
        else:
            db.execute("""INSERT INTO requests
                (requester_id,receiver_id,topic,message) VALUES (?,?,?,?)""",
                (uid, receiver_id, topic, message))
            flash("Learning request sent.", "success")
    return redirect(url_for("requests_page"))

@app.route("/requests")
@login_required
def requests_page():
    uid = session["user_id"]
    with get_db() as db:
        incoming = db.execute("""
            SELECT r.*, u.name AS person_name, u.role AS person_role
            FROM requests r JOIN users u ON u.id=r.requester_id
            WHERE r.receiver_id=? ORDER BY r.created_at DESC
        """, (uid,)).fetchall()
        outgoing = db.execute("""
            SELECT r.*, u.name AS person_name, u.role AS person_role
            FROM requests r JOIN users u ON u.id=r.receiver_id
            WHERE r.requester_id=? ORDER BY r.created_at DESC
        """, (uid,)).fetchall()
    return render_template("requests.html", incoming=incoming, outgoing=outgoing)

@app.route("/request/<int:request_id>/<action>", methods=["POST"])
@login_required
def update_request(request_id, action):
    if action not in ("accept", "decline"):
        return redirect(url_for("requests_page"))
    status = "Accepted" if action == "accept" else "Declined"
    with get_db() as db:
        db.execute("UPDATE requests SET status=? WHERE id=? AND receiver_id=? AND status='Pending'",
                   (status, request_id, session["user_id"]))
    flash(f"Request {status.lower()}.", "success")
    return redirect(url_for("requests_page"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
