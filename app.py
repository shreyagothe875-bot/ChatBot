from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from google import genai
from google.genai import types
import sqlite3
import json
import time
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "sys_core_super_secret_key"

# --- API Configuration ---
# Your new API Key
API_KEY = "AIzaSyBnh9mcuxwCV4tUHrhAe-dAFEatNfn2G7Y" 
client = genai.Client(api_key=API_KEY)

def init_db():
    with sqlite3.connect('sys_users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            username TEXT UNIQUE NOT NULL, 
                            password TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            user_id INTEGER, 
                            user_msg TEXT, 
                            bot_text TEXT, 
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                            FOREIGN KEY (user_id) REFERENCES users (id))''')
        conn.commit()

init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('sys_users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('home'))
        return render_template('auth.html', error="ACCESS DENIED: Invalid credentials.")
    return render_template('auth.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('auth.html', error="ERROR: Missing fields.")
        hashed_password = generate_password_hash(password)
        try:
            with sqlite3.connect('sys_users.db') as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
                conn.commit()
            return render_template('auth.html', success="ACCOUNT CREATED: You may now log in.")
        except sqlite3.IntegrityError:
            return render_template('auth.html', error="ERROR: Username already exists.")
    return render_template('auth.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/history', methods=['GET'])
def get_history():
    if 'user_id' not in session: return jsonify([])
    with sqlite3.connect('sys_users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_msg, bot_text FROM messages WHERE user_id = ? ORDER BY id ASC', (session['user_id'],))
        rows = cursor.fetchall()
    return jsonify([{"user": row[0], "bot": row[1]} for row in rows])

@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({"response": "SYSTEM ERROR: Unauthorized access."})

    user_message = request.form.get('message', '')
    
    try:
        print(f"--- LOG: Request from {session['username']} ---")
        # Standard chat call
        response = client.models.generate_content(model="gemini-2.0-flash", contents=user_message)
        bot_response = response.text
        
        with sqlite3.connect('sys_users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO messages (user_id, user_msg, bot_text) VALUES (?, ?, ?)', 
                           (session['user_id'], user_message, bot_response))
            conn.commit()
        
        return jsonify({"response": bot_response})
        
    except Exception as e:
        print(f"!!! REAL ERROR IN TERMINAL: {e}")
        if "429" in str(e):
            return jsonify({"response": "PROTOCOL COOLING: Please wait 30 seconds."})
        return jsonify({"response": "SYSTEM BUSY: Please try again."})

@app.route('/generate_flashcards', methods=['POST'])
def generate_flashcards():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    try:
        with sqlite3.connect('sys_users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_msg, bot_text FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 1', (session['user_id'],))
            row = cursor.fetchone()

        if not row: return jsonify({"error": "Chat with P.A.C.E. first!"})

        prompt = f"Generate 5 educational flashcards as JSON for: {row[1]}"
        response = client.models.generate_content(
            model="gemini-2-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return jsonify(json.loads(response.text))
    except Exception as e:
        print(f"FLASHCARD ERROR: {e}")
        return jsonify({"error": "Model busy. Try again."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)