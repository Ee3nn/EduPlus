import os
from flask import Flask, send_from_directory, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, inspect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__, static_folder="static")
app.secret_key = os.urandom(24)

# Persistent Storage Logic for Azure
is_azure = 'WEBSITE_SITE_NAME' in os.environ
if is_azure:
    # Use /home for persistent storage on Azure
    db_path = '/home/users.db'
    UPLOAD_FOLDER = '/home/avatars'
else:
    # Local development
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'users.db')
    UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads/avatars')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    profile_pic = db.Column(db.String(200), nullable=True)
    selected_electives = db.Column(db.Text, nullable=True)

with app.app_context():
    db.create_all()
    # Migration: Ensure columns exist (for existing DBs)
    try:
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('user')]
        if 'selected_electives' not in columns:
            db.session.execute(db.text("ALTER TABLE user ADD COLUMN selected_electives TEXT"))
        if 'profile_pic' not in columns:
            db.session.execute(db.text("ALTER TABLE user ADD COLUMN profile_pic VARCHAR(200)"))
        db.session.commit()
    except Exception as e:
        print(f"Database migration info: {e}")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# Specialized route to serve avatars from persistent storage
@app.route("/static/uploads/avatars/<path:filename>")
def serve_avatar(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/avatar/upload", methods=['POST'])
def upload_avatar():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if 'avatar' not in request.files:
        return jsonify({"message": "No file"}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    
    user = db.session.get(User, session['user_id'])
    filename = secure_filename(f"user_{user.id}.jpg")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        img = Image.open(file)
        width, height = img.size
        size = min(width, height)
        left = (width - size) / 2
        top = (height - size) / 2
        right = (width + size) / 2
        bottom = (height + size) / 2
        img = img.crop((left, top, right, bottom))
        img.convert('RGB').save(filepath, "JPEG")
        
        user.profile_pic = filename
        db.session.commit()
        # Return the public URL path
        return jsonify({"message": "Avatar uploaded", "url": f"/static/uploads/avatars/{filename}"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route("/profile/save_electives", methods=['POST'])
def save_electives():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    user = db.session.get(User, session['user_id'])
    data = request.json
    user.selected_electives = data.get('electives')
    db.session.commit()
    return jsonify({"message": "Electives saved"}), 200

@app.route("/register", methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Invalid JSON"}), 400
            
        username = data.get('username')
        email = data.get('email', '').lower()
        password = data.get('password')

        if not username or not email or not password:
            return jsonify({"message": "All fields are required"}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({"message": "Username already taken"}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Email already registered"}), 400

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({"message": "Server error during registration"}), 500

@app.route("/login", methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Invalid JSON"}), 400
            
        login_id = data.get('loginId')
        password = data.get('password')

        if not login_id or not password:
            return jsonify({"message": "Username/Email and Password are required"}), 400

        user = User.query.filter(or_(User.username == login_id, User.email == login_id)).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return jsonify({
                "message": "Login successful", 
                "username": user.username,
                "electives": user.selected_electives
            }), 200
        
        return jsonify({"message": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({"message": f"Server error: {str(e)}"}), 500

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out"}), 200

@app.route("/profile", methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    return jsonify({
        "username": user.username,
        "email": user.email,
        "profile_pic": f"/static/uploads/avatars/{user.profile_pic}" if user.profile_pic else None,
        "electives": user.selected_electives
    }), 200

@app.route("/profile/update", methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    user = db.session.get(User, session['user_id'])
    data = request.json
    
    new_username = data.get('username')
    new_email = data.get('email')
    new_password = data.get('password')
    
    if new_username:
        if User.query.filter(User.username == new_username, User.id != user.id).first():
            return jsonify({"message": "Username already taken"}), 400
        user.username = new_username
        
    if new_email:
        if User.query.filter(User.email == new_email, User.id != user.id).first():
            return jsonify({"message": "Email already in use"}), 400
        user.email = new_email
        
    if new_password:
        user.password_hash = generate_password_hash(new_password)
        
    db.session.commit()
    return jsonify({"message": "Profile updated successfully", "username": user.username}), 200

@app.route("/profile/delete", methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    user = db.session.get(User, session['user_id'])
    db.session.delete(user)
    db.session.commit()
    session.pop('user_id', None)
    return jsonify({"message": "Account deleted successfully"}), 200

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(debug=True)
