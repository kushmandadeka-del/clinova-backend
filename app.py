
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import requests
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = "hackathon-secret-key-change-me"

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def translate_to_english(text, source_language):
    
    if source_language == "en":
        return text


    if source_language == "hi":

        roman_hindi = text.lower().strip()

        # Common Roman Hindi medical phrases
        replacements = {
            "bukhar ho raha hai": "I am having fever",
            "bukhar ho rha hai": "I am having fever",
            "bukhar hai": "I have fever",

            "sir dard ho raha hai": "I have a headache",
            "sir dard ho rha hai": "I have a headache",
            "sir mein dard hai": "I have a headache",

            "khansi ho rahi hai": "I have a cough",
            "khansi ho rha hai": "I have a cough",
            "khansi hai": "I have a cough",

            "sardi ho rahi hai": "I have a cold",
            "sardi ho rha hai": "I have a cold",
            "sardi hai": "I have a cold",

            "mujhe diabetes hai": "I have diabetes",
            "muje diabetes hai": "I have diabetes",

            "mujhe blood pressure hai": "I have high blood pressure",
            "muje blood pressure hai": "I have high blood pressure",

            "paracetamol leta hoon": "I take paracetamol",
            "paracetamol leti hoon": "I take paracetamol"
        }

        # Check for phrases inside the sentence
        for hindi_phrase, english_phrase in replacements.items():

            if hindi_phrase in roman_hindi:

                # Keep the duration if it exists
                if "3 din" in roman_hindi or "3 din se" in roman_hindi:
                    return english_phrase + " for three days"

                if "2 din" in roman_hindi or "2 din se" in roman_hindi:
                    return english_phrase + " for two days"

                if "1 din" in roman_hindi or "1 din se" in roman_hindi:
                    return english_phrase + " for one day"

                if "three days" in roman_hindi:
                    return english_phrase + " for three days"

                if "two days" in roman_hindi:
                    return english_phrase + " for two days"

                return english_phrase

    # MyMemory translation for everything else

    response = requests.get(
        "https://api.mymemory.translated.net/get",
        params={
            "q": text,
            "langpair": f"{source_language}|en"
        }
    )

    data = response.json()

    return data["responseData"]["translatedText"]

def extract_case(text):

    text = text.lower()

    symptoms = []

    if "fever" in text or "bukhar" in text:
        symptoms.append("Fever")

    if "headache" in text or "sir dard" in text:
        symptoms.append("Headache")

    if "cough" in text or "khansi" in text:
        symptoms.append("Cough")

    if "cold" in text or "sardi" in text:
        symptoms.append("Cold")

    duration = "Not mentioned"

    if "three days" in text or "3 days" in text or "3 din" in text:
        duration = "3 days"

    elif "two days" in text or "2 days" in text or "2 din" in text:
        duration = "2 days"

    elif "one day" in text or "1 day" in text or "1 din" in text:
        duration = "1 day"

    medical_history = "Not mentioned"

    if "diabetes" in text:
        medical_history = "Diabetes"

    elif "blood pressure" in text or "bp" in text:
        medical_history = "High blood pressure"

    medications = "Not mentioned"

    if "paracetamol" in text:
        medications = "Paracetamol"

    elif "medicine" in text or "medication" in text:
        medications = "Medicine mentioned"

    allergies = "Not mentioned"

    if "allergic to" in text:
        allergies = "Allergy mentioned"

    elif "allergy" in text:
        allergies = "Allergy mentioned"

    return {
        "symptoms": symptoms,
        "duration": duration,
        "medical_history": medical_history,
        "medications": medications,
        "allergies": allergies
    }

@app.route("/translate", methods=["POST"])
def translate():

    text = request.form["text"]
    language = request.form["language"]

    translated = translate_to_english(text, language)

    return translated

@app.route("/analyze", methods=["POST"])
def analyze():

    text = request.form["text"]

    result = extract_case(text)

    return result


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

    # Add ABHA ID column if it does not exist
    columns = c.execute("PRAGMA table_info(patients)").fetchall()
    column_names = [column["name"] for column in columns]

    if "abha_id" not in column_names:
        c.execute("ALTER TABLE patients ADD COLUMN abha_id TEXT")

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
        doctor_id INTEGER,
        symptoms TEXT,
        medical_history TEXT,
        vitals TEXT,
        medications TEXT,
        allergies TEXT,
        lab_reports TEXT,
        duration TEXT,
        original_transcript TEXT,
        english_translation TEXT,
        status TEXT DEFAULT 'SUBMITTED',
        created_at TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )
