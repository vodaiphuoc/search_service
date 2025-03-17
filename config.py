# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Lấy đường dẫn tới thư mục hiện tại
basedir = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'my_secret_key')
    
    # Chỉ định đường dẫn SQLite rõ ràng
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        f'sqlite:///{basedir}/instance/app.db'
    )
    print(f"Database URI: {SQLALCHEMY_DATABASE_URI}")   
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 5MB limit
    
    # Email configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    # Load environment variables from .env file
    load_dotenv()
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')