from flask import Flask, request, render_template_string
import sqlite3
from datetime import datetime
import smtplib

app = Flask(__name__)

# -----------------------------
# Setup: Create database tables
# -----------------------------
def init_db():
    conn = sqlite3.connect("phase4.db")
    c = conn.cursor()

    # Staff table with contact info
    c.execute('''CREATE TABLE IF NOT EXISTS staff (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    badge_number TEXT,
                    shift INTEGER,
                    start_date TEXT,
                    class_rank INTEGER,
                    pto_balance INTEGER,
                    email TEXT
                )''')

    # Requests table
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER,
                    date TEXT,
                    shift INTEGER,
                    status TEXT,
                    waitlist_pos INTEGER
                )''')

    # Schedule table (daily roster)
    c.execute('''CREATE TABLE IF NOT EXISTS schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER,
                    date TEXT,
                    shift INTEGER,
                    status TEXT
                )''')

    conn.commit()
    conn.close()

# -----------------------------
# Helper: Send notification (email)
# -----------------------------
def send_notification(email, subject, message):
    """Send email notification to staff."""
    try:
        server = smtplib.SMTP("localhost")
        body = f"Subject: {subject}\n\n{message}"
        server.sendmail("admin@nj.doc.gov", email, body)  # admin email updated
        server.quit()
        print(f"Notification sent to {email}: {subject}")
    except Exception as e:
        print(f"Error sending email: {e}")

# -----------------------------
# Helper: Lockout staff from schedule
# -----------------------------
def lockout_staff(staff_id, date, shift):
    """Mark staff as unavailable in schedule table."""
    conn = sqlite3.connect("phase4.db")
    c = conn.cursor()
    c.execute("INSERT INTO schedule (staff_id, date, shift, status) VALUES (?, ?, ?, ?)",
              (staff_id, date, shift, "unavailable"))
    conn.commit()
    conn.close()

# -----------------------------
# Webpage: Approve a PTO request
# -----------------------------
@app.route("/approve", methods=["GET", "POST"])
def approve_request():
    message = ""
    if request.method == "POST":
        req_id = int(request.form["request_id"])

        conn = sqlite3.connect("phase4.db")
        c = conn.cursor()

        # Find request + staff info
        c.execute("SELECT staff_id, date, shift FROM requests WHERE id=?", (req_id,))
        req = c.fetchone()

        if not req:
            message = "Request not found."
        else:
            staff_id, date, shift = req
            c.execute("UPDATE requests SET status='approved' WHERE id=?", (req_id,))

            # Lock staff out of schedule
            lockout_staff(staff_id, date, shift)

            # Get staff email and name
            c.execute("SELECT email, name FROM staff WHERE id=?", (staff_id,))
            staff = c.fetchone()
            if staff:
                email, name = staff
                send_notification(
                    email,
                    "PTO Approved",
                    f"Hello {name}, your request for {date} (Shift {shift}) has been approved."
                )

            conn.commit()
            message = "Request approved. Staff notified and locked out of schedule."

        conn.close()

    return render_template_string(APPROVE_PAGE, message=message)

# -----------------------------
# HTML form for testing
# -----------------------------
APPROVE_PAGE = '''
    <h2>Approve PTO (Phase 4)</h2>
    <form method="POST">
        Request ID: <input type="text" name="request_id"><br>
        <input type="submit" value="Approve Request">
    </form>
    <p>{{message}}</p>
'''

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
