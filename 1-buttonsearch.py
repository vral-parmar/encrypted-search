from flask import Flask, request, render_template_string, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
from cryptography.fernet import Fernet
from rapidfuzz import fuzz
import mysql.connector
import os
import time

#perfectly working fine with loader and 70/80 precent accurancy.

app = Flask(__name__)

# === Config ===
KEY_FILE = "secret.key"
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Replace with your MySQL password
    "database": "smart_search"
}

# === Load encryption key ===
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as f:
        f.write(Fernet.generate_key())
with open(KEY_FILE, "rb") as f:
    KEY = f.read()
cipher = Fernet(KEY)

def encrypt(text): return cipher.encrypt(text.encode()).decode()
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

# === Routes ===

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html><html><head>
  <title>🔐 Encrypted Fuzzy Search</title>
  <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 text-gray-800 p-8 font-sans">

<div class="max-w-xl mx-auto bg-white p-6 rounded shadow">
  <h2 class="text-2xl font-bold mb-4">➕ Add Person</h2>
  <input id="first" placeholder="First Name" class="border p-2 w-full mb-2 rounded">
  <input id="last" placeholder="Last Name" class="border p-2 w-full mb-2 rounded">
  <button id="saveBtn" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition">Save</button>
  <p id="alert" class="text-green-600 mt-2 hidden"></p>
</div>

<div class="max-w-xl mx-auto bg-white p-6 mt-6 rounded shadow">
  <h2 class="text-2xl font-bold mb-4">🔍 Search Person</h2>
  <div class="flex gap-2 items-center">
  <input id="search" class="border p-2 rounded w-full" placeholder="Enter name or typo...">
  <button id="searchBtn" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition">Search</button>
  <div id="loader" class="hidden animate-spin ml-2 border-4 border-t-green-600 border-gray-200 rounded-full w-6 h-6"></div>
</div>

  <div id="results" class="mt-4"></div>
</div>

<script>
$(document).ready(function () {
  $('#saveBtn').click(function () {
    const first = $('#first').val(), last = $('#last').val();
    if (!first || !last) return;

    $.ajax({
      url: "/add",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify({ first, last }),
      success: function (res) {
        $('#alert').text(res).removeClass('hidden');
        setTimeout(() => $('#alert').addClass('hidden'), 3000);
        $('#first').val('');
        $('#last').val('');
      },
      error: function (xhr) {
        alert("❌ Save failed: " + xhr.responseText);
      }
    });
  });

  $('#searchBtn').click(function () {
  const q = $('#search').val();
  if (q.length < 2) {
    $('#results').html('<p class="text-red-500">Enter at least 2 characters.</p>');
    return;
  }

  $('#loader').removeClass('hidden');
  $('#results').html('');

  $.get('/search?q=' + encodeURIComponent(q), function (data) {
    $('#loader').addClass('hidden');
    if (data.length === 0) {
      $('#results').html('<p class="text-red-500">No match found.</p>');
    } else {
      let html = '<ul>';
      data.forEach(p => {
        html += `<li class="p-2 bg-gray-100 rounded my-1">${p.first} ${p.last} <span class="text-sm text-gray-500">(Score: ${p.score})</span></li>`;
      });
      html += '</ul>';
      $('#results').html(html);
    }
  }).fail(() => {
    $('#loader').addClass('hidden');
    $('#results').html('<p class="text-red-500">Search failed.</p>');
  });
});

});
</script>
</body></html>
''')

@app.route('/add', methods=['POST'])
def add_person():
    data = request.get_json(force=True)
    first, last = data.get('first'), data.get('last')
    if not first or not last:
        return "Missing name", 400

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

from concurrent.futures import ThreadPoolExecutor, as_completed

from concurrent.futures import ThreadPoolExecutor, as_completed

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    if not query or len(query) < 2:
        return jsonify([])

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT token, person_id FROM tokens WHERE token LIKE %s LIMIT 10000", (f"%{query}%",))
        token_map = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        print("❌ Error fetching tokens:", e)
        return jsonify([])

    # === Threaded Fuzzy Match with Score ===
    scores = {}

    def match_token(record):
        token, pid = record
        try:
            score = fuzz.ratio(query, token)
            if score >= 75:
                return (pid, score)
        except:
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(match_token, rec) for rec in token_map]
        for future in as_completed(futures):
            result = future.result()
            if result:
                pid, score = result
                if pid not in scores or score > scores[pid]:
                    scores[pid] = score  # Keep best score

    if not scores:
        return jsonify([])

    try:
        conn = get_db()
        cur = conn.cursor()
        placeholders = ",".join(["%s"] * len(scores))
        cur.execute(f"SELECT id, first_enc, last_enc FROM people WHERE id IN ({placeholders})", tuple(scores.keys()))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = []
        for pid, first_enc, last_enc in rows:
            results.append({
                "first": decrypt(first_enc),
                "last": decrypt(last_enc),
                "score": scores[pid]
            })

        results.sort(key=lambda x: -x['score'])  # 🔥 Sort by best match
        return jsonify(results)

    except Exception as e:
        print("❌ Error fetching matches:", e)
        return jsonify([])



# === MAIN ===
if __name__ == '__main__':
    app.run(debug=True, port=5001)
