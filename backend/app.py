import os
import time
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pymysql
import bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity, get_jwt
)

app = Flask(__name__, static_folder='.')
CORS(app)

# JWT SECURITY

app.config['JWT_SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-in-production!')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# DATABASE CONNECTION

def get_db_connection():
    retries = 5
    while retries > 0:
        try:
            connection = pymysql.connect(
                host=os.environ.get('DB_HOST', '127.0.0.1'),
                port=int(os.environ.get('DB_PORT', '3306')),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASSWORD', ''),
                database=os.environ.get('DB_NAME', 'gateway_db'),
                connect_timeout=5,
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except pymysql.MySQLError as e:
            print(f"Waiting for database... Retries left: {retries - 1}")
            retries -= 1
            time.sleep(3)
    raise ConnectionError("Could not connect to the database")

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "Please fill in all fields."}), 400

    if len(username) > 50 or len(password) > 128:
        return jsonify({"error": "Data too long."}), 400

    try:
        conn = get_db_connection()
    except ConnectionError:
        return jsonify({"error": "No connection to the database. Please try again later."}), 503

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({"error": "This username is already taken."}), 409

            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'user')",
                (username, hashed_password)
            )
        conn.commit()
        return jsonify({"message": "Registration successful! You can now log in."}), 201
    except Exception as e:
        return jsonify({"error": "Server error."}), 500
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "Please fill in all fields."}), 400

    try:
        conn = get_db_connection()
    except ConnectionError:
        return jsonify({"error": "No connection to the database. Please try again later."}), 503

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Invalid username or password."}), 401

        stored_hash = user['password_hash'].encode('utf-8')
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            return jsonify({"error": "Invalid username or password."}), 401

        access_token = create_access_token(
            identity=str(user['id']),
            additional_claims={
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
            },
        )

        return jsonify({
            "access_token": access_token,
            "user_id": user['id'],
            "username": user['username'],
            "role": user['role'],
        }), 200
    except Exception:
        return jsonify({"error": "Server error."}), 500
    finally:
        conn.close()

# CHAT HISTORY

@app.route('/api/chat/history', methods=['GET'])
@jwt_required()
def get_chat_history():
    claims = get_jwt()
    user_id = claims.get('user_id')

    try:
        conn = get_db_connection()
    except ConnectionError:
        return jsonify({"error": "No connection to the database. Please try again later."}), 503

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, role, message, created_at FROM chat_messages WHERE user_id = %s ORDER BY created_at ASC LIMIT 100",
                (user_id,)
            )
            return jsonify(cursor.fetchall()), 200
    finally:
        conn.close()

@app.route('/api/chat/message', methods=['POST'])
@jwt_required()
def save_chat_message():
    claims = get_jwt()
    user_id = claims.get('user_id')
    data = request.json
    role = data.get('role', 'user')
    message = data.get('message', '').strip()

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    if role not in ('user', 'assistant'):
        return jsonify({"error": "Invalid role"}), 400

    try:
        conn = get_db_connection()
    except ConnectionError:
        return jsonify({"error": "No connection to the database. Please try again later."}), 503

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO chat_messages (user_id, role, message) VALUES (%s, %s, %s)",
                (user_id, role, message)
            )
        conn.commit()
        return jsonify({"message": "Saved"}), 201
    except Exception as e:
        return jsonify({"error": "Server error"}), 500
    finally:
        conn.close()

# USER DIRECTORY

@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    claims = get_jwt()
    user_id = claims.get('user_id')
    role = claims.get('role')

    if role != 'admin':
        return jsonify({"error": "Access denied"}), 403

    try:
        conn = get_db_connection()
    except ConnectionError:
        return jsonify({"error": "No connection to the database. Please try again later."}), 503

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, role FROM users ORDER BY username")
            users = cursor.fetchall()
        return jsonify(users), 200
    except Exception:
        return jsonify({"error": "Server error."}), 500
    finally:
        conn.close()

@app.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    claims = get_jwt()
    current_user_id = claims.get('user_id')
    role = claims.get('role')

    if current_user_id != user_id and role != 'admin':
        return jsonify({"error": "Access denied"}), 403

    try:
        conn = get_db_connection()
    except ConnectionError:
        return jsonify({"error": "No connection to the database. Please try again later."}), 503

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found."}), 404
        
        return jsonify(user), 200
    except Exception:
        return jsonify({"error": "Server error."}), 500
    finally:
        conn.close()

# STATIC FILES

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# APP LAUNCHER

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
