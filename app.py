from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key

# Cloudinary configuration
cloudinary.config(
    cloud_name="dro9la4md",
    api_key="543898143451387",
    api_secret="d9kNxlhA-hBrOBJe3QjO6dI5jjM",
    secure=True
)

# Database setup
def get_db():
    db = sqlite3.connect('storage_app.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# Check if database exists, if not create it
if not os.path.exists('storage_app.db'):
    with open('schema.sql', 'w') as f:
        f.write('''
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS files;
        
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            public_id TEXT NOT NULL,
            url TEXT NOT NULL,
            filename TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            format TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        ''')
    init_db()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Routes for authentication
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        db = get_db()
        error = None
        
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif not email:
            error = 'Email is required.'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f"User {username} is already registered."
        elif db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone() is not None:
            error = f"Email {email} is already registered."
        
        if error is None:
            db.execute(
                'INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), email)
            )
            db.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        
        flash(error)
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        error = None
        
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'
        
        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        
        flash(error)
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Main routes
@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session.get('username'))

# Upload File
import re
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    try:
        # Extract user ID for folder structure
        user_folder = f"user_{session['user_id']}"
        
        # Clean filename: replace spaces & special characters with underscores
        filename = re.sub(r"[^\w\-_.]", "_", file.filename)

        # Ensure extension is retained
        file_ext = os.path.splitext(filename)[-1]  # Get .pdf, .txt, etc.
        file_base_name = os.path.splitext(filename)[0]  # Get filename without extension
        public_id = f"{user_folder}/{file_base_name}"  

        # Detect resource type
        resource_type = "raw" if file_ext.lower() in [".pdf", ".txt", ".zip"] else "auto"

        # Upload to Cloudinary with forced attachment (preserves extension)
        upload_result = cloudinary.uploader.upload(
            file,
            resource_type=resource_type,
            public_id=public_id,
            format=file_ext.replace(".", ""),  # Ensures correct extension
            attachment=True  # Forces correct download behavior
        )

        # Just use the secure_url directly from the upload result
        file_url = upload_result["secure_url"]

        # Save to database
        db = get_db()
        db.execute(
            '''INSERT INTO files (user_id, public_id, url, filename, resource_type, format) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (
                session['user_id'], 
                upload_result["public_id"], 
                file_url,  
                filename,
                upload_result["resource_type"],
                upload_result.get("format", file_ext.replace(".", ""))  
            )
        )
        db.commit()

        return jsonify({
            "url": file_url,
            "public_id": upload_result["public_id"],
            "filename": filename
        })
    
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500
# List Files for current user
@app.route('/files', methods=['GET'])
@login_required
def list_files():
    try:
        db = get_db()
        user_files = db.execute(
            'SELECT * FROM files WHERE user_id = ? ORDER BY created_at DESC',
            (session['user_id'],)
        ).fetchall()
        
        files_list = []
        for file in user_files:
            files_list.append({
                'id': file['id'],
                'public_id': file['public_id'],
                'url': file['url'],
                'filename': file['filename'],
                'resource_type': file['resource_type'],
                'format': file['format'],
                'created_at': file['created_at']
            })
        
        return jsonify(files_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Delete File
@app.route('/delete/<file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    try:
        db = get_db()
        
        # Get file info and check if it belongs to current user
        file = db.execute(
            'SELECT * FROM files WHERE id = ? AND user_id = ?',
            (file_id, session['user_id'])
        ).fetchone()
        
        if not file:
            return jsonify({"error": "File not found or access denied"}), 404
        
        # Delete from Cloudinary
        cloudinary.uploader.destroy(file['public_id'])
        
        # Delete from database
        db.execute('DELETE FROM files WHERE id = ?', (file_id,))
        db.commit()
        
        return jsonify({"message": "File deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# User profile
@app.route('/profile')
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    file_count = db.execute('SELECT COUNT(*) as count FROM files WHERE user_id = ?', 
                           (session['user_id'],)).fetchone()['count']
    
    return render_template('profile.html', user=user, file_count=file_count)

if __name__ == '__main__':
    app.run(debug=True)