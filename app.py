from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"


# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        description TEXT,
        status TEXT DEFAULT 'Pending',
        date TEXT,
        reminder INTEGER DEFAULT 0,
        category TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        comment TEXT,
        date TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        date TEXT,
        type TEXT,
        complaint_id INTEGER)''')

    conn.commit()
    conn.close()

init_db()


# ================= HOME =================
@app.route('/')
def home():
    return render_template('home.html')


# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'student')

        conn = sqlite3.connect('database.db', timeout=10)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                      (username, email, password, role))
            conn.commit()
        except:
            conn.close()
            return "User already exists!"
        conn.close()
        return redirect('/login')

    return render_template('register.html')


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db', timeout=10)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['role'] = user[4]
            session['name'] = user[1]

            if user[4] == "admin":
                return redirect('/admin_dashboard')
            else:
                return redirect('/student_dashboard')
        else:
            return "Invalid Login"

    return render_template('login.html')


# ================= STUDENT DASHBOARD =================
@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM complaints WHERE user_id=?", (session['user_id'],))
    my_count = c.fetchone()[0]

    c.execute("SELECT * FROM feedback ORDER BY id DESC LIMIT 2")
    feedbacks = c.fetchall()

    c.execute("""SELECT * FROM notifications
                 WHERE user_id=? AND is_read=0 AND type='status_update'
                 ORDER BY id DESC""", (session['user_id'],))
    notifications = c.fetchall()
    notif_count = len(notifications)

    conn.close()

    return render_template('student_dashboard.html',
                           my_count=my_count,
                           feedbacks=feedbacks,
                           feedback_success=False,
                           notifications=notifications,
                           notif_count=notif_count)


# ================= STUDENT NOTIFICATIONS PAGE =================
@app.route('/student_notifications')
def student_notifications():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()

    c.execute("""SELECT * FROM notifications
                 WHERE user_id=? AND type='status_update'
                 ORDER BY id DESC""", (session['user_id'],))
    all_notifications = c.fetchall()

    c.execute("""SELECT COUNT(*) FROM notifications
                 WHERE user_id=? AND type='status_update' AND is_read=0""",
              (session['user_id'],))
    unread_count = c.fetchone()[0]

    conn.close()

    return render_template('student_notifications.html',
                           all_notifications=all_notifications,
                           unread_count=unread_count)


# ================= MARK STUDENT NOTIFICATIONS READ =================
@app.route('/mark_read')
def mark_read():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("""UPDATE notifications SET is_read=1
                 WHERE user_id=? AND type='status_update'""",
              (session['user_id'],))
    conn.commit()
    conn.close()

    # ✅ Redirect to dashboard so notification box disappears
    return redirect('/student_dashboard')


# ================= SUBMIT FEEDBACK =================
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if 'user_id' not in session:
        return redirect('/login')

    name = request.form['name']
    email = request.form['email']
    comment = request.form['comment']
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("INSERT INTO feedback(name, email, comment, date) VALUES(?,?,?,?)",
              (name, email, comment, date))
    conn.commit()

    c.execute("SELECT COUNT(*) FROM complaints WHERE user_id=?", (session['user_id'],))
    my_count = c.fetchone()[0]

    c.execute("SELECT * FROM feedback ORDER BY id DESC LIMIT 2")
    feedbacks = c.fetchall()

    c.execute("""SELECT * FROM notifications
                 WHERE user_id=? AND is_read=0 AND type='status_update'
                 ORDER BY id DESC""", (session['user_id'],))
    notifications = c.fetchall()
    notif_count = len(notifications)

    conn.close()

    return render_template('student_dashboard.html',
                           my_count=my_count,
                           feedbacks=feedbacks,
                           feedback_success=True,
                           notifications=notifications,
                           notif_count=notif_count)


# ================= ALL FEEDBACKS - STUDENT VIEW =================
@app.route('/all_student_feedbacks')
def all_student_feedbacks():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("SELECT * FROM feedback ORDER BY id DESC")
    feedbacks = c.fetchall()
    conn.close()

    return render_template('all_student_feedbacks.html', feedbacks=feedbacks)


# ================= MY COMPLAINTS =================
@app.route('/my_complaints')
def my_complaints():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("""SELECT complaints.*, users.email
                 FROM complaints
                 JOIN users ON complaints.user_id = users.id
                 WHERE complaints.user_id=?
                 ORDER BY complaints.id DESC""",
              (session['user_id'],))
    complaints = c.fetchall()
    conn.close()

    return render_template('my_complaints.html', complaints=complaints)


# ================= ADD COMPLAINT =================
@app.route('/add_complaint', methods=['GET', 'POST'])
def add_complaint():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = sqlite3.connect('database.db', timeout=10)
        c = conn.cursor()
        c.execute("""INSERT INTO complaints(user_id, title, description, date, category)
                     VALUES(?,?,?,?,?)""",
                  (session['user_id'], title, description, date, category))
        conn.commit()
        conn.close()

        return redirect('/student_dashboard')

    return render_template('add_complaint.html')


# ================= ADMIN DASHBOARD =================
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()

    c.execute("""SELECT complaints.*, users.name, users.email
                 FROM complaints
                 JOIN users ON complaints.user_id = users.id""")
    complaints = c.fetchall()

    c.execute("SELECT COUNT(*) FROM complaints")
    total_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    completed_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending_count = c.fetchone()[0]

    c.execute("SELECT * FROM feedback ORDER BY id DESC LIMIT 2")
    feedbacks = c.fetchall()

    c.execute("""SELECT notifications.*, users.name, complaints.title
                 FROM notifications
                 JOIN users ON notifications.user_id = users.id
                 JOIN complaints ON notifications.complaint_id = complaints.id
                 WHERE notifications.type='reminder' AND notifications.is_read=0
                 ORDER BY notifications.id DESC""")
    admin_notifications = c.fetchall()
    admin_notif_count = len(admin_notifications)

    conn.close()

    return render_template('admin_dashboard.html',
                           complaints=complaints,
                           total_count=total_count,
                           completed_count=completed_count,
                           pending_count=pending_count,
                           feedbacks=feedbacks,
                           admin_notifications=admin_notifications,
                           admin_notif_count=admin_notif_count)


# ================= ADMIN NOTIFICATIONS PAGE =================
@app.route('/admin_notifications')
def admin_notifications():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()

    c.execute("""SELECT * FROM notifications
                 WHERE type='reminder'
                 ORDER BY id DESC""")
    all_notifications = c.fetchall()

    c.execute("""SELECT COUNT(*) FROM notifications
                 WHERE type='reminder' AND is_read=0""")
    unread_count = c.fetchone()[0]

    conn.close()

    return render_template('admin_notifications.html',
                           all_notifications=all_notifications,
                           unread_count=unread_count)


# ================= MARK ADMIN NOTIFICATIONS READ =================
@app.route('/mark_admin_read')
def mark_admin_read():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("UPDATE notifications SET is_read=1 WHERE type='reminder'")
    conn.commit()
    conn.close()

    # ✅ Redirect to dashboard so notification box disappears
    return redirect('/admin_dashboard')


# ================= ALL FEEDBACKS - ADMIN VIEW =================
@app.route('/all_feedbacks')
def all_feedbacks():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("SELECT * FROM feedback ORDER BY id DESC")
    feedbacks = c.fetchall()
    conn.close()

    return render_template('all_feedbacks.html', feedbacks=feedbacks)


# ================= TOTAL COMPLAINTS =================
@app.route('/total_complaints')
def total_complaints():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("""SELECT complaints.*, users.name, users.email
                 FROM complaints
                 JOIN users ON complaints.user_id = users.id
                 ORDER BY complaints.id DESC""")
    complaints = c.fetchall()
    conn.close()

    return render_template('total_complaints.html', complaints=complaints)


# ================= COMPLETED COMPLAINTS =================
@app.route('/completed_complaints')
def completed_complaints():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("""SELECT complaints.*, users.name, users.email
                 FROM complaints
                 JOIN users ON complaints.user_id = users.id
                 WHERE complaints.status='Resolved'""")
    complaints = c.fetchall()
    conn.close()

    return render_template('completed_complaints.html', complaints=complaints)


# ================= PENDING COMPLAINTS =================
@app.route('/pending_complaints')
def pending_complaints():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("""SELECT complaints.*, users.name, users.email
                 FROM complaints
                 JOIN users ON complaints.user_id = users.id
                 WHERE complaints.status='Pending'""")
    complaints = c.fetchall()
    conn.close()

    return render_template('pending_complaints.html', complaints=complaints)


# ================= UPDATE STATUS =================
@app.route('/update/<int:id>/<status>')
def update(id, status):
    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()

    c.execute("SELECT * FROM complaints WHERE id=?", (id,))
    complaint = c.fetchone()

    if complaint:
        user_id = complaint[1]
        title = complaint[2]
        date = datetime.now().strftime("%Y-%m-%d %H:%M")

        c.execute("UPDATE complaints SET status=? WHERE id=?", (status, id))

        message = f"Your complaint '{title}' has been marked as {status} by Admin."
        c.execute("""INSERT INTO notifications
                     (user_id, message, is_read, date, type, complaint_id)
                     VALUES(?,?,0,?,'status_update',?)""",
                  (user_id, message, date, id))

    conn.commit()
    conn.close()
    return redirect('/admin_dashboard')


# ================= REMINDER =================
@app.route('/reminder/<int:id>')
def reminder(id):
    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()

    c.execute("UPDATE complaints SET reminder = reminder + 1 WHERE id=?", (id,))

    c.execute("SELECT * FROM complaints WHERE id=?", (id,))
    complaint = c.fetchone()

    if complaint:
        title = complaint[2]
        user_id = complaint[1]
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"Student {session.get('name', 'Student')} is reminding about complaint '{title}'."

        c.execute("""INSERT INTO notifications
                     (user_id, message, is_read, date, type, complaint_id)
                     VALUES(?,?,0,?,'reminder',?)""",
                  (user_id, message, date, id))

    conn.commit()
    conn.close()
    return redirect('/my_complaints')


# ================= DELETE COMPLAINT =================
@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db', timeout=10)
    c = conn.cursor()
    c.execute("DELETE FROM complaints WHERE id=? AND user_id=?",
              (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/my_complaints')


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)