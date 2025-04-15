# from faker import Faker
# import mysql.connector
# from cryptography.fernet import Fernet
# import os

# # Database credentials
# DB_HOST = "localhost"
# DB_USER = "root"
# DB_PASSWORD = ""
# DB_NAME = "whole"
# TABLE_NAME = "names"

# # Path to the file containing the encryption key
# KEY_FILE_PATH = "secret.key"

# def load_key(file_path):
#     """Loads the encryption key from the specified file."""
#     try:
#         with open(file_path, "r") as key_file:
#             key = key_file.read().strip()
#         return key.encode()
#     except FileNotFoundError:
#         print(f"Error: Key file not found at '{file_path}'")
#         return None
#     except Exception as e:
#         print(f"Error reading key file: {e}")
#         return None

# # Load the encryption key
# encryption_key_bytes = load_key(KEY_FILE_PATH)
# if not encryption_key_bytes:
#     exit()  # Exit if the key cannot be loaded
# fernet = Fernet(encryption_key_bytes)

# def encrypt_data(data):
#     """Encrypts the given data."""
#     encrypted_data = fernet.encrypt(data.encode())
#     return encrypted_data

# def connect_db():
#     """Connects to the MySQL database."""
#     try:
#         mydb = mysql.connector.connect(
#             host=DB_HOST,
#             user=DB_USER,
#             password=DB_PASSWORD,
#             database=DB_NAME
#         )
#         return mydb, mydb.cursor()
#     except mysql.connector.Error as err:
#         print(f"Error connecting to MySQL: {err}")
#         return None, None

# def create_table(cursor):
#     """Creates the table if it doesn't exist."""
#     try:
#         cursor.execute(f"""
#             CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 first_name VARBINARY(255) NOT NULL,
#                 last_name VARBINARY(255) NOT NULL
#             )
#         """)
#         print(f"Table '{TABLE_NAME}' created or already exists.")
#     except mysql.connector.Error as err:
#         print(f"Error creating table: {err}")

# def insert_data(cursor, first_name_encrypted, last_name_encrypted):
#     """Inserts encrypted first and last names into the database."""
#     try:
#         sql = f"INSERT INTO {TABLE_NAME} (first_name, last_name) VALUES (%s, %s)"
#         val = (first_name_encrypted, last_name_encrypted)
#         cursor.execute(sql, val)
#     except mysql.connector.Error as err:
#         print(f"Error inserting data: {err}")

# def main():
#     """Generates and inserts 1,000,000 encrypted names into the database."""
#     fake = Faker()
#     mydb, cursor = connect_db()

#     if not mydb:
#         return

#     create_table(cursor)

#     num_records = 1000000
#     batch_size = 1000  # Commit after every batch to improve performance

#     try:
#         for i in range(num_records):
#             first_name = fake.first_name()
#             last_name = fake.last_name()
#             print(first_name, last_name)
#             first_name_encrypted = encrypt_data(first_name)
#             last_name_encrypted = encrypt_data(last_name)

#             insert_data(cursor, first_name_encrypted, last_name_encrypted)

#             if (i + 1) % batch_size == 0:
#                 mydb.commit()
#                 print(f"Inserted {i + 1}/{num_records} records.")

#         mydb.commit()  # Commit any remaining records
#         print(f"Successfully inserted {num_records} encrypted name records.")

#     except Exception as e:
#         print(f"An error occurred during data generation and insertion: {e}")
#         mydb.rollback()

#     finally:
#         if mydb and mydb.is_connected():
#             cursor.close()
#             mydb.close()
#             print("Database connection closed.")

# if __name__ == "__main__":
#     main()

#--------------------------Faker script end here ---------------------------

# from flask import Flask, render_template, request, jsonify
# import mysql.connector
# from cryptography.fernet import Fernet
# import os

# app = Flask(__name__)

# # Database credentials
# DB_HOST = "localhost"
# DB_USER = "root"
# DB_PASSWORD = ""
# DB_NAME = "whole"
# TABLE_NAME = "names"

# # Path to the file containing the encryption key
# KEY_FILE_PATH = "secret.key"

# # --- HTML Content (moved from templates/index.html) ---
# HTML_CONTENT = """
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>User Search and Add</title>
#     <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
#     <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
#     <style>
#         #loader {
#             display: none;
#             border: 5px solid #f3f3f3; /* Light grey */
#             border-top: 5px solid #3498db; /* Blue */
#             border-radius: 50%;
#             width: 40px;
#             height: 40px;
#             animation: spin 2s linear infinite;
#         }

#         @keyframes spin {
#             0% { transform: rotate(0deg); }
#             100% { transform: rotate(360deg); }
#         }
#     </style>
# </head>
# <body>
#     <div class="container mt-5">
#         <h2>Search Users</h2>
#         <div class="form-group">
#             <input type="text" class="form-control" id="search_term" placeholder="Enter name to search">
#             <div id="loader" class="mt-2"></div>
#         </div>
#         <ul class="list-group" id="results">
#             </ul>

