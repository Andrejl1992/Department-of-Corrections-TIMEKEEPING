from flask import Flask, request, render_template_string
import sqlite3

app = Flask(__name__)

# -----------------------------
# Setup: Create the database
# -----------------------------
def init_db():
    conn = sqlite3.connect("phase1.db")
    c = conn.cursor()

    # Staff table: holds staff info and PTO balance
    c.execute('''CREATE TABLE IF NOT EXISTS staff (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    badge_number TEXT,
                    shift INTEGER,
                    pto_balance INTEGER
                )''')

    # Requests table: stores PTO requests
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER,
                    date TEXT,
                    shift INTEGER,
                    status TEXT
                )''')

    conn.commit()
    conn.close()

# -----------------------------
# Helper: Check if slots are available
# -----------------------------
def slots_available(shift, date):
    # Slot limits per shift
    limits = {1: 25, 2: 15, 3: 7}

    conn = sqlite3.connect("phase1.db")
    c = conn.cursor()

    # Count approved requests for that shift/date
    c.execute("SELECT COUNT(*) FROM requests WHERE date=? AND shift=? AND status='approved'", (date, shift))
    count = c.fetchone()[0]

    conn.close()
    return count < limits[shift]

# -----------------------------
# Webpage: Submit PTO request
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def request_timeoff():
    message = ""
    if request.method == "POST":
        staff_id = int(request.form["staff_id"])
        date = request.form["date"]

        conn = sqlite3.connect("phase1.db")
        c = conn.cursor()

        # Find staff info
        c.execute("SELECT shift, pto_balance FROM staff WHERE id=?", (staff_id,))
        row = c.fetchone()

        if not row:
            message = "Staff not found."
        else:
            shift, balance = row

            if balance <= 0:
                status = "denied"
                message = "Denied: not enough PTO."
            elif not slots_available(shift, date):
                status = "denied"
                message = "Denied: no open slots."
            else:
                status = "approved"
                message = "Approved!"

                # Deduct 1 PTO day
                c.execute("UPDATE staff SET pto_balance = pto_balance - 1 WHERE id=?", (staff_id,))

            # Save request
            c.execute("INSERT INTO requests (staff_id, date, shift, status) VALUES (?, ?, ?, ?)",
                      (staff_id, date, shift, status))
            conn.commit()

        conn.close()

    # Simple HTML form for testing
    return render_template_string('''
        <h2>PTO Request System (Phase 1)</h2>
        <form method="POST">
            Staff ID: <input type="text" name="staff_id"><br>
            Date (YYYY-MM-DD): <input type="text" name="date"><br>
            <input type="submit" value="Submit Request">
        </form>
        <p>{{message}}</p>
    ''', message=message)


if __name__ == "__main__":
    init_db()   # Make sure database exists
    app.run(debug=True)