""")
    
    # Hospitals table
    c.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            has_icu INTEGER DEFAULT 0,
            has_nicu INTEGER DEFAULT 0,
            has_obstetric_emergency INTEGER DEFAULT 0,
            has_blood_bank INTEGER DEFAULT 0,
            available_icu_beds INTEGER DEFAULT 0,
            available_nicu_beds INTEGER DEFAULT 0,
            ambulance_available INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    
    hospital_columns = c.execute(
        "PRAGMA table_info(hospitals)"
    ).fetchall()

    hospital_column_names = [
        column["name"] for column in hospital_columns
    ]

    if "distance_km" not in hospital_column_names:
        c.execute(
            "ALTER TABLE hospitals ADD COLUMN distance_km REAL DEFAULT 0"
        )

    # Pregnancy profiles table
    c.execute("""
        CREATE TABLE IF NOT EXISTS pregnancy_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            hospital_id INTEGER NOT NULL,
            lmp_date TEXT,
            edd_date TEXT,
            blood_group TEXT,
            risk_status TEXT DEFAULT 'Normal',
            created_at TEXT NOT NULL,

            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id),
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        )
    """)

    # Pregnancy medications table
    c.execute("""
        CREATE TABLE IF NOT EXISTS pregnancy_medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pregnancy_id INTEGER NOT NULL,
            medicine_name TEXT NOT NULL,
            dosage TEXT,
            frequency TEXT,
            start_date TEXT,
            end_date TEXT,
            notes TEXT,

            FOREIGN KEY (pregnancy_id) REFERENCES pregnancy_profiles(id)
        )
    """)

    # Pregnancy checkups table
    c.execute("""
        CREATE TABLE IF NOT EXISTS pregnancy_checkups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pregnancy_id INTEGER NOT NULL,
            checkup_date TEXT NOT NULL,
            pregnancy_week TEXT,
            blood_pressure TEXT,
            weight TEXT,
            hemoglobin TEXT,
            blood_sugar TEXT,
            ultrasound_report TEXT,
            doctor_notes TEXT,

            FOREIGN KEY (pregnancy_id) REFERENCES pregnancy_profiles(id)
        )
    """)

    # Emergency transfer requests table
    c.execute("""
        CREATE TABLE IF NOT EXISTS transfer_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pregnancy_id INTEGER NOT NULL,
            from_hospital_id INTEGER NOT NULL,
            to_hospital_id INTEGER NOT NULL,
            required_facility TEXT NOT NULL,
            emergency_level TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            responded_at TEXT,

            FOREIGN KEY (pregnancy_id) REFERENCES pregnancy_profiles(id),
            FOREIGN KEY (from_hospital_id) REFERENCES hospitals(id),
            FOREIGN KEY (to_hospital_id) REFERENCES hospitals(id)
        )
    """)
    
    transfer_columns = c.execute(
        "PRAGMA table_info(transfer_requests)"
    ).fetchall()

    transfer_column_names = [
        column["name"] for column in transfer_columns
    ]

    if "attempt_number" not in transfer_column_names:
        c.execute(
            "ALTER TABLE transfer_requests ADD COLUMN attempt_number INTEGER DEFAULT 1"
        )

        # Add lab_reports column if it does not already exist
    columns = c.execute("PRAGMA table_info(case_records)").fetchall()

    column_names = [column["name"] for column in columns]
    
    if "lab_reports" not in column_names:
        c.execute("ALTER TABLE case_records ADD COLUMN lab_reports TEXT")
    
    if "doctor_id" not in column_names:
        c.execute("ALTER TABLE case_records ADD COLUMN doctor_id INTEGER")
    
    if "duration" not in column_names:
        c.execute("ALTER TABLE case_records ADD COLUMN duration TEXT")
    
    if "original_transcript" not in column_names:
        c.execute("ALTER TABLE case_records ADD COLUMN original_transcript TEXT")
    
    if "english_translation" not in column_names:
        c.execute("ALTER TABLE case_records ADD COLUMN english_translation TEXT")
    
    if "status" not in column_names:
        c.execute("ALTER TABLE case_records ADD COLUMN status TEXT DEFAULT 'SUBMITTED'")

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

    c.execute("""
        CREATE TABLE IF NOT EXISTS access_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,

            prescriptions INTEGER DEFAULT 0,
            lab_reports INTEGER DEFAULT 0,
            consultations INTEGER DEFAULT 0,

            status TEXT NOT NULL DEFAULT 'PENDING',

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
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
        abha_id = request.form.get("abha_id","").strip()

        conn = get_db()

        conn.execute(
            """
            INSERT INTO patients
            (name, age, gender, phone, abha_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                age,
                gender,
                phone,
                abha_id,
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

        # Check doctor login credentials
        user = conn.execute(
            """SELECT * FROM users
               WHERE username = ?
               AND password = ?
               AND role = 'doctor'""",
            (username, password)
        ).fetchone()

        if user:

            # Save basic login information
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            # Find the doctor's profile
            doctor = conn.execute(
                """SELECT * FROM doctors
                   WHERE email = ?""",
                (user["username"],)
            ).fetchone()

            if doctor:
                session["doctor_id"] = doctor["id"]
            else:
                session["doctor_id"] = None

            conn.close()

            return redirect(url_for("doctor_requests"))
        conn.close()

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
        lab_reports = request.form["lab_reports"]

        conn.execute(
    """INSERT INTO case_records
       (patient_id, symptoms, medical_history, vitals, medications,
        allergies, lab_reports, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
    (patient_id, symptoms, medical_history, vitals, medications,
     allergies, lab_reports,
     datetime.now().strftime("%Y-%m-%d %H:%M"))
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

    conn = get_db()

    patients = conn.execute(
        "SELECT * FROM patients ORDER BY name"
    ).fetchall()

    doctors = conn.execute(
        "SELECT * FROM doctors ORDER BY name"
    ).fetchall()

    conn.close()

    return render_template(
        "talk_to_doctor.html",
        patients=patients,
        doctors=doctors
    )

    
@app.route("/submit_case", methods=["POST"])
def submit_case():

    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")

    original_transcript = request.form.get("original_transcript")
    english_translation = request.form.get("english_translation")

    symptoms = request.form.get("symptoms")
    duration = request.form.get("duration")
    medical_history = request.form.get("medical_history")
    medications = request.form.get("medications")
    allergies = request.form.get("allergies")

    if not patient_id or not doctor_id:
        return "Please select a patient and doctor."

    conn = get_db()

    patient = conn.execute(
        "SELECT * FROM patients WHERE id = ?",
        (patient_id,)
    ).fetchone()

    doctor = conn.execute(
        "SELECT * FROM doctors WHERE id = ?",
        (doctor_id,)
    ).fetchone()

    if not patient:
        conn.close()
        return "Patient not found."

    if not doctor:
        conn.close()
        return "Doctor not found."

    conn.execute(
        """
        INSERT INTO case_records
        (
            patient_id,
            doctor_id,
            symptoms,
            medical_history,
            vitals,
            medications,
            allergies,
            duration,
            original_transcript,
            english_translation,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_id,
            doctor_id,
            symptoms,
            medical_history,
            "",
            medications,
            allergies,
            duration,
            original_transcript,
            english_translation,
            "SUBMITTED",
            datetime.now().strftime("%Y-%m-%d %H:%M")
        )
    )

    conn.commit()
    conn.close()

    return "Case submitted successfully to the doctor."

@app.route("/language")
def language():
    return render_template("language.html")

@app.route("/emergency")
def emergency():
    return render_template("emergency.html")

@app.route("/emergency_patient", methods=["GET", "POST"])
def emergency_patient():

    if request.method == "POST":

        emergency_type = request.form["emergency_type"]
        symptoms = request.form["symptoms"]
        severity = request.form["severity"]

        return f"""
        <h1>🚨 Emergency Submitted</h1>

        <p><strong>Emergency Type:</strong> {emergency_type}</p>

        <p><strong>Description:</strong> {symptoms}</p>

        <p><strong>Emergency Level:</strong> {severity}</p>

        <p>Please seek immediate medical assistance.</p>

        <a href="/emergency">Back to Emergency</a>
        """ 

    return render_template("emergency_patient.html")


@app.route("/emergency_referral_general", methods=["GET", "POST"])
def emergency_referral_general():

    if request.method == "POST":

        emergency_type = request.form["emergency_type"]
        required_facility = request.form["required_facility"]
        emergency_level = request.form["emergency_level"]
        description = request.form["description"]

        return f"""
        <h1>🏥 Emergency Referral Requested</h1>

        <p><strong>Emergency Type:</strong> {emergency_type}</p>
        <p><strong>Required Facility:</strong> {required_facility}</p>
        <p><strong>Emergency Level:</strong> {emergency_level}</p>
        <p><strong>Description:</strong> {description}</p>

        <p>Your emergency referral request has been submitted.</p>

        <a href="/emergency">Back to Emergency Care</a>
        """

    return render_template("emergency_referral_general.html")

@app.route("/pharmacy")
def pharmacy():
    return render_template("pharmacy.html")

@app.route("/pregnancy_care")
def pregnancy_care():
    return render_template("pregnancy.html")

#hospital
@app.route("/hospital_register", methods=["GET", "POST"])
def hospital_register():

    if request.method == "POST":

        name = request.form["name"]
        address = request.form["address"]
        phone = request.form["phone"]

        has_icu = 1 if request.form.get("has_icu") else 0
        has_nicu = 1 if request.form.get("has_nicu") else 0
        has_obstetric_emergency = 1 if request.form.get("has_obstetric_emergency") else 0
        has_blood_bank = 1 if request.form.get("has_blood_bank") else 0
        ambulance_available = 1 if request.form.get("ambulance_available") else 0

        available_icu_beds = request.form["available_icu_beds"]
        available_nicu_beds = request.form["available_nicu_beds"]

        conn = get_db()

        conn.execute(
            """
            INSERT INTO hospitals
            (
                name,
                address,
                phone,
                has_icu,
                has_nicu,
                has_obstetric_emergency,
                has_blood_bank,
                available_icu_beds,
                available_nicu_beds,
                ambulance_available,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                address,
                phone,
                has_icu,
                has_nicu,
                has_obstetric_emergency,
                has_blood_bank,
                available_icu_beds,
                available_nicu_beds,
                ambulance_available,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        )

        conn.commit()
        conn.close()

        return "Hospital registered successfully."

    return render_template("hospital_register.html")

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

        try:

            # Save doctor information
            conn.execute(
                """INSERT INTO doctors
                   (name, registration_number, specialization,
                    hospital, phone, email, password, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
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

            # Create login account for the doctor
            conn.execute(
                """INSERT INTO users
                   (username, password, role)
                   VALUES (?, ?, ?)""",
                (
                    email,
                    password,
                    "doctor"
                )
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.rollback()
            conn.close()

            return "A doctor with this email already exists."

        conn.close()

        return redirect(url_for("doctor_login"))

    return render_template("dr_register.html")

#------------pregnancy profile----------------
@app.route("/pregnancy/<int:pregnancy_id>/checkup", methods=["GET", "POST"])
def pregnancy_checkup(pregnancy_id):

    conn = get_db()

    pregnancy = conn.execute(
        "SELECT * FROM pregnancy_profiles WHERE id = ?",
        (pregnancy_id,)
    ).fetchone()

    if not pregnancy:
        conn.close()
        return "Pregnancy record not found."

    if request.method == "POST":

        checkup_date = request.form["checkup_date"]
        pregnancy_week = request.form.get("pregnancy_week")
        blood_pressure = request.form.get("blood_pressure")
        weight = request.form.get("weight")
        hemoglobin = request.form.get("hemoglobin")
        blood_sugar = request.form.get("blood_sugar")
        ultrasound_report = request.form.get("ultrasound_report")
        doctor_notes = request.form.get("doctor_notes")

        conn.execute(
            """
            INSERT INTO pregnancy_checkups
            (
                pregnancy_id,
                checkup_date,
                pregnancy_week,
                blood_pressure,
                weight,
                hemoglobin,
                blood_sugar,
                ultrasound_report,
                doctor_notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pregnancy_id,
                checkup_date,
                pregnancy_week,
                blood_pressure,
                weight,
                hemoglobin,
                blood_sugar,
                ultrasound_report,
                doctor_notes
            )
        )

        conn.commit()
        conn.close()

        return redirect(
            url_for(
                "pregnancy",
                pregnancy_id=pregnancy_id
            )
        )

    conn.close()

    return render_template(
        "pregnancy_checkup.html",
        pregnancy=pregnancy
    )

#---------------------medication------------------

@app.route("/pregnancy/<int:pregnancy_id>/medication", methods=["GET", "POST"])
def pregnancy_medication(pregnancy_id):

    conn = get_db()

    pregnancy = conn.execute(
        "SELECT * FROM pregnancy_profiles WHERE id = ?",
        (pregnancy_id,)
    ).fetchone()

    if not pregnancy:
        conn.close()
        return "Pregnancy record not found."

    if request.method == "POST":

        medicine_name = request.form["medicine_name"]
        dosage = request.form.get("dosage")
        frequency = request.form.get("frequency")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        notes = request.form.get("notes")

        conn.execute(
            """
            INSERT INTO pregnancy_medications
            (
                pregnancy_id,
                medicine_name,
                dosage,
                frequency,
                start_date,
                end_date,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pregnancy_id,
                medicine_name,
                dosage,
                frequency,
                start_date,
                end_date,
                notes
            )
        )

        conn.commit()
        conn.close()

        return redirect(
            url_for(
                "pregnancy",
                pregnancy_id=pregnancy_id
            )
        )

    conn.close()

    return render_template(
        "pregnancy_medication.html",
        pregnancy=pregnancy
    )

#----------------------------emergency referral--------------

@app.route("/pregnancy/<int:pregnancy_id>/emergency", methods=["GET", "POST"])
def emergency_referral(pregnancy_id):

    conn = get_db()

    pregnancy = conn.execute(
        """
        SELECT * FROM pregnancy_profiles
        WHERE id = ?
        """,
        (pregnancy_id,)
    ).fetchone()

    if not pregnancy:
        conn.close()
        return "Pregnancy record not found."

    patient = conn.execute(
        """
        SELECT * FROM patients
        WHERE id = ?
        """,
        (pregnancy["patient_id"],)
    ).fetchone()

    current_hospital = conn.execute(
        """
        SELECT * FROM hospitals
        WHERE id = ?
        """,
        (pregnancy["hospital_id"],)
    ).fetchone()

    if request.method == "POST":

        required_facility = request.form["required_facility"]
        emergency_level = request.form["emergency_level"]

        hospitals = conn.execute(
            """
            SELECT * FROM hospitals
            WHERE id != ?
            ORDER BY distance_km ASC
            """,
            (pregnancy["hospital_id"],)
        ).fetchall()

        selected_hospital = None

        for hospital in hospitals:

            suitable = False

            if required_facility == "NICU":
                suitable = (
                    hospital["has_nicu"] == 1
                    and hospital["available_nicu_beds"] > 0
                )

            elif required_facility == "ICU":
                suitable = (
                    hospital["has_icu"] == 1
                    and hospital["available_icu_beds"] > 0
                )

            elif required_facility == "Obstetric Emergency":
                suitable = hospital["has_obstetric_emergency"] == 1

            elif required_facility == "Blood Bank":
                suitable = hospital["has_blood_bank"] == 1

            elif required_facility == "ICU + NICU":
                suitable = (
                    hospital["has_icu"] == 1
                    and hospital["has_nicu"] == 1
                    and hospital["available_icu_beds"] > 0
                    and hospital["available_nicu_beds"] > 0
                )

            elif required_facility == "Obstetric Emergency + NICU":
                suitable = (
                    hospital["has_obstetric_emergency"] == 1
                    and hospital["has_nicu"] == 1
                    and hospital["available_nicu_beds"] > 0
                )

            if suitable:
                selected_hospital = hospital
                break

        if not selected_hospital:
            conn.close()

            return """
            <h2>No suitable hospital currently found.</h2>
            <p>Please contact emergency services immediately.</p>
            """

        conn.execute(
            """
            INSERT INTO transfer_requests
            (
                pregnancy_id,
                from_hospital_id,
                to_hospital_id,
                required_facility,
                emergency_level,
                status,
                attempt_number,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pregnancy_id,
                current_hospital["id"],
                selected_hospital["id"],
                required_facility,
                emergency_level,
                "PENDING",
                1,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        )

        conn.commit()

        request_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        conn.close()

        return redirect(
            url_for(
                "hospital_requests"
            )
        )

    conn.close()

    return render_template(
        "emergency_referral.html",
        pregnancy=pregnancy,
        patient=patient,
        current_hospital=current_hospital
    )


#----------------hospital request----------
@app.route("/hospital_requests")
def hospital_requests():

    conn = get_db()

    hospitals = conn.execute(
        """
        SELECT * FROM hospitals
        ORDER BY name
        """
    ).fetchall()

    selected_hospital_id = request.args.get(
        "hospital_id",
        type=int
    )

    selected_hospital = None
    requests = []

    if selected_hospital_id:

        selected_hospital = conn.execute(
            """
            SELECT * FROM hospitals
            WHERE id = ?
            """,
            (selected_hospital_id,)
        ).fetchone()

        requests = conn.execute(
            """
            SELECT
                transfer_requests.*,
                patients.name AS patient_name,
                hospitals.name AS from_hospital_name
            FROM transfer_requests

            JOIN pregnancy_profiles
            ON transfer_requests.pregnancy_id =
               pregnancy_profiles.id

            JOIN patients
            ON pregnancy_profiles.patient_id =
               patients.id

            JOIN hospitals
            ON transfer_requests.from_hospital_id =
               hospitals.id

            WHERE transfer_requests.to_hospital_id = ?
            AND transfer_requests.status = 'PENDING'

            ORDER BY transfer_requests.created_at ASC
            """,
            (selected_hospital_id,)
        ).fetchall()

    conn.close()

    return render_template(
        "hospital_requests.html",
        hospitals=hospitals,
        selected_hospital=selected_hospital,
        selected_hospital_id=selected_hospital_id,
        requests=requests
    )

#-----------------------------pregnancy-register---------------------
@app.route("/pregnancy_register", methods=["GET", "POST"])
def pregnancy_register():

    conn = get_db()

    # Get existing patients
    patients = conn.execute("""
        SELECT *
        FROM patients
        ORDER BY name
    """).fetchall()

    # Get existing doctors
    doctors = conn.execute("""
        SELECT *
        FROM doctors
        ORDER BY name
    """).fetchall()

    # Get existing hospitals
    hospitals = conn.execute("""
        SELECT *
        FROM hospitals
        ORDER BY name
    """).fetchall()

    if request.method == "POST":

        patient_id = request.form["patient_id"]
        doctor_id = request.form["doctor_id"]
        hospital_id = request.form["hospital_id"]

        lmp_date = request.form.get("lmp_date")
        edd_date = request.form.get("edd_date")
        blood_group = request.form.get("blood_group")
        risk_status = request.form.get("risk_status", "Normal")

        conn.execute("""
            INSERT INTO pregnancy_profiles
            (
                patient_id,
                doctor_id,
                hospital_id,
                lmp_date,
                edd_date,
                blood_group,
                risk_status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            doctor_id,
            hospital_id,
            lmp_date,
            edd_date,
            blood_group,
            risk_status,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        conn.commit()

        pregnancy_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        conn.close()

        return redirect(
            url_for("pregnancy", pregnancy_id=pregnancy_id)
        )

    conn.close()

    return render_template(
        "pregnancy_register.html",
        patients=patients,
        doctors=doctors,
        hospitals=hospitals
    )
#-----------------------pregnancy-profile--------------
@app.route("/pregnancy/<int:pregnancy_id>")
def pregnancy(pregnancy_id):

    conn = get_db()

    # Get pregnancy profile
    pregnancy = conn.execute(
        """
        SELECT *
        FROM pregnancy_profiles
        WHERE id = ?
        """,
        (pregnancy_id,)
    ).fetchone()

    if not pregnancy:
        conn.close()
        return "Pregnancy record not found."

    # Get patient
    patient = conn.execute(
        """
        SELECT *
        FROM patients
        WHERE id = ?
        """,
        (pregnancy["patient_id"],)
    ).fetchone()

    # Get doctor
    doctor = conn.execute(
        """
        SELECT *
        FROM doctors
        WHERE id = ?
        """,
        (pregnancy["doctor_id"],)
    ).fetchone()

    # Get hospital
    hospital = conn.execute(
        """
        SELECT *
        FROM hospitals
        WHERE id = ?
        """,
        (pregnancy["hospital_id"],)
    ).fetchone()

    # Get medications
    medications = conn.execute(
        """
        SELECT *
        FROM pregnancy_medications
        WHERE pregnancy_id = ?
        ORDER BY start_date DESC
        """,
        (pregnancy_id,)
    ).fetchall()

    # Get checkups
    checkups = conn.execute(
        """
        SELECT *
        FROM pregnancy_checkups
        WHERE pregnancy_id = ?
        ORDER BY checkup_date DESC
        """,
        (pregnancy_id,)
    ).fetchall()

    # Calculate pregnancy week
    pregnancy_week = "Not available"

    if pregnancy["lmp_date"]:

        try:
            lmp = datetime.strptime(
                pregnancy["lmp_date"],
                "%Y-%m-%d"
            ).date()

            today = date.today()

            days = (today - lmp).days

            if days >= 0:
                pregnancy_week = days // 7

        except ValueError:
            pregnancy_week = "Not available"

    conn.close()

    return render_template(
        "pregnancy_profile.html",
        pregnancy=pregnancy,
        patient=patient,
        doctor=doctor,
        hospital=hospital,
        medications=medications,
        checkups=checkups,
        pregnancy_week=pregnancy_week
    )
    
#--------------------pregnancy-patients--------------

@app.route("/pregnancy_patients")
def pregnancy_patients():

    conn = get_db()

    pregnancies = conn.execute("""
        SELECT
            pregnancy_profiles.*,
            patients.name AS patient_name,
            patients.age AS patient_age,
            patients.gender AS patient_gender,
            patients.phone AS patient_phone,
            doctors.name AS doctor_name,
            hospitals.name AS hospital_name
        FROM pregnancy_profiles

        JOIN patients
            ON pregnancy_profiles.patient_id = patients.id

        LEFT JOIN doctors
            ON pregnancy_profiles.doctor_id = doctors.id

        LEFT JOIN hospitals
            ON pregnancy_profiles.hospital_id = hospitals.id

        ORDER BY pregnancy_profiles.created_at DESC
    """).fetchall()

    conn.close()

    return render_template(
        "pregnancy_patients.html",
        pregnancies=pregnancies
    )
#--------------hospital-list--------------------
@app.route("/hospital_list")
def hospital_list():

    conn = get_db()

    hospitals = conn.execute("""
        SELECT *
        FROM hospitals
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "hospital_list.html",
        hospitals=hospitals
    )
#----------------------accept referral--------------
@app.route(
    "/hospital_requests/<int:request_id>/accept",
    methods=["POST"]
)
def accept_referral(request_id):

    hospital_id = request.form["hospital_id"]

    conn = get_db()

    transfer = conn.execute(
        """
        SELECT * FROM transfer_requests
        WHERE id = ?
        AND to_hospital_id = ?
        AND status = 'PENDING'
        """,
        (request_id, hospital_id)
    ).fetchone()

    if not transfer:
        conn.close()
        return "Request not found."

    conn.execute(
        """
        UPDATE transfer_requests
        SET status = 'ACCEPTED',
            responded_at = ?
        WHERE id = ?
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            request_id
        )
    )

    conn.commit()
    conn.close()

    return """
    <h2>Referral Accepted</h2>
    <p>The hospital has accepted the emergency referral.</p>
    <p>The patient can now be transferred to the receiving hospital.</p>
    <a href="/hospital_requests">Back to Hospital Requests</a>
    """
    
    #---------------------reject referral----------------------
@app.route(
    "/hospital_requests/<int:request_id>/reject",
    methods=["POST"]
)
def reject_referral(request_id):

    hospital_id = request.form["hospital_id"]

    conn = get_db()

    transfer = conn.execute(
        """
        SELECT * FROM transfer_requests
        WHERE id = ?
        AND to_hospital_id = ?
        AND status = 'PENDING'
        """,
        (request_id, hospital_id)
    ).fetchone()

    if not transfer:
        conn.close()
        return "Request not found."

    conn.execute(
        """
        UPDATE transfer_requests
        SET status = 'REJECTED',
            responded_at = ?
        WHERE id = ?
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            request_id
        )
    )

    next_hospital = conn.execute(
        """
        SELECT * FROM hospitals
        WHERE id != ?
        AND id != ?

        AND id NOT IN (
            SELECT to_hospital_id
            FROM transfer_requests
            WHERE pregnancy_id = ?
        )

        ORDER BY distance_km ASC
        """,
        (
            transfer["from_hospital_id"],
            hospital_id,
            transfer["pregnancy_id"]
        )
    ).fetchall()

    selected_hospital = None

    for hospital in next_hospital:

        suitable = False

        facility = transfer["required_facility"]

        if facility == "NICU":

            suitable = (
                hospital["has_nicu"] == 1
                and hospital["available_nicu_beds"] > 0
            )

        elif facility == "ICU":

            suitable = (
                hospital["has_icu"] == 1
                and hospital["available_icu_beds"] > 0
            )

        elif facility == "Obstetric Emergency":

            suitable = (
                hospital["has_obstetric_emergency"] == 1
            )

        elif facility == "Blood Bank":

            suitable = (
                hospital["has_blood_bank"] == 1
            )

        elif facility == "ICU + NICU":

            suitable = (
                hospital["has_icu"] == 1
                and hospital["has_nicu"] == 1
                and hospital["available_icu_beds"] > 0
                and hospital["available_nicu_beds"] > 0
            )

        elif facility == "Obstetric Emergency + NICU":

            suitable = (
                hospital["has_obstetric_emergency"] == 1
                and hospital["has_nicu"] == 1
                and hospital["available_nicu_beds"] > 0
            )

        if suitable:
            selected_hospital = hospital
            break

    if not selected_hospital:

        conn.commit()
        conn.close()

        return """
        <h2>No other suitable hospital found.</h2>
        <p>Please contact emergency services immediately.</p>
        <a href="/hospital_requests">Back</a>
        """

    attempt_number = transfer["attempt_number"] + 1

    conn.execute(
        """
        INSERT INTO transfer_requests
        (
            pregnancy_id,
            from_hospital_id,
            to_hospital_id,
            required_facility,
            emergency_level,
            status,
            attempt_number,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            transfer["pregnancy_id"],
            transfer["from_hospital_id"],
            selected_hospital["id"],
            transfer["required_facility"],
            transfer["emergency_level"],
            "PENDING",
            attempt_number,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        )
    )

    conn.commit()
    conn.close()

    return """
    <h2>Request Rejected</h2>
    <p>
        The system has automatically sent the request
        to the next suitable hospital.
    </p>
    <a href="/hospital_requests">Back to Hospital Requests</a>
    """
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



@app.route("/request_access/<int:patient_id>", methods=["GET", "POST"])
def request_access(patient_id):

    conn = get_db()

    # Find the patient
    patient = conn.execute(
        "SELECT * FROM patients WHERE id = ?",
        (patient_id,)
    ).fetchone()

    if not patient:
        conn.close()
        return "Patient not found"

    # Get all registered doctors
    doctors = conn.execute(
        "SELECT * FROM doctors ORDER BY name"
    ).fetchall()

    if request.method == "POST":

        doctor_id = request.form.get("doctor_id")

        prescriptions = 1 if request.form.get("prescriptions") else 0
        lab_reports = 1 if request.form.get("lab_reports") else 0
        consultations = 1 if request.form.get("consultations") else 0

        # Make sure at least one record type is selected
        if prescriptions == 0 and lab_reports == 0 and consultations == 0:
            conn.close()
            return "Please select at least one type of record."

        # Check that the doctor exists
        doctor = conn.execute(
            "SELECT * FROM doctors WHERE id = ?",
            (doctor_id,)
        ).fetchone()

        if not doctor:
            conn.close()
            return "Doctor not found."

        # Check if there is already a pending request
        existing = conn.execute(
            """SELECT * FROM access_requests
               WHERE patient_id = ?
               AND doctor_id = ?
               AND status = 'PENDING'""",
            (patient_id, doctor_id)
        ).fetchone()

        if existing:
            conn.close()
            return "You already have a pending request for this doctor."

        # Create the request
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn.execute(
            """INSERT INTO access_requests
               (patient_id, doctor_id,
                prescriptions, lab_reports, consultations,
                status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                patient_id,
                doctor_id,
                prescriptions,
                lab_reports,
                consultations,
                "PENDING",
                now,
                now
            )
        )

        conn.commit()
        conn.close()

        return "Access request sent successfully."

    conn.close()

    return render_template(
        "request_access.html",
        patient=patient,
        doctors=doctors
    )
  #  ----------------------Dr Requests----------------------

@app.route("/doctor_requests")
def doctor_requests():

    if session.get("role") != "doctor":
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")

    if not doctor_id:
        return "Doctor profile not found."

    conn = get_db()

    doctor = conn.execute(
        "SELECT * FROM doctors WHERE id = ?",
        (doctor_id,)
    ).fetchone()

    requests = conn.execute(
        """SELECT access_requests.*,
                  patients.name AS patient_name
           FROM access_requests
           JOIN patients
           ON access_requests.patient_id = patients.id
           WHERE access_requests.doctor_id = ?
           AND access_requests.status = 'PENDING'
           ORDER BY access_requests.created_at DESC""",
        (doctor_id,)
    ).fetchall()

    submitted_cases = conn.execute(
        """
        SELECT case_records.*,
               patients.name AS patient_name
        FROM case_records
        JOIN patients
        ON case_records.patient_id = patients.id
        WHERE case_records.doctor_id = ?
        AND case_records.status = 'SUBMITTED'
        ORDER BY case_records.created_at DESC
        """,
        (doctor_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "doctor_requests.html",
        doctor=doctor,
        requests=requests,
        submitted_cases=submitted_cases
    )

# ---------------- RUN APP ----------------
if __name__ == "__main__":

    # result = extract_case(
    #     "I have fever and headache for three days."
    # )

    # print(result)

    init_db()
    app.run(debug=True)