#         <hr class="my-4">

#         <h2>Add New User</h2>
#         <form id="add_user_form">
#             <div class="form-group">
#                 <label for="first_name">First Name:</label>
#                 <input type="text" class="form-control" id="first_name" required>
#             </div>
#             <div class="form-group">
#                 <label for="last_name">Last Name:</label>
#                 <input type="text" class="form-control" id="last_name" required>
#             </div>
#             <button type="submit" class="btn btn-primary">Add User</button>
#             <div id="add_user_message" class="mt-2"></div>
#         </form>
#     </div>

#     <script>
#         $(document).ready(function() {
#             $('#search_term').on('input', function() {
#                 let searchTerm = $(this).val().trim();
#                 $('#loader').show();
#                 $('#results').empty(); // Clear previous results

#                 if (searchTerm) {
#                     $.ajax({
#                         url: '/search',
#                         type: 'POST',
#                         data: { search_term: searchTerm },
#                         dataType: 'json',
#                         success: function(response) {
#                             $('#loader').hide();
#                             if (response.results && response.results.length > 0) {
#                                 $.each(response.results, function(index, user) {
#                                     $('#results').append(`<li class="list-group-item">${user.first_name} ${user.last_name} (ID: ${user.id})</li>`);
#                                 });
#                             } else if (response.error) {
#                                 $('#results').append(`<li class="list-group-item text-danger">${response.error}</li>`);
#                             } else {
#                                 $('#results').append('<li class="list-group-item">No results found.</li>');
#                             }
#                         },
#                         error: function(error) {
#                             $('#loader').hide();
#                             $('#results').append(`<li class="list-group-item text-danger">Error: ${error.responseText}</li>`);
#                         }
#                     });
#                 } else {
#                     $('#loader').hide(); // Hide loader if search term is empty
#                 }
#             });

#             $('#add_user_form').on('submit', function(event) {
#                 event.preventDefault();
#                 let firstName = $('#first_name').val().trim();
#                 let lastName = $('#last_name').val().trim();
#                 let messageDiv = $('#add_user_message');
#                 messageDiv.text(''); // Clear previous messages

#                 $.ajax({
#                     url: '/add_user',
#                     type: 'POST',
#                     data: { first_name: firstName, last_name: lastName },
#                     dataType: 'json',
#                     success: function(response) {
#                         if (response.message) {
#                             messageDiv.text(response.message).addClass('text-success').removeClass('text-danger');
#                             $('#add_user_form')[0].reset(); // Clear the form
#                         } else if (response.error) {
#                             messageDiv.text(response.error).addClass('text-danger').removeClass('text-success');
#                         }
#                     },
#                     error: function(error) {
#                         messageDiv.text(`Error: ${error.responseText}`).addClass('text-danger').removeClass('text-success');
#                     }
#                 });
#             });
#         });
#     </script>
# </body>
# </html>
# """

# def load_key(file_path):
#     """Loads the encryption key from the specified file."""
#     try:
#         with open(file_path, "r") as key_file:
#             key = key_file.read().strip()
#         return key.encode()
#     except FileNotFoundError:
#         print(f"Error: Key file not found at '{file_path}'")
#         return None
#     except Exception as e:
#         print(f"Error reading key file: {e}")
#         return None

# # Load the encryption key
# encryption_key_bytes = load_key(KEY_FILE_PATH)
# if not encryption_key_bytes:
#     exit()  # Exit if the key cannot be loaded
# fernet = Fernet(encryption_key_bytes)

# def decrypt_data(encrypted_data):
#     """Decrypts the given data."""
#     try:
#         decrypted_data = fernet.decrypt(encrypted_data).decode()
#         return decrypted_data
#     except Exception as e:
#         print(f"Error decrypting data: {e}")
#         return None

# def encrypt_data(data):
#     """Encrypts the given data."""
#     encrypted_data = fernet.encrypt(data.encode())
#     return encrypted_data

# def connect_db():
#     """Connects to the MySQL database."""
#     try:
#         mydb = mysql.connector.connect(
#             host=DB_HOST,
#             user=DB_USER,
#             password=DB_PASSWORD,
#             database=DB_NAME
#         )
#         return mydb, mydb.cursor()
#     except mysql.connector.Error as err:
#         print(f"Error connecting to MySQL: {err}")
#         return None, None

# @app.route("/", methods=["GET"])
# def index():
#     return HTML_CONTENT

# @app.route("/search", methods=["POST"])
# def search():
#     search_term = request.form.get("search_term", "").strip()
#     if not search_term:
#         return jsonify({"results": []})

#     mydb, cursor = connect_db()
#     if not mydb:
#         return jsonify({"error": "Database connection error"})

