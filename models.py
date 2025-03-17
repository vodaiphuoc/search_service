# models/models.py
from database.db import db

# models/models.py
from database.db import db
import secrets

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)
    refresh_token = db.Column(db.String(100), unique=True)
    refresh_token_expires_at = db.Column(db.DateTime)

    images = db.relationship("Image", back_populates="user", cascade="all, delete-orphan")

    def generate_verification_token(self):
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token

    def generate_refresh_token(self):
        self.refresh_token = secrets.token_urlsafe(32)
        return self.refresh_token
        
class Image(db.Model):
    __tablename__ = 'images'
    image_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500), nullable=False)  
    uploaded_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", back_populates="images")
    embeddings = db.relationship("ImageEmbedding", back_populates="image", cascade="all, delete-orphan")

class ImageEmbedding(db.Model):
    __tablename__ = 'image_embeddings'
    embedding_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.image_id'), nullable=False)
    embedding_vector = db.Column(db.LargeBinary, nullable=False)
    model = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    image = db.relationship("Image", back_populates="embeddings")

