
from flask import Flask, render_template, request, redirect, session, flash
import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change in production

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT")
    )
    return conn

# ---------------- Login ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM students WHERE email=%s AND password=%s", (email, password))
        student = cur.fetchone()
        cur.close()
        conn.close()

        if student:
            session["student_id"] = student[0]
            session["student_name"] = student[1]
            return redirect("/dashboard")
        else:
            flash("Invalid credentials")
    return render_template("login.html")

# ---------------- Dashboard ----------------
@app.route("/dashboard")
def dashboard():
    if "student_id" not in session:
        return redirect("/")
    
    student_id = session["student_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT debt, nhif_exempted FROM students WHERE id=%s", (student_id,))
    debt, nhif = cur.fetchone()
    cur.close()
    conn.close()

    return render_template("dashboard.html", name=session["student_name"], debt=debt, nhif=nhif)

# ---------------- Voting ----------------
@app.route("/vote", methods=["GET", "POST"])
def vote():
    if "student_id" not in session:
        return redirect("/")

    student_id = session["student_id"]
    conn = get_db_connection()
    cur = conn.cursor()

    # Get candidates
    cur.execute("SELECT id, name, position FROM election_candidates")
    candidates = cur.fetchall()

    # Check if student has already voted
    cur.execute("SELECT COUNT(*) FROM votes WHERE student_id=%s", (student_id,))
    voted = cur.fetchone()[0] > 0

    if request.method == "POST":
        candidate_id = request.form.get("candidate_id")
        if not voted:
            cur.execute("INSERT INTO votes (student_id, candidate_id) VALUES (%s, %s)", (student_id, candidate_id))
            conn.commit()
            flash("Vote submitted successfully!")
            voted = True
        else:
            flash("You have already voted!")

    cur.close()
    conn.close()
    return render_template("vote.html", candidates=candidates, voted=voted)

# ---------------- Academic Results ----------------
@app.route("/results")
def results():
    if "student_id" not in session:
        return redirect("/")

    student_id = session["student_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT course_name, grade, year FROM academic_results WHERE student_id=%s", (student_id,))
    results = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("results.html", results=results)

# ---------------- PEX Requests ----------------
@app.route("/pex", methods=["GET", "POST"])
def pex():
    if "student_id" not in session:
        return redirect("/")

    student_id = session["student_id"]
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        reason = request.form.get("reason")
        cur.execute("INSERT INTO pex_requests (student_id, reason) VALUES (%s, %s)", (student_id, reason))
        conn.commit()
        flash("PEX request submitted!")

    # Fetch student's PEX requests
    cur.execute("SELECT reason, status, requested_on FROM pex_requests WHERE student_id=%s", (student_id,))
    pex_requests = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("pex.html", pex_requests=pex_requests)

# ---------------- Change Password ----------------
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "student_id" not in session:
        return redirect("/")

    student_id = session["student_id"]

    if request.method == "POST":
        old_pass = request.form.get("old_password")
        new_pass = request.form.get("new_password")

        conn = get_db_connection()
        cur = conn.cursor()
        # Verify old password
        cur.execute("SELECT password FROM students WHERE id=%s", (student_id,))
        current_password = cur.fetchone()[0]

        if old_pass == current_password:
            cur.execute("UPDATE students SET password=%s WHERE id=%s", (new_pass, student_id))
            conn.commit()
            flash("Password changed successfully!")
        else:
            flash("Old password is incorrect!")
        cur.close()
        conn.close()

    return render_template("change_password.html")

# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True)
