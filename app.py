"""
 OOP classes die ik heb gebruikt in app.py:
   - DatabaseManager    : Verwant aan een 'Model' in MVC, beheert alle database-interacties
   - User               : Verbonden aan een 'Model' in MVC, vertegenwoordigt een ingelogde gebruiker
   - Patient            : Verbonden aan een 'Model' in MVC, vertegenwoordigt een patiëntrecord
   - FileUploadHandler  : Verbonden aan een 'Controller' in MVC, beheert de logica van bestand uploads
   - App                : Behoort tot de 'Controller' in MVC, zet Flask op en definieert alle routes
   - Templates          : Behoort tot de 'View' in MVC, HTML-bestanden in de 'templates' map die de gebruikersinterface vormen ;)
 
 Hoe start je het:
   python app.py
   Open: http://127.0.0.1:5000
=============================================================================
"""
 
import os           # Voor bestandspadbewerkingen
import logging      # Voor het registreren van inlogpogingen en fouten
import sqlite3      # Ingebouwde database (dus geen installatie nodig)
from datetime import datetime  
 
# --- Import dependencies (pip install flask werkzeug) ---
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  # Voorkomt schadelijke bestandsnamen
import html  # Voor het escapen van uitvoer (XSS-beveiliging)
 
 
#  CONFIGURATION CONSTANTS
 
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'docx'}
 
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
 
DATABASE_PATH = os.path.join('instance', 'medifile.db')
 
UPLOAD_FOLDER = 'uploads'
 
 
#  CLASS: DatabaseManager
#  PURPOSE: Handles all interactions with the SQLite database.
#           This keeps database logic in one place (separation of concerns).
 
