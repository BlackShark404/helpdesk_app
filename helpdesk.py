import bcrypt
import psycopg2
from flask import Flask, request, render_template, session, redirect, url_for
from functools import wraps

app = Flask(__name__)
app.secret_key = 'super-secret-key-for-lab' 

DB_CONFIG = {
    "host": "localhost",
    "database": "helpdesk_dump",
    "user": "postgres",
    "password": "18271504",  
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.OperationalError as e:
        print("Error: Unable to connect to the database. Check your credentials.")
        print(e)
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def support_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'support_role':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET'])
def index():
    if 'logged_in' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('role') == 'support_role':
            return redirect(url_for('support_dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')

    conn = get_db_connection()
    if not conn:
        return render_template('login.html', login_message="Database connection failed.")

    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, role, password FROM public.staff_users WHERE username = %s;", (username,))
        user = cur.fetchone()

        if not user:
            cur.close()
            return render_template('login.html', login_message="Invalid username or password.")

        uid, uname, role, stored_value = user

        # Check if password already hashed
        if stored_value and stored_value.startswith("$2b$"):
            if bcrypt.checkpw(password.encode('utf-8'), stored_value.encode('utf-8')):
                session['logged_in'] = True
                session['username'] = uname
                session['role'] = role
                cur.close()
                if role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('support_dashboard'))
            else:
                cur.close()
                return render_template('login.html', login_message="Invalid username or password.")
        else:
            # Plaintext in DB → hash and update automatically
            new_hash = bcrypt.hashpw(stored_value.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
            cur.execute("UPDATE public.staff_users SET password = %s WHERE id = %s;", (new_hash, uid))
            conn.commit()
            if bcrypt.checkpw(password.encode('utf-8'), new_hash.encode('utf-8')):
                session['logged_in'] = True
                session['username'] = uname
                session['role'] = role
                cur.close()
                if role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('support_dashboard'))
            else:
                cur.close()
                return render_template('login.html', login_message="Invalid username or password.")
    except Exception as e:
        print("Login error:", e)
        return render_template('login.html', login_message="An error occurred during login.")
    finally:
        if conn:
            conn.close()

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/submit_ticket', methods=['POST'])
def submit_ticket():
    student_id = request.form.get('student_id', '')
    issue = request.form.get('issue', '')

    conn = get_db_connection()
    if not conn:
        return render_template('login.html', ticket_message="Database connection failed.")
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO public.tickets (student_id, issue) VALUES (%s, %s);", (int(student_id), issue))
        conn.commit()
        cur.close()
        return render_template('login.html', ticket_message="Ticket submitted successfully!")
    except Exception as e:
        print("Ticket submission error:", e)
        return render_template('login.html', ticket_message="An error occurred.")
    finally:
        if conn:
            conn.close()

# Admin Routes
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    stats = {
        'total_students': 0,
        'total_tickets': 0,
        'total_staff': 0,
        'last_ticket': None
    }
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM public.students;")
            stats['total_students'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM public.tickets;")
            stats['total_tickets'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM public.staff_users;")
            stats['total_staff'] = cur.fetchone()[0]
            
            cur.execute("SELECT created_at FROM public.tickets ORDER BY created_at DESC LIMIT 1;")
            result = cur.fetchone()
            if result:
                stats['last_ticket'] = result[0].strftime('%Y-%m-%d %H:%M')
            
            cur.close()
        except Exception as e:
            print("Dashboard error:", e)
        finally:
            conn.close()
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/tickets')
@admin_required
def admin_tickets():
    conn = get_db_connection()
    tickets = []
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT t.id, s.name, t.issue, t.status, t.created_at 
                FROM public.tickets t
                JOIN public.students s ON t.student_id = s.id
                ORDER BY t.created_at DESC;
            """)
            tickets = cur.fetchall()
            cur.close()
        except Exception as e:
            print("Tickets fetch error:", e)
        finally:
            conn.close()
    
    return render_template('admin/tickets.html', tickets=tickets)

@app.route('/admin/tickets/delete/<int:ticket_id>', methods=['POST'])
@admin_required
def delete_ticket(ticket_id):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM public.tickets WHERE id = %s;", (ticket_id,))
            conn.commit()
            cur.close()
        except Exception as e:
            print("Delete ticket error:", e)
        finally:
            conn.close()
    
    return redirect(url_for('admin_tickets'))

@app.route('/admin/tickets/resolve/<int:ticket_id>', methods=['POST'])
@admin_required
def resolve_ticket(ticket_id):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("UPDATE public.tickets SET status = 'resolved' WHERE id = %s;", (ticket_id,))
            conn.commit()
            cur.close()
        except Exception as e:
            print("Resolve ticket error:", e)
        finally:
            conn.close()
    
    return redirect(url_for('admin_tickets'))

@app.route('/admin/students')
@admin_required
def admin_students():
    conn = get_db_connection()
    students = []
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name, email, phone FROM public.students ORDER BY name;")
            students = cur.fetchall()
            cur.close()
        except Exception as e:
            print("Students fetch error:", e)
        finally:
            conn.close()
    
    return render_template('admin/students.html', students=students)

@app.route('/admin/staff')
@admin_required
def admin_staff():
    conn = get_db_connection()
    staff = []
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, username, role FROM public.staff_users ORDER BY id;")
            staff = cur.fetchall()
            cur.close()
        except Exception as e:
            print("Staff fetch error:", e)
        finally:
            conn.close()
    
    return render_template('admin/staff.html', staff=staff)

@app.route('/admin/audit')
@admin_required
def admin_audit():
    conn = get_db_connection()
    logs = []
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, action, student_id, old_issue, new_issue, changed_at 
                FROM public.audit_log 
                ORDER BY changed_at DESC;
            """)
            logs = cur.fetchall()
            cur.close()
        except Exception as e:
            print("Audit logs fetch error:", e)
        finally:
            conn.close()
    
    return render_template('admin/audit.html', logs=logs)

# Support Routes
@app.route('/support/dashboard')
@support_required
def support_dashboard():
    conn = get_db_connection()
    stats = {
        'open_tickets': 0,
        'resolved_tickets': 0,
        'total_students': 0
    }
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM public.tickets;")
            stats['open_tickets'] = cur.fetchone()[0]
            
            stats['resolved_tickets'] = 0  # Placeholder
            
            cur.execute("SELECT COUNT(*) FROM public.students;")
            stats['total_students'] = cur.fetchone()[0]
            
            cur.close()
        except Exception as e:
            print("Dashboard error:", e)
        finally:
            conn.close()
    
    return render_template('support/dashboard.html', stats=stats)

@app.route('/support/tickets')
@support_required
def support_tickets():
    conn = get_db_connection()
    tickets = []
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT t.id, s.name, t.issue, t.status, t.created_at 
                FROM public.tickets t
                JOIN public.students s ON t.student_id = s.id
                ORDER BY t.created_at DESC;
            """)
            tickets = cur.fetchall()
            cur.close()
        except Exception as e:
            print("Tickets fetch error:", e)
        finally:
            conn.close()
    
    return render_template('support/tickets.html', tickets=tickets)

@app.route('/support/students')
@support_required
def support_students():
    conn = get_db_connection()
    students = []
    
    if conn:
        try:
            cur = conn.cursor()
            # Use the restricted view for support users
            cur.execute("SELECT id, name, email, phone FROM public.students_support_view ORDER BY name;")
            students = cur.fetchall()
            cur.close()
        except Exception as e:
            print("Students fetch error:", e)
        finally:
            conn.close()
    
    return render_template('support/students.html', students=students)

@app.route('/support/audit')
@support_required
def support_audit():
    conn = get_db_connection()
    logs = []
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, action, student_id, old_issue, new_issue, changed_at 
                FROM public.audit_log 
                ORDER BY changed_at DESC;
            """)
            logs = cur.fetchall()
            cur.close()
        except Exception as e:
            print("Audit logs fetch error:", e)
        finally:
            conn.close()
    
    return render_template('support/audit.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True)