#     try:
#         sql = f"""
#             SELECT id, first_name, last_name
#             FROM {TABLE_NAME}
#             WHERE HEX(first_name) LIKE %s OR HEX(last_name) LIKE %s
#         """
#         val = (f"%{search_term.encode('utf-8').hex()}%", f"%{search_term.encode('utf-8').hex()}%")
#         cursor.execute(sql, val)
#         results = cursor.fetchall()
#         decrypted_results = []
#         for row in results:
#             first_name = decrypt_data(row[1])
#             last_name = decrypt_data(row[2])
#             if first_name and last_name and (search_term.lower() in first_name.lower() or search_term.lower() in last_name.lower()):
#                 decrypted_results.append({"id": row[0], "first_name": first_name, "last_name": last_name})
#         return jsonify({"results": decrypted_results})
#     except mysql.connector.Error as err:
#         print(f"Error searching data: {err}")
#         return jsonify({"error": "Error searching database"})
#     finally:
#         if mydb and mydb.is_connected():
#             cursor.close()
#             mydb.close()

# @app.route("/add_user", methods=["POST"])
# def add_user():
#     first_name = request.form.get("first_name").strip()
#     last_name = request.form.get("last_name").strip()

#     if not first_name or not last_name:
#         return jsonify({"error": "First and last name are required"})

#     first_name_encrypted = encrypt_data(first_name)
#     last_name_encrypted = encrypt_data(last_name)

#     mydb, cursor = connect_db()
#     if not mydb:
#         return jsonify({"error": "Database connection error"})

#     try:
#         sql = f"INSERT INTO {TABLE_NAME} (first_name, last_name) VALUES (%s, %s)"
#         val = (first_name_encrypted, last_name_encrypted)
#         cursor.execute(sql, val)
#         mydb.commit()
#         return jsonify({"message": "User added successfully"})
#     except mysql.connector.Error as err:
#         print(f"Error adding user: {err}")
#         mydb.rollback()
#         return jsonify({"error": "Error adding user to database"})
#     finally:
#         if mydb and mydb.is_connected():
#             cursor.close()
#             mydb.close()

# if __name__ == "__main__":
#     app.run(debug=True)


# ----------------------------------------- decrypt by every charecter by comparing hex value end here -----------------

from flask import Flask, render_template, request, jsonify
import mysql.connector
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Database credentials
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "whole"
TABLE_NAME = "names"

# Path to the file containing the encryption key
KEY_FILE_PATH = "secret.key"