class DatabaseManager:
    """
    Manages all database operations for MediFile.
 
    SQLite is a file-based database built into Python - no server needed!
    We use parameterized queries everywhere to prevent SQL Injection attacks.
    """
 
    def __init__(self, db_path: str):
        """
        Constructor: stores the path to the database file.
        :param db_path: Path to the SQLite .db file
        """
        self.db_path = db_path
 
    def get_connection(self):
        """
        Opens and returns a connection to the SQLite database.
        'row_factory = sqlite3.Row' lets us access columns by name (like a dict).
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  
        return conn
 
    def initialize_database(self):
        """
        Creates all necessary tables if they don't already exist.
        Also seeds the database with example data for demo purposes.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,          -- Stored as a secure hash
                role     TEXT DEFAULT 'staff',   -- 'admin' or 'staff'
                created  TEXT NOT NULL
            )
        """)
 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                dob          TEXT NOT NULL,       -- Date of birth
                condition    TEXT NOT NULL,
                doctor       TEXT NOT NULL,
                ward         TEXT NOT NULL,
                status       TEXT DEFAULT 'Active',
                last_updated TEXT NOT NULL
            )
        """)
 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL,
                success    INTEGER NOT NULL,      -- 1 = success, 0 = failure
                ip_address TEXT,
                timestamp  TEXT NOT NULL
            )
        """)
 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL,
                patient_id  INTEGER,
                uploaded_by TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                file_size   INTEGER,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
 
        conn.commit()
 
        self._seed_default_data(conn, cursor)
 
        conn.close()
 
    def _seed_default_data(self, conn, cursor):
        """
        Private method: adds example data if the database is empty.
        The underscore prefix (_) is a Python convention for 'private' methods.
        """
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
 
            admin_hash = generate_password_hash("Admin@1234")
            staff_hash = generate_password_hash("Staff@5678")
 
            cursor.execute(
                "INSERT INTO users (username, password, role, created) VALUES (?, ?, ?, ?)",
                ("admin", admin_hash, "admin", datetime.now().isoformat())
            )
            cursor.execute(
                "INSERT INTO users (username, password, role, created) VALUES (?, ?, ?, ?)",
                ("nurse_jones", staff_hash, "staff", datetime.now().isoformat())
            )

            sample_patients = [
                ("Emma van der Berg",    "1982-03-15", "Hypertension",       "Dr. Kowalski",   "Ward A", "Active"),
                ("Lucas Hendriks",       "1995-07-22", "Type 2 Diabetes",    "Dr. Patel",      "Ward B", "Active"),
                ("Sophie de Vries",      "1940-11-05", "Cardiac Arrhythmia", "Dr. Okonkwo",   "ICU",    "Critical"),
                ("Maarten Bakker",       "1978-01-30", "Fractured Femur",    "Dr. Yamamoto",  "Ward C", "Stable"),
                ("Ingrid Smits",         "2001-09-12", "Appendicitis",       "Dr. Al-Hassan", "Ward A", "Recovering"),
                ("Dirk Vermeer",         "1965-06-08", "COPD",               "Dr. Kowalski",   "Ward D", "Active"),
                ("Anneliese Mulder",     "1990-12-20", "Migraine Disorder",  "Dr. Patel",      "Ward B", "Stable"),
                ("Pieter van Dijk",      "1958-04-17", "Kidney Disease",     "Dr. Okonkwo",   "Ward C", "Active"),
            ]
 
            now = datetime.now().strftime("%Y-%m-%d")
            for p in sample_patients:
                cursor.execute(
                    """INSERT INTO patients (name, dob, condition, doctor, ward, status, last_updated)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (*p, now)
                )
 
            conn.commit()
            print("[✓] Database seeded with sample data.")
 
    def get_user_by_username(self, username: str):
        """
        Fetches a user record by username. Returns None if not found.
        SECURITY: Uses parameterized query (?) to prevent SQL Injection.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return user
 
    def log_login_attempt(self, username: str, success: bool, ip: str):
        """
        Records every login attempt (both success and failure).
        This is important for detecting brute-force attacks.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO login_log (username, success, ip_address, timestamp) VALUES (?, ?, ?, ?)",
            (username, 1 if success else 0, ip, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
 
    def search_patients(self, query: str):
        """
        Searches patients by name or condition.
        Uses LIKE with % wildcards for partial matching.
        SECURITY: Parameterized query prevents SQL Injection.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        search_term = f"%{query}%"
        cursor.execute(
            """SELECT * FROM patients
               WHERE name LIKE ? OR condition LIKE ? OR doctor LIKE ? OR ward LIKE ?
               ORDER BY name ASC""",
            (search_term, search_term, search_term, search_term)
        )
        results = cursor.fetchall()
        conn.close()
        return results
 
    def get_all_patients(self):
        """Returns all patients ordered alphabetically."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients ORDER BY name ASC")
        patients = cursor.fetchall()
        conn.close()
        return patients
 
    def get_patient_by_id(self, patient_id: int):
        """Fetches a single patient by their ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        patient = cursor.fetchone()
        conn.close()
        return patient
 
    def get_dashboard_stats(self):
        """Returns summary statistics for the dashboard."""
        conn = self.get_connection()
        cursor = conn.cursor()
 
        cursor.execute("SELECT COUNT(*) FROM patients")
        total_patients = cursor.fetchone()[0]
 
        cursor.execute("SELECT COUNT(*) FROM patients WHERE status = 'Critical'")
        critical = cursor.fetchone()[0]
 
        cursor.execute("SELECT COUNT(*) FROM uploaded_files")
        total_files = cursor.fetchone()[0]
 
        cursor.execute("SELECT COUNT(*) FROM login_log WHERE success = 1")
        total_logins = cursor.fetchone()[0]
 
        conn.close()
        return {
            'total_patients': total_patients,
            'critical': critical,
            'total_files': total_files,
            'total_logins': total_logins,
        }
 
    def save_file_record(self, filename, patient_id, uploaded_by, file_size):
        """Saves a record of an uploaded file to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO uploaded_files (filename, patient_id, uploaded_by, upload_time, file_size)
               VALUES (?, ?, ?, ?, ?)""",
            (filename, patient_id, uploaded_by, datetime.now().isoformat(), file_size)
        )
        conn.commit()
        conn.close()
 
    def get_all_files(self):
        """Returns all uploaded file records."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.*, p.name as patient_name
            FROM uploaded_files f
            LEFT JOIN patients p ON f.patient_id = p.id
            ORDER BY f.upload_time DESC
        """)
        files = cursor.fetchall()
        conn.close()
        return files
 
 
# class: Gebruiker
# DOEL: geauthenticeerde gebruiker in de sessie.
# Verpakt eigenlijk de gebruikersgegevens voor gemakkelijke toegang in de applicatie.
 
class User:
    """
    Represents a logged-in MediFile user.
    Stores session info and provides helper methods.
    """
 
    def __init__(self, user_row):
        """
        Constructor: takes a database row and extracts user info.
        :param user_row: A sqlite3.Row object from the users table
        """
        self.id       = user_row['id']
        self.username = user_row['username']
        self.role     = user_row['role']     
 
    @property
    def is_admin(self) -> bool:
        """Returns True if this user has admin privileges."""
        return self.role == 'admin'
 
    def to_dict(self) -> dict:
        """Converts user info to a dictionary (useful for sessions)."""
        return {
            'id':       self.id,
            'username': self.username,
            'role':     self.role,
        }
 
 
# KLASSE: Patiënt
# DOEL: voegt een patiëntendossier toe.
# Biedt hulpmethoden voor weergaveopmaak.
 
class Patient:
    """
    Represents a patient in the MediFile system.
    Wraps a database row with useful helper methods.
    """
 
    STATUS_COLORS = {
        'Active':     'status-active',
        'Critical':   'status-critical',
        'Stable':     'status-stable',
        'Recovering': 'status-recovering',
    }
 
    def __init__(self, patient_row):
        """
        Constructor: extracts patient data from a database row.
        """
        self.id           = patient_row['id']
        self.name         = patient_row['name']
        self.dob          = patient_row['dob']
        self.condition    = patient_row['condition']
        self.doctor       = patient_row['doctor']
        self.ward         = patient_row['ward']
        self.status       = patient_row['status']
        self.last_updated = patient_row['last_updated']
 
    @property
    def age(self) -> int:
        """Calculates patient's age from date of birth."""
        try:
            born = datetime.strptime(self.dob, "%Y-%m-%d")
            today = datetime.today()
            return today.year - born.year - (
                (today.month, today.day) < (born.month, born.day)
            )
        except Exception:
            return 0
 
    @property
    def status_class(self) -> str:
        """Returns the CSS class for the status badge."""
        return self.STATUS_COLORS.get(self.status, 'status-active')
 
    def safe_name(self) -> str:
        """Returns HTML-escaped name to prevent XSS attacks."""
        return html.escape(self.name)
 
 
