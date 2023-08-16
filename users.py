from flask import Flask, request, jsonify,render_template
import mysql.connector
from passlib.hash import sha256_crypt
import jwt
import datetime
from functools import wraps
import random
import string
import smtplib
from flask_cors import cross_origin



# Email Configuration
smtp_server = 'smtp.gmail.com'
smtp_port = 587
smtp_username = 'klaimohamed1994@gmail.com'
smtp_password = 'nnpvjpcogwzpzsbv'
from_email = 'klaimohamed1994@gmail.com'
app = Flask(__name__)

# MySQL configuration
db_config = {"host": "localhost", "user": "root", "password": "", "database": "emails"}


# Helper function to create a database connection
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn


# Helper function to close the database connection
def close_db_connection(conn):
    if conn.is_connected():
        conn.close()


# ...

# Secret key for JWT token (change this to a secure random string)
app.config["SECRET_KEY"] = "secret_key"


# Helper function to generate JWT token
def generate_token(user_id):
    payload = {
        "id": user_id,
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(days=7),  # Token expires in 1 day
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


# Create a new user
@app.route("/users", methods=["POST"])
@cross_origin()

def create_user():
    data = request.get_json()
    username = data["username"]
    email = data["email"]
    password = data["password"]
    nom = data["nom"]
    prenom = data["prenom"]

    # Hash the password using sha256_crypt
    hashed_password = sha256_crypt.hash(password)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the email already exists in the database
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            close_db_connection(conn)
            return jsonify({"message": "User with this email already exists"}), 409

        # Insert the new user into the database
        query = "INSERT INTO users (username, email, password, nom, prenom) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (username, email, hashed_password, nom, prenom))
        user_id = cursor.lastrowid  # Get the ID of the inserted user
        conn.commit()
        close_db_connection(conn)

        # Generate JWT token
        token = generate_token(user_id)

        return jsonify({"message": "User created successfully", "token": token}), 201
    except Exception as e:
        close_db_connection(conn)
        return jsonify({"error": str(e)}), 500


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user_id = data["id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token!"}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated


# Get all users
@app.route("/users", methods=["GET"])
@token_required
def get_users(current_user_id):
    try:
        # Ensure only authenticated users can access this endpoint
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM users"
        cursor.execute(query)
        users = cursor.fetchall()
        close_db_connection(conn)
        return jsonify(users), 200
    except Exception as e:
        close_db_connection(conn)
        return jsonify({"error": str(e)}), 500


# Get a specific user by ID
@app.route("/users/<int:user_id>", methods=["GET"])
# @token_required
@cross_origin()
def get_user( user_id):
    try:
        # Ensure only authenticated users can access this endpoint
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        close_db_connection(conn)
        if user:
            return jsonify(user), 200
        else:
            return jsonify({"message": "User not found"}), 404
    except Exception as e:
        close_db_connection(conn)
        return jsonify({"error": str(e)}), 500


# Delete a user by ID
@app.route("/users/<int:user_id>", methods=["DELETE"])
@cross_origin()
def delete_user( user_id):
    try:
        # Ensure only authenticated users can access this endpoint
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "DELETE FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        conn.commit()
        close_db_connection(conn)
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        close_db_connection(conn)
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/users/<int:user_id>", methods=["PUT"])
@cross_origin()
def update_user(user_id):
    data = request.get_json()
    username = data["username"]
    email = data["email"]
    nom = data["nom"]
    prenom = data["prenom"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the email exists in the database
        query = "SELECT id, password FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()

        if user:
            # Check if 'password' is present in the request data and hash it if it is
            if "password" in data:
                password = data["password"]
                hashed_password = sha256_crypt.hash(password)          
        else:
            close_db_connection(conn)
            return jsonify({"message": "Invalid User with ID"}), 401

        query = "UPDATE users SET username = %s, email = %s, nom = %s, prenom = %s WHERE id = %s"
        cursor.execute(query, (username, email, nom, prenom, user_id))

        conn.commit()
        close_db_connection(conn)
        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        close_db_connection(conn)
        return jsonify({"error": str(e)}), 500
@app.route('/change_password/<int:user_id>', methods=['PUT'])
@cross_origin()
def change_password(user_id):
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({"error": "Current password and new password are required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Retrieve user data from the database
        cursor.execute("SELECT id, password FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        if not sha256_crypt.verify(current_password, user['password']):
            return jsonify({"error": "Invalid current password"}), 401

        hashed_new_password = sha256_crypt.hash(new_password)
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_new_password, user_id))
        conn.commit()

        return jsonify({"message": "Password changed successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route("/login", methods=["POST"])
@cross_origin()
def login():
    data = request.get_json()
    email = data["email"]
    password = data["password"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the email exists in the database
        query = "SELECT id, password FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user:
            user_id = user[0]  # Access the user's ID using index 0
            hashed_password = user[1]  # Access the hashed password using index 1

            # Validate the password
            if sha256_crypt.verify(password, hashed_password):
                # Password is valid, generate JWT token
                token = generate_token(user_id)
                close_db_connection(conn)
                return jsonify({"message": "Login successful", "token": token,"id":user_id}), 200
            else:
                close_db_connection(conn)
                return jsonify({"message": "Invalid email or password"}), 401
        else:
            close_db_connection(conn)
            return jsonify({"message": "Invalid email or password"}), 401

    except Exception as e:
        close_db_connection(conn)
        return jsonify({"error": str(e)}), 500
@app.route('/forgot_password', methods=['POST'])
@cross_origin()

def forgot_password():
    data = request.get_json()
    email = data['email']
    db_connection = get_db_connection()

        # Check if the email exists in the database
    cursor = db_connection.cursor()
    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()

    if user:
            # Generate a random token to use in the password reset link
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            
            # Save the token and the associated user's email in the database
            cursor.execute('INSERT INTO reset_tokens (token, email) VALUES (%s, %s)', (token, email))
            db_connection.commit()

            # Send the email with the password reset link
            message = f"Click the link below to reset your password:\n\n"
            reset_link = f"http://localhost:4200/newpassword/{token}"
            message += reset_link

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(from_email, email, message)
            server.quit()
    return jsonify(token)
   

@app.route('/newpassword/<token>', methods=['POST'])
@cross_origin()
def reset_password(token):
    data = request.get_json()
    new_password = data['password']
    db_connection = get_db_connection()

    cursor = db_connection.cursor()
    cursor.execute('SELECT * FROM reset_tokens WHERE token = %s', (token,))
    token_data = cursor.fetchone()

    if token_data:
            email = token_data[1]
            # Update the user's password in the database
            hashed_password = sha256_crypt.hash(new_password)
            cursor.execute('UPDATE users SET password = %s WHERE email = %s', (hashed_password, email))
            # Delete the used token from the tokens table
            cursor.execute('DELETE FROM reset_tokens WHERE token = %s', (token,))
            db_connection.commit()
            return jsonify("token_data"),200
    else:
            return "Invalid or expired token.",404
    
    


if __name__ == "__main__":
    app.run(debug=True)