# --- HTML Content ---
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Search and Add</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        #full-screen-loader {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5); /* Semi-transparent black */
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000; /* Ensure it's on top */
            display: none; /* Hidden by default */
        }

        .loader {
            border: 8px solid #f3f3f3; /* Light grey */
            border-top: 8px solid #3498db; /* Blue */
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 2s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        button:disabled {
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="container mt-5">
        <h2>Search Users</h2>
        <div class="form-group">
            <input type="text" class="form-control" id="search_term" placeholder="Enter name to search">
        </div>
        <button id="search_button" class="btn btn-primary">Search</button>
        <div id="full-screen-loader">
            <div class="loader"></div>
        </div>
        <ul class="list-group mt-3" id="results">
        </ul>

        <hr class="my-4">

        <h2>Add New User</h2>
        <form id="add_user_form">
            <div class="form-group">
                <label for="add_first_name">First Name:</label>
                <input type="text" class="form-control" id="add_first_name" required>
            </div>
            <div class="form-group">
                <label for="add_last_name">Last Name:</label>
                <input type="text" class="form-control" id="add_last_name" required>
            </div>
            <button type="submit" id="add_user_button" class="btn btn-success">Add User</button>
            <div id="add_user_message" class="mt-2"></div>
        </form>
    </div>

    <script>
        $(document).ready(function() {
            $('#search_button').on('click', function() {
                let searchTerm = $('#search_term').val().trim();
                if (searchTerm) {
                    $('#full-screen-loader').show();
                    $('#search_button').prop('disabled', true);
                    $('#add_user_button').prop('disabled', true);
                    $('#results').empty();

                    $.ajax({
                        url: '/search',
                        type: 'POST',
                        data: { search_term: searchTerm },
                        dataType: 'json',
                        success: function(response) {
                            $('#full-screen-loader').hide();
                            $('#search_button').prop('disabled', false);
                            $('#add_user_button').prop('disabled', false);
                            if (response.results && response.results.length > 0) {
                                $.each(response.results, function(index, user) {
                                    $('#results').append(`<li class="list-group-item">${user.first_name} ${user.last_name} (ID: ${user.id})</li>`);
                                });
                            } else if (response.error) {
                                $('#results').append(`<li class="list-group-item text-danger">${response.error}</li>`);
                            } else {
                                $('#results').append('<li class="list-group-item">No results found.</li>');
                            }
                        },
                        error: function(error) {
                            $('#full-screen-loader').hide();
                            $('#search_button').prop('disabled', false);
                            $('#add_user_button').prop('disabled', false);
                            $('#results').append(`<li class="list-group-item text-danger">Error: ${error.responseText}</li>`);
                        }
                    });
                } else {
                    $('#results').html('<li class="list-group-item text-warning">Please enter a search term.</li>');
                }
            });

            $('#add_user_form').on('submit', function(event) {
                event.preventDefault();
                let firstName = $('#add_first_name').val().trim();
                let lastName = $('#add_last_name').val().trim();
                let messageDiv = $('#add_user_message');
                let addButton = $('#add_user_button');
                messageDiv.text('');
                addButton.prop('disabled', true);

                $.ajax({
                    url: '/add_user',
                    type: 'POST',
                    data: { first_name: firstName, last_name: lastName },
                    dataType: 'json',
                    success: function(response) {
                        addButton.prop('disabled', false);
                        if (response.message) {
                            messageDiv.text(response.message).addClass('text-success').removeClass('text-danger');
                            $('#add_user_form')[0].reset();
                        } else if (response.error) {
                            messageDiv.text(response.error).addClass('text-danger').removeClass('text-success');
                        }
                    },
                    error: function(error) {
                        addButton.prop('disabled', false);
                        messageDiv.text(`Error: ${error.responseText}`).addClass('text-danger').removeClass('text-success');
                    }
                });
            });
        });
    </script>
</body>
</html>
"""

def load_key(file_path):
    """Loads the encryption key from the specified file."""
    try:
        with open(file_path, "r") as key_file:
            key = key_file.read().strip()
        return key.encode()
    except FileNotFoundError:
        print(f"Error: Key file not found at '{file_path}'")
        return None
    except Exception as e:
        print(f"Error reading key file: {e}")
        return None

# Load the encryption key
encryption_key_bytes = load_key(KEY_FILE_PATH)
if not encryption_key_bytes:
    exit()
fernet = Fernet(encryption_key_bytes)

def decrypt_data(encrypted_data):
    """Decrypts the given data."""
    try:
        decrypted_data = fernet.decrypt(encrypted_data).decode()
        return decrypted_data
    except Exception as e:
        print(f"Error decrypting data: {e}")
        return None

def encrypt_data(data):
    """Encrypts the given data."""
    encrypted_data = fernet.encrypt(data.encode())
    return encrypted_data

def connect_db():
    """Connects to the MySQL database."""
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return mydb, mydb.cursor()
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None, None

@app.route("/", methods=["GET"])
def index():
    return HTML_CONTENT

@app.route("/search", methods=["POST"])
def search():
    search_term = request.form.get("search_term", "").strip().lower()
    if not search_term:
        return jsonify({"results": []})

    mydb, cursor = connect_db()
    if not mydb:
        return jsonify({"error": "Database connection error"})

    try:
        sql = f"SELECT id, first_name, last_name FROM {TABLE_NAME}"
        cursor.execute(sql)
        results = cursor.fetchall()
        decrypted_results = []
        for row in results:
            first_name_encrypted = row[1]
            last_name_encrypted = row[2]
            first_name = decrypt_data(first_name_encrypted)
            last_name = decrypt_data(last_name_encrypted)
            if first_name and last_name and (search_term in first_name.lower() or search_term in last_name.lower()):
                decrypted_results.append({"id": row[0], "first_name": first_name, "last_name": last_name})
        return jsonify({"results": decrypted_results})
    except mysql.connector.Error as err:
        print(f"Error searching data: {err}")
        return jsonify({"error": "Error searching database"})
    finally:
        if mydb and mydb.is_connected():
            cursor.close()
            mydb.close()

@app.route("/add_user", methods=["POST"])
def add_user():
    first_name = request.form.get("first_name").strip()
    last_name = request.form.get("last_name").strip()

    if not first_name or not last_name:
        return jsonify({"error": "First and last name are required"})

    first_name_encrypted = encrypt_data(first_name)
    last_name_encrypted = encrypt_data(last_name)

    mydb, cursor = connect_db()
    if not mydb:
        return jsonify({"error": "Database connection error"})

    try:
        sql = f"INSERT INTO {TABLE_NAME} (first_name, last_name) VALUES (%s, %s)"
        val = (first_name_encrypted, last_name_encrypted)
        cursor.execute(sql, val)
        mydb.commit()
        return jsonify({"message": "User added successfully"})
    except mysql.connector.Error as err:
        print(f"Error adding user: {err}")
        mydb.rollback()
        return jsonify({"error": "Error adding user to database"})
    finally:
        if mydb and mydb.is_connected():
            cursor.close()
            mydb.close()

if __name__ == "__main__":
    app.run(debug=True)