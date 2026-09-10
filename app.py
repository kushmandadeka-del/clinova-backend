
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "hackathon-secret-key-change-me"

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Patients table
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            created_at TEXT
        )
    """)

    # Case records table
    c.execute("""
        CREATE TABLE IF NOT EXISTS case_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            symptoms TEXT,
            medical_history TEXT,
            vitals TEXT,
            medications TEXT,
            allergies TEXT,
            created_at TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)

    # Doctors table
    c.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            registration_number TEXT NOT NULL,
            specialization TEXT NOT NULL,
            hospital TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Create default users only if no users exist
    c.execute("SELECT COUNT(*) FROM users")

    if c.fetchone()[0] == 0:
        c.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """,
            ("staff1", "staff123", "staff")
        )

        c.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """,
            ("doctor1", "doctor123", "doctor")
        )

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    search = request.args.get("search", "")

    conn = get_db()

    if search:
        patients = conn.execute(
            """
            SELECT * FROM patients
            WHERE name LIKE ?
            ORDER BY created_at DESC
            """,
            (f"%{search}%",)
        ).fetchall()
    else:
        patients = conn.execute(
            """
            SELECT * FROM patients
            ORDER BY created_at DESC
            """
        ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        patients=patients,
        search=search
    )


# ---------------- REGISTER PATIENT ----------------

@app.route("/register_patient", methods=["GET", "POST"])
def register_patient():

    if request.method == "POST":

        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]

        conn = get_db()

        conn.execute(
            """
            INSERT INTO patients
            (name, age, gender, phone, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                age,
                gender,
                phone,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("register_patient.html")


# ---------------- APPOINTMENTS ----------------

@app.route("/appointments")
def appointments():

    conn = get_db()

    patients = conn.execute(
        """
        SELECT * FROM patients
        ORDER BY created_at DESC
        """
    ).fetchall()

    pending = []
    seen = []

    for patient in patients:

        record = conn.execute(
            """
            SELECT COUNT(*)
            FROM case_records
            WHERE patient_id = ?
            """,
            (patient["id"],)
        ).fetchone()

        if record[0] == 0:
            pending.append(patient)
        else:
            seen.append(patient)

    conn.close()

    return render_template(
        "appointments.html",
        pending=pending,
        seen=seen
    )


# ---------------- STAFF LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ?
            AND password = ?
            """,
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


# ---------------- DOCTOR LOGIN ----------------

@app.route("/doctor_login", methods=["GET", "POST"])
def doctor_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            """
            SELECT * FROM users
            WHERE username = ?
            AND password = ?
            AND role = 'doctor'
            """,
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("appointments"))

        return render_template(
            "doctor_login.html",
            error="Invalid username or password"
        )

    return render_template("doctor_login.html")


# ---------------- CASE FORM ----------------

@app.route("/case_form/<int:patient_id>", methods=["GET", "POST"])
def case_form(patient_id):

    conn = get_db()

    patient = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()


    if request.method == "POST":

        symptoms = request.form["symptoms"]
        medical_history = request.form["medical_history"]
        vitals = request.form["vitals"]
        medications = request.form["medications"]
        allergies = request.form["allergies"]

        conn.execute(
            """
            INSERT INTO case_records
            (
                patient_id,
                symptoms,
                medical_history,
                vitals,
                medications,
                allergies,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                symptoms,
                medical_history,
                vitals,
                medications,
                allergies,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    conn.close()

    return render_template(
        "case_form.html",
        patient=patient
    )
@app.route("/lab")
def lab():
    return render_template("lab.html")

@app.route("/generic")
def generic():
    return render_template("generic.html")

@app.route("/new_appointment")
def new_appointment():
    return render_template("new_appointment.html")


@app.route("/patient_history")
def patient_history():
    return render_template("patient_history.html")

@app.route("/talk_to_doctor")
def talk_to_doctor():
    return render_template("talk_to_doctor.html")

@app.route("/language")
def language():
    return render_template("language.html")

@app.route("/emergency")
def emergency():
    return render_template("emergency.html")

@app.route("/pharmacy")
def pharmacy():
    return render_template("pharmacy.html")

#------------------ DOCTOR REGISTRATION ----------------
@app.route("/doctor_register", methods=["GET", "POST"])
def doctor_register():

    if request.method == "POST":

        name = request.form["doctor-name"]
        registration_number = request.form["registration-number"]
        specialization = request.form["specialization"]
        hospital = request.form["hospital"]
        phone = request.form["phone"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm-password"]

        # Check passwords
        if password != confirm_password:
            return "Passwords do not match"

        conn = get_db()

        conn.execute(
            """
            INSERT INTO doctors
            (name, registration_number, specialization, hospital,
             phone, email, password, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                registration_number,
                specialization,
                hospital,
                phone,
                email,
                password,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("doctor_login"))

    return render_template("dr_register.html")


# ---------------- VIEW PATIENT RECORD ----------------

@app.route("/view_record/<int:patient_id>")
def view_record(patient_id):

    conn = get_db()

    patient = conn.execute(
        """
        SELECT * FROM patients
        WHERE id = ?
        """,
        (patient_id,)
    ).fetchone()

    records = conn.execute(
        """
        SELECT * FROM case_records
        WHERE patient_id = ?
        ORDER BY created_at DESC
        """,
        (patient_id,)
    ).fetchall()

    conn.close()

    summaries = []

    for record in records:

        summary = (
            f"Patient reported: {record['symptoms']}. "
            f"Medical history: {record['medical_history'] or 'None reported'}. "
            f"Vitals: {record['vitals'] or 'None recorded'}. "
            f"Current medications: {record['medications'] or 'None'}. "
            f"Allergies: {record['allergies'] or 'None known'}."
        )

        summaries.append(summary)

    return render_template(
        "view_record.html",
        patient=patient,
        records=records,
        summaries=summaries
    )


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

