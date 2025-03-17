# app.py
from flask import Flask,render_template
from config import Config
from routes.images import images_bp
from routes.search import search_bp
from routes.auth import auth_bp
from database.db import init_db
import os
import sys
import signal

def signal_handler(sig, frame):
    """Handler for graceful shutdown"""
    print("\nSaving FAISS index before exit...")
    from services.ai_service import ai_service
    ai_service.save_faiss_index("faiss_index.bin")
    print("FAISS index saved. Exiting...")
    sys.exit(0)
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Đăng ký thư mục lưu ảnh
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads') 
    
    # Đảm bảo thư mục tồn tại
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Khởi tạo database (SQLAlchemy)
    init_db(app)

    # Đăng ký các blueprint
    app.register_blueprint(images_bp, url_prefix='/api/images')
    app.register_blueprint(search_bp, url_prefix='/api/search')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    @app.route('/login')
    def login():
        return render_template('login.html')

    @app.route('/register')
    def register():
        return render_template('register.html')
    @app.route('/')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/images') 
    def my_images():
        return render_template('image.html')
    
    @app.route('/search')
    def search():
        return render_template('search.html')
    return app

if __name__ == '__main__':
    flask_app = create_app()
    flask_app.run(host="0.0.0.0", port=5000, debug=True)