# KLASSE: FileUploadHandler
# DOEL: Verwerkt de logica voor het veilig uploaden van bestanden.
# Valideert bestandstypen en filtert bestandsnamen.
 
class FileUploadHandler:
    """
    Manages secure file uploads.
 
    SECURITY MEASURES:
    - Only allows specific file extensions
    - Sanitizes filenames using werkzeug's secure_filename()
    - Adds timestamp to prevent filename collisions
    """
 
    def __init__(self, upload_folder: str, allowed_extensions: set):
        """
        Constructor.
        :param upload_folder: Directory where files will be stored
        :param allowed_extensions: Set of allowed file extensions (e.g. {'pdf', 'jpg'})
        """
        self.upload_folder     = upload_folder
        self.allowed_extensions = allowed_extensions
 
        os.makedirs(upload_folder, exist_ok=True)
 
    def is_allowed(self, filename: str) -> bool:
        """
        Checks if a file extension is allowed.
        '.' in filename ensures there's an extension at all.
        """
        return (
            '.' in filename and
            filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
        )
 
    def save_file(self, file_object) -> tuple:
        """
        Validates and saves an uploaded file.
        Returns (success: bool, saved_filename: str, error_message: str)
 
        secure_filename() strips dangerous characters like '../' from filenames
        (prevents directory traversal attacks).
        """
        if not file_object or file_object.filename == '':
            return False, '', 'No file selected.'
 
        original_name = file_object.filename
 
        if not self.is_allowed(original_name):
            allowed = ', '.join(self.allowed_extensions)
            return False, '', f'File type not allowed. Allowed types: {allowed}'
 
        safe_name = secure_filename(original_name)
 
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_name = f"{timestamp}_{safe_name}"
 
        save_path = os.path.join(self.upload_folder, final_name)
 
        file_object.save(save_path)
 
        file_size = os.path.getsize(save_path)
 
        return True, final_name, file_size
 
 
