from flask import Flask, request, render_template_string, jsonify
from cryptography.fernet import Fernet
from rapidfuzz import fuzz
import mysql.connector
import os
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
KEY_FILE = "secret.key"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # 🔁 Set your MySQL password
    "database": "searchjson"
}

# === Encryption Setup ===
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as f:
        f.write(Fernet.generate_key())
with open(KEY_FILE, "rb") as f:
    KEY = f.read()
cipher = Fernet(KEY)

def encrypt(txt): return cipher.encrypt(txt.encode()).decode()
def decrypt(txt): return cipher.decrypt(txt.encode()).decode()

# === Token Generator (min 3 letters)
def generate_tokens(name):
    name = name.lower()
    tokens = set()
    for i in range(len(name)):
        for j in range(i+3, len(name)+1):
            tokens.add(name[i:j])
    return list(tokens)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# === Routes ===

@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html><html><head>
<title>🔍 Fuzzy Encrypted Search</title>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 text-gray-800 p-8">
<div class="max-w-xl mx-auto bg-white p-6 rounded shadow">
  <h2 class="text-2xl font-bold mb-4">➕ Add Name</h2>
  <input id="first" placeholder="First Name" class="border p-2 w-full mb-2 rounded">
  <input id="last" placeholder="Last Name" class="border p-2 w-full mb-2 rounded">
  <button id="saveBtn" class="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
  <p id="alert" class="text-green-600 mt-2 hidden"></p>
</div>

<div class="max-w-xl mx-auto bg-white p-6 mt-6 rounded shadow">
  <h2 class="text-2xl font-bold mb-4">🔍 Search</h2>
  <div class="flex gap-2 items-center">
    <input id="search" class="border p-2 rounded w-full" placeholder="Enter name...">
    <button id="searchBtn" class="bg-green-600 text-white px-4 py-2 rounded">Search</button>
    <div id="loader" class="hidden animate-spin border-4 border-t-green-600 border-gray-200 rounded-full w-6 h-6"></div>
  </div>
  <div id="results" class="mt-4"></div>
</div>

<script>
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
      $('#first').val(''); $('#last').val('');
    }
  });
});

$('#searchBtn').click(function () {
  const q = $('#search').val();
  if (q.length < 3) return $('#results').html('<p class="text-red-500">Enter at least 3 characters.</p>');
  $('#loader').removeClass('hidden'); $('#results').html('');
  $.get('/search?q=' + encodeURIComponent(q), function (data) {
    $('#loader').addClass('hidden');
    if (!data.length) return $('#results').html('<p class="text-red-500">No match found.</p>');
    let html = '<ul>';
    data.forEach(p => {
      html += `<li class="p-2 bg-gray-100 my-1 rounded">${p.first} ${p.last} <span class="text-sm text-gray-500">(Score: ${p.score})</span></li>`;
    });
    html += '</ul>';
    $('#results').html(html);
  });
});
</script>
</body></html>
''')

# === Add Name Endpoint
@app.route('/add', methods=['POST'])
def add_person():
    data = request.get_json(force=True)
    first, last = data.get('first'), data.get('last')
    if not first or not last:
        return "Missing name", 400

    conn = get_db()
    cur = conn.cursor()
    f_enc, l_enc = encrypt(first), encrypt(last)
    tokens = generate_tokens(first) + generate_tokens(last)
    tokens_json = json.dumps(tokens)

    cur.execute("""
        INSERT INTO names (first_enc, last_enc, tokens_json)
        VALUES (%s, %s, %s)
    """, (f_enc, l_enc, tokens_json))
    conn.commit()
    cur.close(); conn.close()
    return "✅ Name saved."

@app.route('/search')
def search():
    query = request.args.get('q', '').lower().strip()
    if not query or len(query) < 3:
        return jsonify([])

    max_results = 20
    max_threads = 6
    scores = {}

    try:
        # Step 1: Pre-filter by JSON_CONTAINS
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, first_enc, last_enc, tokens_json
            FROM names
            WHERE JSON_CONTAINS(tokens_json, JSON_QUOTE(%s))
            LIMIT 10
        """, (query,))
        rows = cur.fetchall()
        cur.close(); conn.close()

        if not rows:
            return jsonify([])

        # Step 2: Fuzzy match via RapidFuzz
        def match_row(row):
            pid, f_enc, l_enc, token_str = row
            try:
                tokens = json.loads(token_str)
                best = max([fuzz.ratio(query, t) for t in tokens], default=0)
                return (pid, f_enc, l_enc, best) if best >= 75 else None
            except:
                return None

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(match_row, row) for row in rows]
            for f in as_completed(futures):
                res = f.result()
                if res:
                    pid, f_enc, l_enc, score = res
                    if pid not in scores or score > scores[pid]:
                        scores[pid] = (f_enc, l_enc, score)

    except Exception as e:
        print("❌ Search error:", e)
        return jsonify([])

    # Step 3: Decrypt and sort
    try:
        results = []
        for pid, (f_enc, l_enc, score) in scores.items():
            results.append({
                "first": decrypt(f_enc),
                "last": decrypt(l_enc),
                "score": score
            })
        return jsonify(sorted(results, key=lambda x: -x['score'])[:max_results])
    except Exception as e:
        print("❌ Decrypt error:", e)
        return jsonify([])



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0",port=80)