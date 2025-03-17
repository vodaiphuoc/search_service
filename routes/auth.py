# routes/auth.py
from flask import Blueprint, request, jsonify, current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps
from utils.validate_field import validate_password, validate_email
from database.db import db
from models import User
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(user_id=data['user_id']).first()
            if not current_user:
                return jsonify({'message': 'Invalid token!'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401

        return f(current_user, *args, **kwargs)
    
    return decorated

def send_verification_email(user_email, verification_token):
    """Send verification email to user"""
    sender_email = current_app.config['MAIL_USERNAME']
    password = current_app.config['MAIL_PASSWORD']

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = user_email
    message["Subject"] = "Verify your email"

    verification_url = url_for('auth.verify_email', 
                             token=verification_token, 
                             _external=True)
    
    body = f"Click the following link to verify your email: {verification_url}"
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, user_email, message.as_string())

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()

        # Validate required fields
        if not all(key in data for key in ['username', 'email', 'password']):
            return jsonify({'message': 'Missing required fields'}), 400

        # Validate password
        is_valid_password, password_message = validate_password(data['password'])
        if not is_valid_password:
            return jsonify({'message': password_message}), 400

        # Validate email
        is_valid_email, email_message = validate_email(data['email'])
        if not is_valid_email:
            return jsonify({'message': email_message}), 400

        # Check existing user
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'message': 'Username already exists'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already exists'}), 400

        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password'], method='pbkdf2:sha256')
        )

        # Generate verification token
        verification_token = new_user.generate_verification_token()
        
        db.session.add(new_user)
        db.session.commit()

        # Send verification email
        try:
            send_verification_email(new_user.email, verification_token)
        except Exception as e:
            current_app.logger.error(f"Failed to send verification email: {str(e)}")
            # Don't return error to client, just log it

        return jsonify({
            'message': 'User created successfully. Please check your email to verify your account.',
            'user': {
                'username': new_user.username,
                'email': new_user.email
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error creating user', 'error': str(e)}), 500

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        return jsonify({'message': 'Invalid verification token'}), 400
    
    user.email_verified = True
    user.verification_token = None
    db.session.commit()
    
    return jsonify({'message': 'Email verified successfully'})

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': 'Missing username or password'}), 400

        user = User.query.filter_by(username=data['username']).first()

        if not user or not check_password_hash(user.password_hash, data['password']):
            return jsonify({'message': 'Invalid username or password'}), 401

        if not user.email_verified:
            return jsonify({'message': 'Please verify your email before logging in'}), 401

        # Generate access token
        access_token = jwt.encode({
            'user_id': user.user_id,
            'exp': datetime.utcnow() + timedelta(minutes=15)  # Short lived access token
        }, current_app.config['SECRET_KEY'], algorithm="HS256")

        # Generate refresh token
        refresh_token = user.generate_refresh_token()
        user.refresh_token_expires_at = datetime.utcnow() + timedelta(days=7)
        db.session.commit()

        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email
            }
        })

    except Exception as e:
        return jsonify({'message': 'Login failed', 'error': str(e)}), 500

@auth_bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    refresh_token = request.json.get('refresh_token')
    if not refresh_token:
        return jsonify({'message': 'Refresh token is required'}), 400

    user = User.query.filter_by(refresh_token=refresh_token).first()
    if not user or user.refresh_token_expires_at < datetime.utcnow():
        return jsonify({'message': 'Invalid or expired refresh token'}), 401

    # Generate new access token
    access_token = jwt.encode({
        'user_id': user.user_id,
        'exp': datetime.utcnow() + timedelta(hours=250)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'access_token': access_token})

# Test protected route
@auth_bp.route('/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({'message': f'Hello {current_user.username}!'})

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    try:
        # Xóa refresh token của user
        current_user.refresh_token = None
        current_user.refresh_token_expires_at = None
        db.session.commit()
        
        return jsonify({'message': 'Logged out successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error during logout', 'error': str(e)}), 500