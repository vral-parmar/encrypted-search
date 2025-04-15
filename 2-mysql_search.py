from flask import Flask, request, render_template_string, jsonify
from cryptography.fernet import Fernet
from rapidfuzz import fuzz
import mysql.connector
import os
import time

app = Flask(__name__)
KEY_FILE = "secret.key"

# 🔐 Load encryption key
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as f:
        f.write(Fernet.generate_key())
with open(KEY_FILE, "rb") as f:
    KEY = f.read()
cipher = Fernet(KEY)

# ✅ MySQL config
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",       # replace with your MySQL password
    "database": "smart_search"
}

def encrypt(txt): return cipher.encrypt(txt.encode()).decode()
def decrypt(token): return cipher.decrypt(token.encode()).decode()

def generate_tokens(name):
    name = name.lower()
    tokens = set()
    for i in range(len(name)):
        for j in range(i+2, len(name)+1):
            tokens.add(name[i:j])
    return list(tokens)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# -------------------- ROUTES --------------------

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html><html><head>
<title>🔐 Encrypted Fuzzy Search</title>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 text-gray-800 font-sans p-8">

<div class="max-w-2xl mx-auto bg-white p-6 rounded shadow">
<h2 class="text-2xl font-bold mb-4">➕ Add Person</h2>
<input id="first" placeholder="First Name" class="border p-2 w-full mb-2 rounded">
<input id="last" placeholder="Last Name" class="border p-2 w-full mb-2 rounded">
<button onclick="savePerson()" class="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
<p id="alert" class="text-green-600 mt-2 hidden"></p>
</div>

<div class="max-w-2xl mx-auto bg-white p-6 mt-6 rounded shadow">
<h2 class="text-2xl font-bold mb-4">🔍 Search</h2>
<input id="search" class="border p-2 w-full mb-4 rounded" onkeyup="searchName()" placeholder="Type to search...">
<div id="results"></div>
</div>

<script>
function savePerson() {
    const first = $('#first').val(), last = $('#last').val();
    if (!first || !last) return;
    $.ajax({
        url: "/add",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({ first, last }),
        success: function(res) {
            $('#alert').text(res).removeClass('hidden');
            setTimeout(() => $('#alert').addClass('hidden'), 3000);
            $('#first').val('');
            $('#last').val('');
        },
        error: function(xhr) {
            alert("❌ Save failed: " + xhr.responseText);
        }
    });
}

function searchName() {
    const q = $('#search').val();
    if (q.length < 2) { $('#results').html(''); return; }
    $.get('/search?q=' + encodeURIComponent(q), function(data) {
        if (data.length === 0) {
            $('#results').html('<p class="text-red-500">No match found.</p>');
        } else {
            let html = '<ul>';
            data.forEach(p => {
                html += `<li class="p-2 bg-gray-100 rounded my-1">${p.first} ${p.last}</li>`;
            });
            html += '</ul>';
            $('#results').html(html);
        }
    });
}
</script>

</body></html>
''')

@app.route('/add', methods=['POST'])
def add_person():
    data = request.get_json(force=True)
    first, last = data['first'], data['last']
    conn = get_db()
    cur = conn.cursor()

    first_enc = encrypt(first)
    last_enc = encrypt(last)

    cur.execute("INSERT INTO people (first_enc, last_enc) VALUES (%s, %s)", (first_enc, last_enc))
    person_id = cur.lastrowid

    tokens = generate_tokens(first) + generate_tokens(last)
    cur.executemany("INSERT INTO tokens (person_id, token) VALUES (%s, %s)", [(person_id, t) for t in tokens])
    conn.commit()
    cur.close()
    conn.close()
    return "✅ Person saved."

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    if not query or len(query) < 2:
        return jsonify([])

    try:
        conn = get_db()
        cur = conn.cursor()

        # Step 1: Partial SQL filter first
        cur.execute("SELECT DISTINCT token, person_id FROM tokens WHERE token LIKE %s LIMIT 2000", (f"%{query}%",))
        token_map = cur.fetchall()
        cur.close()
        conn.close()

        # Step 2: Apply fuzzy match on filtered set
        matched_ids = set()
        for token, pid in token_map:
            if token and fuzz.ratio(query, token) >= 75:
                matched_ids.add(pid)

        if not matched_ids:
            return jsonify([])

        # Step 3: Fetch and decrypt only matched IDs
        conn = get_db()
        cur = conn.cursor()
        placeholders = ",".join(["%s"] * len(matched_ids))
        cur.execute(f"SELECT first_enc, last_enc FROM people WHERE id IN ({placeholders})", tuple(matched_ids))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = [{"first": decrypt(f), "last": decrypt(l)} for f, l in rows]
        return jsonify(results)

    except Exception as e:
        print(f"❌ Search error: {e}")
        return jsonify([])



@app.route('/benchmark')
def benchmark():
    q = request.args.get("q", "ramesh").lower()
    t0 = time.time()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT token, person_id FROM tokens ")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    matched_ids = {pid for token, pid in rows if fuzz.ratio(q, token) >= 75}

    conn = get_db()
    cur = conn.cursor()
    if matched_ids:
        placeholders = ",".join(["%s"] * len(matched_ids))
        cur.execute(f"SELECT COUNT(*) FROM people WHERE id IN ({placeholders})", tuple(matched_ids))
    else:
        cur.execute("SELECT 0")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()

    elapsed = time.time() - t0
    return f"🔍 Searched '{q}' in {elapsed:.2f} sec — {count} match(es)"

# ------------- MAIN -------------
if __name__ == '__main__':
    app.run(debug=True)
