# database/db.py
import os
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from services.ai_service import ai_service
import atexit

db = SQLAlchemy()

def init_db(app):
    # Đảm bảo thư mục instance tồn tại
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    
    # Khởi tạo app với SQLAlchemy
    db.init_app(app)
    
    # Tạo database file và tables
    with app.app_context():
        # Tạo tất cả tables được định nghĩa trong models
        db.create_all()
        
        # Log để debug
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')        
        # Kiểm tra database đã được tạo
        if os.path.exists(db_path):
            print("Database file created successfully!")
        else:
            print("Error: Database file was not created!")
        
        # Đường dẫn file FAISS index
        faiss_file_path = "faiss_index.bin"
        
        # 1) Tải FAISS index từ file
        ai_service.load_faiss_index(faiss_file_path)
        
        # 2) Nếu index rỗng, thì nạp embedding từ DB
        if ai_service.index is None or ai_service.index.ntotal == 0:
            ai_service.load_embeddings_from_db(db.session)
        
        @atexit.register
        def save_faiss_on_exit():
            faiss_file_path = "faiss_index.bin"
            ai_service.save_faiss_index(faiss_file_path)