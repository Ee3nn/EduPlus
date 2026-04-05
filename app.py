import os
from flask import Flask, send_from_directory, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder="static")
app.secret_key = os.urandom(24)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/register", methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"message": "User already exists"}), 400

    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, email=email, password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201

@app.route("/login", methods=['POST'])
def login():
    data = request.json
    login_id = data.get('loginId') # username or email
    password = data.get('password')

    user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()

    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        return jsonify({"message": "Login successful", "username": user.username}), 200
    
    return jsonify({"message": "Invalid credentials"}), 401

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
        "email": user.email
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
