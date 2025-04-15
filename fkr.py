# # from faker import Faker
# # from cryptography.fernet import Fernet
# # import sqlite3
# # from tqdm import tqdm
# # import os

# # DB = "benchmark_fuzzy.db"
# # COUNT = 50000  # 🔁 Set to 1M for now. 10B would take forever.

# # with open("secret.key", "rb") as f:
# #     key = f.read()
# # cipher = Fernet(key)
# # fake = Faker()

# # def encrypt(text):
# #     return cipher.encrypt(text.encode()).decode()

# # def init_db():
# #     with sqlite3.connect(DB) as conn:
# #         c = conn.cursor()
# #         c.execute("DROP TABLE IF EXISTS people")
# #         c.execute("CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, first TEXT, last TEXT)")
# #         conn.commit()

# # def insert_data():
# #     with sqlite3.connect(DB) as conn:
# #         c = conn.cursor()
# #         for _ in tqdm(range(COUNT), desc="Inserting"):
# #             fl_name = fake.last_name()
# #             ff_name = fake.first_name()
# #             print(fl_name, ff_name)
# #             first = encrypt(ff_name)
# #             last = encrypt(fl_name)
# #             c.execute("INSERT INTO people (first, last) VALUES (?, ?)", (first, last))
# #         conn.commit()

# # if __name__ == '__main__':
# #     init_db()
# #     insert_data()


# from faker import Faker
# from cryptography.fernet import Fernet
# import sqlite3, os, time
# from tqdm import tqdm

# DB = "smart_search.db"
# KEY_FILE = "secret.key"

# # Load key
# with open(KEY_FILE, "rb") as f:
#     key = f.read()
# cipher = Fernet(key)

# fake = Faker()
# TOTAL = 1_000_000

# def encrypt(txt): return cipher.encrypt(txt.encode()).decode()

# def tokenize(name):
#     tokens = set()
#     name = name.lower()
#     for i in range(len(name)):
#         for j in range(i+2, len(name)+1):
#             tokens.add(name[i:j])
#     return list(tokens)

# def insert_data():
#     with sqlite3.connect(DB) as conn:
#         c = conn.cursor()
#         c.execute("DELETE FROM people")
#         c.execute("DELETE FROM tokens")
#         conn.commit()

#         start_time = time.time()
#         for _ in tqdm(range(TOTAL), desc="Inserting People"):
#             first = fake.first_name()
#             last = fake.last_name()
#             print(first, last)
#             first_enc, last_enc = encrypt(first), encrypt(last)
#             c.execute("INSERT INTO people (first_enc, last_enc) VALUES (?, ?)", (first_enc, last_enc))
#             pid = c.lastrowid

#             for token in tokenize(first) + tokenize(last):
#                 c.execute("INSERT INTO tokens (person_id, token) VALUES (?, ?)", (pid, token))

#             if pid % 10000 == 0:
#                 conn.commit()
#         conn.commit()
#         end_time = time.time()

#     print(f"✅ Inserted {TOTAL} records in {end_time - start_time:.2f} sec")

# if __name__ == '__main__':
#     insert_data()

from faker import Faker
from cryptography.fernet import Fernet
import mysql.connector
from tqdm import tqdm
import os

# ======== Config ========
TOTAL = 1_000_000  # You can adjust to 100000 or more
BATCH_SIZE = 1000
KEY_FILE = "secret.key"
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # 🔁 replace with your password
    "database": "smart_search"
}

# ======== Setup ========
fake = Faker()
if not os.path.exists(KEY_FILE):
    raise FileNotFoundError("Fernet key file not found. Please run the Flask app first.")
with open(KEY_FILE, "rb") as f:
    KEY = f.read()
cipher = Fernet(KEY)

def encrypt(txt):
    return cipher.encrypt(txt.encode()).decode()

def generate_tokens(name):
    name = name.lower()
    tokens = set()
    for i in range(len(name)):
        for j in range(i+2, len(name)+1):  # min 2 chars
            tokens.add(name[i:j])
    return list(tokens)

def insert_batch(cursor, people_batch, tokens_batch):
    cursor.executemany("INSERT INTO people (first_enc, last_enc) VALUES (%s, %s)", people_batch)
    cursor.execute("SELECT LAST_INSERT_ID()")
    first_id = cursor.fetchone()[0]
    ids = list(range(first_id, first_id + len(people_batch)))

    # attach person_ids to tokens
    full_tokens = []
    for i, token_list in enumerate(tokens_batch):
        pid = ids[i]
        full_tokens.extend((pid, t) for t in token_list)

    cursor.executemany("INSERT INTO tokens (person_id, token) VALUES (%s, %s)", full_tokens)

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    print(f"🚀 Inserting {TOTAL:,} records into MySQL...")
    for i in tqdm(range(0, TOTAL, BATCH_SIZE)):
        people_batch = []
        tokens_batch = []
        for _ in range(BATCH_SIZE):
            first = fake.first_name()
            last = fake.last_name()
            print(first, last)
            first_enc = encrypt(first)
            last_enc = encrypt(last)
            people_batch.append((first_enc, last_enc))
            tokens_batch.append(generate_tokens(first) + generate_tokens(last))

        insert_batch(cur, people_batch, tokens_batch)
        conn.commit()

    cur.close()
    conn.close()
    print("✅ Done inserting fake people.")

if __name__ == '__main__':
    main()
