
import bcrypt  # ADDED: for secure password hashing
import psycopg2
from flask import Flask, request, render_template_string, session  # REMOVED: redirect/url_for (unused)

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

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>University Helpdesk</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
  <script src="{{ url_for('static', filename='js/password_toggle.js') }}"></script>
</head>
<body class="bg-gray-50 font-sans text-gray-800">
  <div class="max-w-5xl mx-auto p-6">
    <!-- Header -->
    <header class="mb-10 text-center">
      <h1 class="text-4xl font-bold text-gray-900">CCICT Helpdesk</h1>
      <p class="text-gray-600 mt-2">DBMS Security Lab</p>
    </header>

    <div class="grid md:grid-cols-2 gap-6">
      <!-- Login Form -->
      <div class="bg-white rounded-2xl shadow-md p-6 hover:shadow-lg transition">
        <h2 class="text-xl font-semibold mb-4">Login</h2>
        <form action="/login" method="post" class="space-y-4">
          <input type="text" name="username" placeholder="Username" required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none">
          <div class="relative">
            <input type="password" id="password" name="password" placeholder="Password" required
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none">
            <button type="button" id="togglePassword" class="absolute inset-y-0 right-0 pr-3 flex items-center">
              <i class="fas fa-eye text-gray-500 hover:text-gray-700"></i>
            </button>
          </div>
          <button type="submit"
            class="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg hover:bg-blue-700 transition">
            Log In
          </button>
          {% if login_message %}
            <p class="text-red-500 text-sm text-center mt-2">{{ login_message }}</p>
          {% endif %}
        </form>
      </div>

      <!-- New Ticket Form -->
      <div class="bg-white rounded-2xl shadow-md p-6 hover:shadow-lg transition">
        <h2 class="text-xl font-semibold mb-4">Create Ticket</h2>
        <form action="/submit_ticket" method="post" class="space-y-4">
          <input type="text" name="student_id" placeholder="Student ID" required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:outline-none">
          <textarea name="issue" placeholder="Describe your issue..." rows="4" required
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:outline-none"></textarea>
          <button type="submit"
            class="w-full bg-green-600 text-white font-medium py-2 px-4 rounded-lg hover:bg-green-700 transition">
            Submit Ticket
          </button>
          {% if ticket_message %}
            <p class="text-green-600 text-sm text-center mt-2">{{ ticket_message }}</p>
          {% endif %}
        </form>
      </div>
    </div>

    <!-- Ticket Search -->
    <div class="bg-white rounded-2xl shadow-md p-6 mt-8 hover:shadow-lg transition">
      <h2 class="text-xl font-semibold mb-4">Search Tickets</h2>
      <form action="/search" method="get" class="flex flex-col md:flex-row gap-3">
        <input type="text" name="q" placeholder="Search for an issue..." required
          class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:outline-none">
        <button type="submit"
          class="bg-yellow-500 text-white font-medium py-2 px-6 rounded-lg hover:bg-yellow-600 transition">
          Search
        </button>
      </form>

      <!-- Search Results -->
      <div class="mt-6">
        {% if results is not none %}
          <h3 class="text-lg font-semibold mb-2">Results</h3>
          {% if results %}
            <ul class="space-y-2">
              {% for ticket in results %}
                <li class="p-3 bg-gray-50 rounded-lg border text-sm">
                  <span class="font-medium text-gray-900">Ticket #{{ ticket[0] }}</span>: {{ ticket[1] }}
                </li>
              {% endfor %}
            </ul>
          {% else %}
            <p class="text-gray-500 text-sm">No tickets found.</p>
          {% endif %}
        {% endif %}
      </div>
    </div>
  </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(html_template)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')

    conn = get_db_connection()
    if not conn:
        return render_template_string(html_template, login_message="Database connection failed.")

    try:
        cur = conn.cursor()
        # SECURE: parameterized query prevents SQL injection
        cur.execute("SELECT id, username, role, password FROM public.staff_users WHERE username = %s AND password = %s;", (username, password))
        user = cur.fetchone()

        if not user:
            cur.close()
            return render_template_string(html_template, login_message="Invalid username or password.")

        uid, uname, role, stored_value = user

        # ADDED: check if password already hashed
        if stored_value and stored_value.startswith("$2b$"):
            # Already hashed, just check
            if bcrypt.checkpw(password.encode('utf-8'), stored_value.encode('utf-8')):
                session['logged_in'] = True
                session['username'] = uname
                session['role'] = role
                msg = f"Login successful as {uname}!"
                cur.close()
                return render_template_string(html_template, login_message=msg)
            else:
                cur.close()
                return render_template_string(html_template, login_message="Invalid username or password.")
        else:
            # Plaintext in DB → hash and update automatically
            new_hash = bcrypt.hashpw(stored_value.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
            cur.execute("UPDATE public.staff_users SET password = %s WHERE id = %s;", (new_hash, uid))
            conn.commit()
            # Check login now
            if bcrypt.checkpw(password.encode('utf-8'), new_hash.encode('utf-8')):
                session['logged_in'] = True
                session['username'] = uname
                session['role'] = role
                msg = f"Login successful as {uname}! (password just migrated)"
                cur.close()
                return render_template_string(html_template, login_message=msg)
            else:
                cur.close()
                return render_template_string(html_template, login_message="Invalid username or password.")
    except Exception as e:
        print("Login error:", e)
        return render_template_string(html_template, login_message="An error occurred during login.")
    finally:
        if conn:
            conn.close()

@app.route('/submit_ticket', methods=['POST'])
def submit_ticket():
    # unchanged logic but parameterized query added
    student_id = request.form.get('student_id', '')
    issue = request.form.get('issue', '')

    conn = get_db_connection()
    if not conn:
        return render_template_string(html_template, ticket_message="Database connection failed.")
    try:
        cur = conn.cursor()
        # SECURE: parameterized insert
        cur.execute("INSERT INTO public.tickets (student_id, issue) VALUES (%s, %s);", (int(student_id), issue))
        conn.commit()
        cur.close()
        return render_template_string(html_template, ticket_message="Ticket submitted successfully!")
    except Exception as e:
        print("Ticket submission error:", e)
        return render_template_string(html_template, ticket_message="An error occurred.")
    finally:
        if conn:
            conn.close()

def find_secure_tickets(query_string):
    # SECURE SEARCH: Using stored procedure for ticket search
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        like_pattern = f"%{query_string}%"
        cur.execute("SELECT id, issue FROM public.tickets WHERE issue ILIKE %s;", (like_pattern,))
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        print("Search error:", e)
        return []
    finally:
        if conn:
            conn.close()

@app.route('/search', methods=['GET'])
def search_tickets():
    # CHANGED: use secure tickets search
    q = request.args.get('q', '')
    results = find_secure_tickets(q) if q else []
    return render_template_string(html_template, results=results)

if __name__ == '__main__':
    app.run(debug=True)