# KLASSE: App
# DOEL: De hoofdapplicatieklasse. Stelt Flask in, registreert alle routes,
# en verbindt de andere klassen met elkaar.

class App:
    """
    The MediFile Flask application.
    This class initializes Flask and defines all URL routes (pages).
    """
 
    def __init__(self):
        """
        Constructor: sets up Flask app, config, database, and routes.
        """
        self.flask_app = Flask(__name__)
 
        self.flask_app.secret_key = 'medifile-super-secret-key-2025-change-in-prod'
 
        self.flask_app.config['UPLOAD_FOLDER']      = UPLOAD_FOLDER
        self.flask_app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
 
        os.makedirs('instance', exist_ok=True)
 
        self.db      = DatabaseManager(DATABASE_PATH)
        self.uploader = FileUploadHandler(UPLOAD_FOLDER, ALLOWED_EXTENSIONS)
 
        self.db.initialize_database()
 
        logging.basicConfig(
            filename='medifile.log',
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        self.logger = logging.getLogger(__name__)
 
        self._register_routes()
 
# Een decorator die routes beschermt, stuurt door naar de inlogpagina als er niet is ingelogd.
# Dit zorgt ervoor dat alleen geauthenticeerde gebruikers toegang hebben tot bepaalde pagina's (zoals dashboard, patiëntenlijst, uploadpagina). 
    def requires_login(self, f):
        """
        Decorator factory: wraps a route function to require authentication.
        Usage: @app.requires_login  above a route function.
        """
        from functools import wraps
 
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated
 
    #  Route registratie: hier worden alle URL routes gedefinieerd en gekoppeld aan functies.
 
    def _register_routes(self):
        """
        Registers all URL routes with the Flask app.
        Each route maps a URL to a Python function.
        """
        flask = self.flask_app  
 
 
        @flask.route('/')
        def index():
            """Homepage - public landing page."""
            return render_template('index.html')
 
        @flask.route('/contact')
        def contact():
            """Contact page."""
            return render_template('contact.html')
 
        @flask.route('/contact', methods=['POST'])
        def contact_post():
            """Handles contact form submission."""
            name    = html.escape(request.form.get('name', '').strip())
            email   = html.escape(request.form.get('email', '').strip())
            message = html.escape(request.form.get('message', '').strip())
 
            if not name or not email or not message:
                flash('Please fill in all fields.', 'error')
                return redirect(url_for('contact'))
 
            self.logger.info(f"Contact form submission from: {email}")
            flash('Message received! We will get back to you shortly.', 'success')
            return redirect(url_for('contact'))
 
        @flask.route('/conduct')
        def conduct():
            """Code of Conduct page."""
            return render_template('conduct.html')
 
        @flask.route('/orgchart')
        def orgchart():
            """Organisation Chart page."""
            return render_template('orgchart.html')
 
 
        @flask.route('/login', methods=['GET', 'POST'])
        def login():
            """
            GET:  Shows the login form.
            POST: Processes the login form.
            """
            if 'user' in session:
                return redirect(url_for('dashboard'))
 
            if request.method == 'POST':
                username = request.form.get('username', '').strip()
                password = request.form.get('password', '')
                ip       = request.remote_addr
 
                if not username or not password:
                    flash('Username and password are required.', 'error')
                    return render_template('login.html')
 
                user_row = self.db.get_user_by_username(username)
 
                if user_row and check_password_hash(user_row['password'], password):
                    user = User(user_row)
                    session['user'] = user.to_dict()
 
                    self.db.log_login_attempt(username, True, ip)
                    self.logger.info(f"SUCCESSFUL LOGIN: {username} from {ip}")
 
                    flash(f'Welcome back, {username}!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    self.db.log_login_attempt(username, False, ip)
                    self.logger.warning(f"FAILED LOGIN: {username} from {ip}")
                    flash('Invalid username or password.', 'error')
 
            return render_template('login.html')
 
        @flask.route('/logout')
        def logout():
            """Clears the session and redirects to login."""
            username = session.get('user', {}).get('username', 'Unknown')
            session.clear()
            self.logger.info(f"LOGOUT: {username}")
            flash('You have been logged out securely.', 'info')
            return redirect(url_for('login'))
 
 
        @flask.route('/dashboard')
        @self.requires_login
        def dashboard():
            """Main dashboard with statistics cards."""
            stats = self.db.get_dashboard_stats()
            return render_template('dashboard.html',
                                   stats=stats,
                                   user=session['user'])
 
        @flask.route('/patients')
        @self.requires_login
        def patients():
            """Patient list page with optional search."""
            query = request.args.get('q', '').strip()
 
            if query:
                raw_patients = self.db.search_patients(query)
            else:
                raw_patients = self.db.get_all_patients()
 
            patient_objects = [Patient(p) for p in raw_patients]
 
            return render_template('patients.html',
                                   patients=patient_objects,
                                   query=query,
                                   user=session['user'])
 
        @flask.route('/patients/<int:patient_id>')
        @self.requires_login
        def patient_detail(patient_id):
            """Shows detailed record for one patient."""
            raw = self.db.get_patient_by_id(patient_id)
            if not raw:
                abort(404)
            patient = Patient(raw)
            return render_template('patient_detail.html',
                                   patient=patient,
                                   user=session['user'])
 
        @flask.route('/upload', methods=['GET', 'POST'])
        @self.requires_login
        def upload():
            """File upload page."""
            all_patients = self.db.get_all_patients()
 
            if request.method == 'POST':
                file       = request.files.get('file')
                patient_id = request.form.get('patient_id')
                uploader_name = session['user']['username']
 
                success, result, extra = self.uploader.save_file(file)
 
                if success:
                    self.db.save_file_record(result, patient_id, uploader_name, extra)
                    self.logger.info(f"FILE UPLOAD: {result} by {uploader_name}")
                    flash(f'File "{result}" uploaded successfully!', 'success')
                else:
                    flash(extra, 'error')
 
                return redirect(url_for('upload'))
 
            files = self.db.get_all_files()
            return render_template('upload.html',
                                   patients=all_patients,
                                   files=files,
                                   user=session['user'])
 
 
        @flask.errorhandler(404)
        def not_found(e):
            return render_template('404.html'), 404
 
        @flask.errorhandler(413)
        def file_too_large(e):
            flash('File is too large. Maximum size is 16 MB.', 'error')
            return redirect(url_for('upload'))
 
    def run(self, **kwargs):
        """Starts the Flask development server."""
        self.flask_app.run(**kwargs)
 
 

#Het programma wordt NIET uitgevoerd wanneer het bestand als module wordt geïmporteerd. 

if __name__ == '__main__':
    print("=" * 60)
    print("  MediFile - Secure Medical File Management System")
    print("=" * 60)
    print("  Starting server...")
    print("  Open your browser and go to: http://127.0.0.1:5000")
    print()
    print("  DEFAULT LOGIN CREDENTIALS:")
    print("    Admin  → username: admin       | password: Admin@1234")
    print("    Staff  → username: nurse_jones | password: Staff@5678")
    print()
    print("  Press CTRL+C to stop the server.")
    print("=" * 60)
 
    medifile_app = App()
    medifile_app.run(debug=True, host='127.0.0.1', port=5000)
 
