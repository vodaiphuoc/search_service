# routes/images.py
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from database.db import db
from models import Image
from utils.file_handler import FileHandler
from routes.auth import token_required
import os
from services.task_handler import task_handler

images_bp = Blueprint('images', __name__)

# routes/images.py

@images_bp.route('/', methods=['GET'])
@token_required 
def list_images(current_user):
    try:
        # Get page and limit params, default limit=5
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)  # Mặc định 5 ảnh
        
        # Get paginated images for current user
        images = Image.query.filter_by(user_id=current_user.user_id)\
                           .order_by(Image.uploaded_at.desc())\
                           .paginate(page=page, per_page=per_page)
        
        return jsonify({
            'images': [{
                'image_id': img.image_id,
                'title': img.title,
                'description': img.description,
                'file_path': img.file_path,
                'uploaded_at': img.uploaded_at.isoformat()
            } for img in images.items],
            'pagination': {
                'total': images.total,
                'pages': images.pages,
                'current_page': images.page,
                'per_page': per_page
            }
        })
    except Exception as e:
        return jsonify({'message': 'Error fetching images', 'error': str(e)}), 500

@images_bp.route('/', methods=['POST'])
@token_required
def upload_image(current_user):
    try:
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        # Validate file
        is_valid, message = FileHandler.validate_image(file)
        if not is_valid:
            return jsonify({'message': message}), 400
        
        # Get image metadata
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        
        # Save file
        upload_folder = current_app.config['UPLOAD_FOLDER']
        relative_path = FileHandler.save_file(file, upload_folder)
        
        # Create database record
        new_image = Image(
            user_id=current_user.user_id,
            title=title,
            description=description,
            file_path=relative_path
        )
        
        db.session.add(new_image)
        db.session.commit()
        
        task_handler.add_task(
            'generate_embedding',
            app=current_app._get_current_object(),
            image_id=new_image.image_id
        )
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'image': {
                'image_id': new_image.image_id,
                'title': new_image.title,
                'description': new_image.description,
                'file_path': new_image.file_path,
                'uploaded_at': new_image.uploaded_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error uploading image', 'error': str(e)}), 500

@images_bp.route('/<int:image_id>', methods=['GET'])
@token_required
def get_image(current_user, image_id):
    try:
        image = Image.query.filter_by(
            image_id=image_id,
            user_id=current_user.user_id
        ).first()
        
        if not image:
            return jsonify({'message': 'Image not found'}), 404
            
        return jsonify({
            'image_id': image.image_id,
            'title': image.title,
            'description': image.description,
            'file_path': image.file_path,
            'uploaded_at': image.uploaded_at.isoformat()
        })
        
    except Exception as e:
        return jsonify({'message': 'Error fetching image', 'error': str(e)}), 500

@images_bp.route('/<int:image_id>', methods=['PUT'])
@token_required
def update_image(current_user, image_id):
    try:
        image = Image.query.filter_by(
            image_id=image_id,
            user_id=current_user.user_id
        ).first()
        
        if not image:
            return jsonify({'message': 'Image not found'}), 404
            
        # Update metadata
        if 'title' in request.form:
            image.title = request.form['title']
        if 'description' in request.form:
            image.description = request.form['description']
            
        # Handle file update if present
        if 'file' in request.files:
            file = request.files['file']
            
            # Validate new file
            is_valid, message = FileHandler.validate_image(file)
            if not is_valid:
                return jsonify({'message': message}), 400
                
            # Delete old file
            upload_folder = current_app.config['UPLOAD_FOLDER']
            FileHandler.delete_file(image.file_path, upload_folder)
            
            # Save new file
            relative_path = FileHandler.save_file(file, upload_folder)
            image.file_path = relative_path
            
        db.session.commit()
        
        return jsonify({
            'message': 'Image updated successfully',
            'image': {
                'image_id': image.image_id,
                'title': image.title,
                'description': image.description,
                'file_path': image.file_path,
                'uploaded_at': image.uploaded_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error updating image', 'error': str(e)}), 500

@images_bp.route('/<int:image_id>', methods=['DELETE'])
@token_required
def delete_image(current_user, image_id):
    try:
        image = Image.query.filter_by(
            image_id=image_id,
            user_id=current_user.user_id
        ).first()
        
        if not image:
            return jsonify({'message': 'Image not found'}), 404
            
        # Delete file from storage
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not FileHandler.delete_file(image.file_path, upload_folder):
            return jsonify({'message': 'Error deleting image file'}), 500
            
        # Delete database record
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({'message': 'Image deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error deleting image', 'error': str(e)}), 500

@images_bp.route('/file/<path:filename>')  
def serve_image(filename):  # Bỏ @token_required và current_user
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        return jsonify({'message': 'Error serving image', 'error': str(e)}), 500
@images_bp.route('/upload/multiple', methods=['POST'])
@token_required
def upload_multiple_images(current_user):
    try:
        uploaded_files = request.files.getlist('file')
        if not uploaded_files:
            return jsonify({'message': 'No files uploaded'}), 400

        results = []
        upload_folder = current_app.config['UPLOAD_FOLDER']

        # 1. Xử lý tất cả file uploads trước
        for file in uploaded_files:
            is_valid, msg = FileHandler.validate_image(file)
            if not is_valid:
                return jsonify({'message': f'File invalid: {msg}'}), 400

            relative_path = FileHandler.save_file(file, upload_folder)
            
            new_image = Image(
                user_id=current_user.user_id,
                title="Multi-upload",
                description="Uploaded in batch",
                file_path=relative_path
            )
            db.session.add(new_image)
            results.append(new_image)

        # 2. Commit tất cả records một lần
        db.session.commit()

        # 3. Tạo tasks cho batch processing
        for image in results:
            task_handler.add_task(
                'generate_embedding',
                app=current_app._get_current_object(),
                image_id=image.image_id
            )

        return jsonify({
            'message': 'Images uploaded successfully. Processing embeddings...',
            'uploaded_count': len(results),
            'images': [{
                'image_id': img.image_id,
                'file_path': img.file_path,
                'title': img.title,
                'description': img.description,
                'uploaded_at': img.uploaded_at.isoformat()
            } for img in results]
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error uploading images', 'error': str(e)}), 500
    """
    Cho phép upload nhiều ảnh cùng lúc.
    Client có thể gửi dưới dạng multipart/form-data:
        files: [file1, file2, ...]
        (kèm các trường khác, nếu cần)
    """
    try:
        # Lấy danh sách file từ request
        # - Tùy vào form data bên client, có thể là 'file' hoặc 'file[]'
        uploaded_files = request.files.getlist('file')
        if not uploaded_files:
            return jsonify({'message': 'No files uploaded'}), 400

        # Nếu bạn muốn cho phép gửi "title" & "description" riêng
        # cho toàn bộ batch, có thể lấy từ request.form.get()
        # title = request.form.get('title', '')
        # description = request.form.get('description', '')

        # Hoặc nếu muốn cho mỗi ảnh có title/description riêng,
        # bạn cần gửi kèm metadata dưới dạng JSON hay name="file[0].title" ...
        # Ở ví dụ đơn giản này, mình chỉ demo upload nhiều file thôi.

        results = []
        upload_folder = current_app.config['UPLOAD_FOLDER']

        for file in uploaded_files:
            # 1) Kiểm tra hợp lệ
            is_valid, msg = FileHandler.validate_image(file)
            if not is_valid:
                return jsonify({'message': f'File invalid: {msg}'}), 400

            # 2) Lưu file
            relative_path = FileHandler.save_file(file, upload_folder)

            # 3) Tạo record trong DB
            new_image = Image(
                user_id=current_user.user_id,
                title="Multi-upload",           # tùy bạn gắn title mặc định
                description="Uploaded in batch",# mô tả mặc định
                file_path=relative_path
            )
            db.session.add(new_image)
            db.session.commit()

            # 4) Tạo task sinh embedding
            task_handler.add_task(
                'generate_embedding',
                app=current_app._get_current_object(),
                image_id=new_image.image_id
            )

            # 5) Thêm vào kết quả
            results.append({
                'image_id': new_image.image_id,
                'file_path': new_image.file_path,
                'title': new_image.title,
                'description': new_image.description,
                'uploaded_at': new_image.uploaded_at.isoformat()
            })

        # Trả về mảng ảnh đã upload
        return jsonify({
            'message': 'All images uploaded successfully',
            'uploaded_count': len(results),
            'images': results
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Error uploading images', 'error': str(e)}), 500