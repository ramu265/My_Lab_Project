from flask import Flask, render_template, request, redirect, session, send_file, jsonify
import sqlite3
import subprocess
import datetime
import os
import sys
import uuid
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "secret"

DB = "attendance.db"

# ---------------- DATABASE INITIALIZATION ---------------- #
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS classes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS students(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                password TEXT,
                class_id INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS tasks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                sample_input TEXT,
                sample_output TEXT,
                class_id INTEGER,
                created_time TEXT,
                expiry_time TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                date TEXT)""")
    
    # NEW TABLE: To store student submissions and time spent
    c.execute("""CREATE TABLE IF NOT EXISTS submissions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                task_id INTEGER,
                submitted_code TEXT,
                time_spent_seconds INTEGER,
                submission_date TEXT)""")
    
    conn.commit()
    conn.close()

init_db()

# ---------------- AUTHENTICATION ---------------- #
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["type"] == "admin":
            if request.form["username"]=="ADC" and request.form["password"]=="VZM":
                session.clear()
                session["admin"]=True
                return redirect("/admin")
        else:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE name=? AND password=?",
                      (request.form["username"], request.form["password"]))
            user = c.fetchone()
            conn.close()
            if user:
                session.clear()
                session["student_id"]=user[0]
                session["class_id"]=user[3]
                return redirect("/student")
    return render_template("login.html")

# ---------------- ADMIN ROUTES ---------------- #
@app.route("/admin")
def admin():
    if "admin" not in session: return redirect("/")
    return render_template("admin_dashboard.html")

# ---------------- VIEW INDIVIDUAL STUDENT RESULTS ---------------- #
@app.route("/view_results/<int:student_id>")
def view_results(student_id):
    if "admin" not in session: return redirect("/")
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Student name techukovadaniki
    c.execute("SELECT name FROM students WHERE id=?", (student_id,))
    student = c.fetchone()
    student_name = student[0] if student else "Unknown"
    
    # UPDATED QUERY: sample_output add cheyabadindi
    c.execute("""SELECT tasks.question, submissions.submitted_code, 
                        submissions.time_spent_seconds, submissions.submission_date,
                        tasks.sample_output
                 FROM submissions 
                 JOIN tasks ON submissions.task_id = tasks.id 
                 WHERE submissions.student_id=? ORDER BY submissions.id ASC""", (student_id,))
    
    submissions = c.fetchall()
    conn.close()
    
    return render_template("student_submissions.html", 
                           submissions=submissions, 
                           student_name=student_name)

# ---------------- OTHER ADMIN ROUTES ---------------- #
@app.route("/add_class", methods=["GET","POST"])
def add_class():
    if "admin" not in session: return redirect("/")
    if request.method=="POST":
        conn=sqlite3.connect(DB); c=conn.cursor()
        c.execute("INSERT INTO classes(name) VALUES(?)",(request.form["name"],))
        conn.commit(); conn.close()
        return redirect("/admin")
    return render_template("add_class.html")

@app.route("/view_classes")
def view_classes():
    if "admin" not in session: return redirect("/")
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT * FROM classes")
    classes = c.fetchall(); conn.close()
    return render_template("view_classes.html", classes=classes)

@app.route("/class_students/<int:class_id>")
def class_students(class_id):
    if "admin" not in session: return redirect("/")
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("SELECT name FROM classes WHERE id=?", (class_id,))
    class_name = c.fetchone()[0]
    c.execute("SELECT * FROM students WHERE class_id=?", (class_id,))
    students = c.fetchall(); conn.close()
    return render_template("class_students.html", students=students, class_id=class_id, class_name=class_name)

@app.route("/delete_class/<int:class_id>", methods=["POST"])
def delete_class(class_id):
    if "admin" not in session: 
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("DELETE FROM classes WHERE id=?", (class_id,))
        c.execute("DELETE FROM students WHERE class_id=?", (class_id,))
        conn.commit(); conn.close()
        return jsonify({"success": True, "message": "Class and associated data deleted!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/delete_student/<int:student_id>/<int:class_id>")
def delete_student(student_id, class_id):
    if "admin" not in session: return redirect("/")
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit(); conn.close()
    return redirect(f"/class_students/{class_id}")

@app.route("/add_student", methods=["GET","POST"])
def add_student():
    if "admin" not in session: return redirect("/")
    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute("SELECT * FROM classes")
    classes=c.fetchall()
    if request.method=="POST":
        c.execute("INSERT INTO students(name,password,class_id) VALUES(?,?,?)",
                  (request.form["name"], request.form["password"], request.form["class_id"]))
        conn.commit(); conn.close()
        return redirect("/admin")
    conn.close()
    return render_template("add_student.html", classes=classes)

@app.route("/add_task", methods=["GET","POST"])
def add_task():
    if "admin" not in session: return redirect("/")
    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute("SELECT * FROM classes")
    classes=c.fetchall()
    if request.method=="POST":
        now=datetime.datetime.now()
        expiry=now+datetime.timedelta(hours=9)
        c.execute("""INSERT INTO tasks(question,sample_input,sample_output,
                     class_id,created_time,expiry_time)
                     VALUES(?,?,?,?,?,?)""",
                  (request.form["question"], request.form["sample_input"],
                   request.form["sample_output"], request.form["class_id"],
                   now.strftime("%Y-%m-%d %H:%M:%S"), expiry.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()
        return redirect("/admin")
    conn.close()
    return render_template("add_task.html", classes=classes)

# ---------------- STUDENT ROUTES ---------------- #
@app.route("/student")
def student():
    if "student_id" not in session: return redirect("/")
    class_id=session.get("class_id")
    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute("SELECT * FROM tasks WHERE class_id=?",(class_id,))
    tasks=c.fetchall(); conn.close()
    return render_template("student_dashboard.html", tasks=tasks)

# ---------------- COMPILER LOGIC ---------------- #
@app.route("/compiler/<int:task_id>", methods=["GET","POST"])
def compiler(task_id):
    if "student_id" not in session: return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
    task = c.fetchone()

    if request.method == "GET":
        session['start_time'] = datetime.datetime.now().timestamp()

    try:
        expiry = datetime.datetime.strptime(task[6], "%Y-%m-%d %H:%M:%S.%f")
    except:
        expiry = datetime.datetime.strptime(task[6], "%Y-%m-%d %H:%M:%S")
        
    now = datetime.datetime.now()
    today = str(now.date())
    result = ""
    submitted_code = ""

    if request.method == "POST":
        submitted_code = request.form.get("code", "")
        start_time = session.get('start_time', now.timestamp())
        time_spent = int(now.timestamp() - start_time)

        if now <= expiry:
            filename = f"temp_{uuid.uuid4().hex}.py"
            with open(filename, "w") as f:
                f.write(submitted_code)

            try:
                output = subprocess.check_output(
                    [sys.executable, filename],
                    input=task[2],
                    text=True,
                    timeout=5
                ).strip()

                result = output

                if output == task[3].strip():
                    c.execute("INSERT INTO submissions(student_id, task_id, submitted_code, time_spent_seconds, submission_date) VALUES(?,?,?,?,?)",
                              (session["student_id"], task_id, submitted_code, time_spent, today))
                    
                    c.execute("SELECT * FROM attendance WHERE student_id=? AND date=?",
                              (session["student_id"], today))
                    already = c.fetchone()
                    if not already:
                        c.execute("INSERT INTO attendance(student_id,date) VALUES(?,?)",
                                  (session["student_id"], today))
                    conn.commit()
                    result += f"\n\n✅ Correct! Time Spent: {time_spent}s. Attendance Marked."
            except Exception as e:
                result = "Error: " + str(e)
            finally:
                if os.path.exists(filename):
                    os.remove(filename)
        else:
            result = "Task Expired! You cannot submit anymore."

    conn.close()
    return render_template("compiler.html", task=task, result=result, code=submitted_code)

# ---------------- REPORT ---------------- #
@app.route("/report", methods=["GET","POST"])
def report():
    if "admin" not in session: return redirect("/")
    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute("SELECT * FROM classes")
    classes=c.fetchall()
    data=[]; class_id=""; start=""; end=""

    if request.method=="POST":
        class_id=request.form["class_id"]
        start=request.form["start"]; end=request.form["end"]
        c.execute("SELECT id,name,password FROM students WHERE class_id=?",(class_id,))
        students=c.fetchall()
        c.execute("""SELECT DISTINCT date(created_time) FROM tasks
                     WHERE class_id=? AND date(created_time) BETWEEN ? AND ?""", (class_id,start,end))
        total_days=len(c.fetchall())

        for s in students:
            c.execute("""SELECT DISTINCT date FROM attendance
                         WHERE student_id=? AND date BETWEEN ? AND ?""", (s[0],start,end))
            presents=len(c.fetchall())
            absents=total_days - presents if total_days>0 else 0
            percent=(presents/total_days*100) if total_days>0 else 0
            fine=absents*25
            # s[0] is student_id, added at the end for the link
            data.append((s[1],s[2],presents,absents,round(percent,2),fine, s[0]))
    conn.close()
    return render_template("report.html", classes=classes, data=data, class_id=class_id, start=start, end=end)

@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    if "admin" not in session: return redirect("/")
    class_id=request.form["class_id"]
    start=request.form["start"]; end=request.form["end"]

    conn=sqlite3.connect(DB); c=conn.cursor()
    c.execute("SELECT id,name,password FROM students WHERE class_id=?",(class_id,))
    students=c.fetchall()
    c.execute("""SELECT DISTINCT date(created_time) FROM tasks
                 WHERE class_id=? AND date(created_time) BETWEEN ? AND ?""", (class_id,start,end))
    total_days=len(c.fetchall())

    table_data=[["Username","Password","Presents","Absents","Percentage","Fine"]]
    for s in students:
        c.execute("""SELECT DISTINCT date FROM attendance
                     WHERE student_id=? AND date BETWEEN ? AND ?""", (s[0],start,end))
        presents=len(c.fetchall())
        absents=total_days - presents if total_days>0 else 0
        percent=(presents/total_days*100) if total_days>0 else 0
        fine=absents*25
        table_data.append([s[1],s[2],presents,absents, str(round(percent,2))+"%","₹"+str(fine)])
    conn.close()

    file_name="attendance_report.pdf"
    doc=SimpleDocTemplate(file_name)
    elements=[]
    elements.append(Paragraph("Class Report", getSampleStyleSheet()["Heading2"]))
    elements.append(Spacer(1,20))
    table=Table(table_data)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.grey),('GRID',(0,0),(-1,-1),1,colors.black)]))
    elements.append(table)
    doc.build(elements)
    return send_file(file_name, as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=5000)