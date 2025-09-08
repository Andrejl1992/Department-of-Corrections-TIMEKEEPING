from flask import Flask, request, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)

# -----------------------------
# Setup: Create the database
# -----------------------------
def init_db():
    conn = sqlite3.connect("phase2.db")
    c = conn.cursor()

    # Staff table: stores officer info + seniority
    c.execute('''CREATE TABLE IF NOT EXISTS staff (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    badge_number TEXT,
                    shift INTEGER,
                    start_date TEXT,   -- used for seniority
                    class_rank INTEGER, -- rank within academy class
                    pto_balance INTEGER
                )''')

    # Requests table: stores time-off requests
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER,
                    date TEXT,
                    shift INTEGER,
                    status TEXT,       -- approved / denied / waitlist
                    waitlist_pos INTEGER
                )''')

    conn.commit()
    conn.close()

# -----------------------------
# Helper: Seniority Score
# -----------------------------
def seniority_score(start_date, class_rank):
    """ Lower score = higher priority.
        First by hire date, then by class rank.
    """
    return (datetime.strptime(start_date, "%Y-%m-%d"), class_rank)

# -----------------------------
# Helper: Count approved slots
# -----------------------------
def approved_count(shift, date):
    conn = sqlite3.connect("phase2.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM requests WHERE date=? AND shift=? AND status='approved'", (date, shift))
    count = c.fetchone()[0]
    conn.close()
    return count

# -----------------------------
# Webpage: Submit PTO request
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def request_timeoff():
    message = ""
    if request.method == "POST":
        staff_id = int(request.form["staff_id"])
        date = request.form["date"]

        conn = sqlite3.connect("phase2.db")
        c = conn.cursor()

        # Find staff info
        c.execute("SELECT shift, pto_balance, start_date, class_rank FROM staff WHERE id=?", (staff_id,))
        staff = c.fetchone()

        if not staff:
            message = "Staff not found."
        else:
            shift, balance, start_date, class_rank = staff
            limits = {1: 25, 2: 15, 3: 7}

            if balance <= 0:
                # Not enough PTO
                status = "denied"
                message = "Denied: not enough PTO."
            elif approved_count(shift, date) < limits[shift]:
                # Slot available → approve
                status = "approved"
                message = "Approved!"
                c.execute("UPDATE staff SET pto_balance = pto_balance - 1 WHERE id=?", (staff_id,))
            else:
                # Slot full → put on waitlist
                status = "waitlist"

                # Get all current waitlist entries for that shift/date
                c.execute("""SELECT s.start_date, s.class_rank, r.staff_id
                             FROM requests r
                             JOIN staff s ON r.staff_id = s.id
                             WHERE r.date=? AND r.shift=? AND r.status='waitlist'""",
                          (date, shift))
                waitlist = c.fetchall()

                # Add current staff to list and sort by seniority
                waitlist.append((start_date, class_rank, staff_id))
                waitlist.sort(key=lambda x: seniority_score(x[0], x[1]))

                # Position = index in sorted waitlist
                pos = [w[2] for w in waitlist].index(staff_id) + 1
                message = f"All slots full. Added to waitlist (position {pos})."

                # Deduct 1 PTO day and save with waitlist position
                c.execute("UPDATE staff SET pto_balance = pto_balance - 1 WHERE id=?", (staff_id,))
                c.execute("INSERT INTO requests (staff_id, date, shift, status, waitlist_pos) VALUES (?, ?, ?, ?, ?)",
                          (staff_id, date, shift, status, pos))
                conn.commit()
                conn.close()
                return render_template_string(PAGE, message=message)

            # Save request (approved/denied)
            c.execute("INSERT INTO requests (staff_id, date, shift, status, waitlist_pos) VALUES (?, ?, ?, ?, ?)",
                      (staff_id, date, shift, status, None))
            conn.commit()

        conn.close()

    return render_template_string(PAGE, message=message)

# -----------------------------
# HTML form for testing
# -----------------------------
PAGE = '''
    <h2>PTO Request System (Phase 2)</h2>
    <form method="POST">
        Staff ID: <input type="text" name="staff_id"><br>
        Date (YYYY-MM-DD): <input type="text" name="date"><br>
        <input type="submit" value="Submit Request">
    </form>
    <p>{{message}}</p>
'''

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
