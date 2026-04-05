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
# Fetch the API key securely from the environment variables (Render will provide this)
API_KEY = os.environ.get("GEMINI_API_KEY") 
client = genai.Client(api_key=API_KEY)

# --- Database Initialization ---
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

# --- Authentication Routes ---
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
        else:
            return render_template('auth.html', error="ACCESS DENIED: Invalid credentials.")
    return render_template('auth.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
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

# --- Main App Routes ---
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/history', methods=['GET'])
def get_history():
    if 'user_id' not in session:
        return jsonify([])
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
        with sqlite3.connect('sys_users.db') as conn:
            cursor = conn.cursor()
            # Fetch last 2 exchanges for context
            cursor.execute('SELECT user_msg, bot_text FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 2', (session['user_id'],))
            history_rows = cursor.fetchall()
            history_rows.reverse()
            
            history_context = "".join([f"User: {row[0]}\nBot: {row[1]}\n\n" for row in history_rows])
            final_prompt = f"Context:\n{history_context}\nQuestion: {user_message}"

            response = client.models.generate_content(model="gemini-2.5-flash", contents=final_prompt)
            bot_response = response.text
            
            cursor.execute('INSERT INTO messages (user_id, user_msg, bot_text) VALUES (?, ?, ?)', (session['user_id'], user_message, bot_response))
            conn.commit()
        
        return jsonify({"response": bot_response})
        
    except Exception as e:
        if "429" in str(e):
            return jsonify({"response": "I'm thinking too fast! Please wait 30 seconds."})
        return jsonify({"response": f"SYSTEM ERROR: {str(e)}"})
    
# --- Flashcard Generation Route ---
@app.route('/generate_flashcards', methods=['POST'])
def generate_flashcards():
    time.sleep(1.5) 
    
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        with sqlite3.connect('sys_users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_msg, bot_text FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 1', (session['user_id'],))
            row = cursor.fetchone()

        if not row:
            return jsonify({"error": "Please chat with P.A.C.E. about a topic first!"})

        context = f"User asked: {row[0]}\nBot answered: {row[1]}"
        flashcard_prompt = f"""
        Generate exactly 5 educational flashcards based on this context:
        {context}
        
        Format as a JSON array with 'question' and 'answer' keys.
        """

        # Force the API to return pure JSON
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=flashcard_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        flashcards = json.loads(response.text)
        return jsonify(flashcards)

    except Exception as e:
        print(f"\n❌ FLASHCARD CRASH: {str(e)}\n") 
        return jsonify({"error": "Failed to build cards. Try asking a shorter question!"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)