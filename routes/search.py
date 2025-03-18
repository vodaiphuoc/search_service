# routes/search.py
from flask import Blueprint, request, jsonify, current_app
from services.ai_service import ai_service
from models import Image, ImageEmbedding
from routes.auth import token_required
import numpy as np
from PIL import Image as PILImage

search_bp = Blueprint('search', __name__)

@search_bp.route('/text', methods=['POST'])
@token_required
def search_by_text(current_user):
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'message': 'No search query provided'}), 400

        # Lấy tham số phân trang
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)

        # Tạo embedding cho text
        query_embedding = ai_service.get_text_embedding(data['query'])

        # Tìm tất cả ảnh tương tự
        all_results = ai_service.search_similar(query_embedding, k=1)  # Lấy nhiều kết quả hơn
        print('all_results: ', all_results)
        if not all_results:
            return jsonify({
                'results': [],
                'pagination': {
                    'total': 0,
                    'pages': 0,
                    'current_page': page,
                    'per_page': per_page
                }
            })

        # Lọc kết quả theo user_id
        filtered_results = []
        for idx, score in all_results:
            image = Image.query.get(int(idx))
            print('image: ', image)
            print('check id: ',image.user_id, current_user.user_id)

            if image and image.user_id == current_user.user_id:
                filtered_results.append({
                    'image_id': image.image_id,
                    'title': image.title,
                    'description': image.description,
                    'file_path': image.file_path,
                    'similarity_score': float(score)
                })

        # Tính toán phân trang
        total = len(filtered_results)
        total_pages = (total + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        print('total: ', total)
        return jsonify({
            'results': filtered_results[start_idx:end_idx],
            'pagination': {
                'total': total,
                'pages': total_pages,
                'current_page': page,
                'per_page': per_page
            }
        })

    except Exception as e:
        return jsonify({'message': 'Error performing search', 'error': str(e)}), 500
@search_bp.route('/image', methods=['POST'])
@token_required
def search_by_image(current_user):
    try:
        if 'file' not in request.files:
            return jsonify({'message': 'No image file uploaded'}), 400

        # Lấy tham số phân trang
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)

        file = request.files['file']
        uploaded_image = PILImage.open(file)

        # Tạo embedding cho ảnh upload
        query_embedding = ai_service.get_image_embedding(uploaded_image)

        # Tìm ảnh tương tự
        all_results = ai_service.search_similar(query_embedding, k=100)  # Lấy nhiều kết quả hơn
        if not all_results:
            return jsonify({
                'results': [],
                'pagination': {
                    'total': 0,
                    'pages': 0,
                    'current_page': page,
                    'per_page': per_page
                }
            })

        # Lọc kết quả theo user_id và similarity threshold
        similarity_threshold = 0.20
        filtered_results = []

        for idx, score in all_results:
            image = Image.query.get(int(idx))
            if image and image.user_id == current_user.user_id:
                if score >= similarity_threshold:
                    filtered_results.append({
                        'image_id': image.image_id,
                        'title': image.title,
                        'description': image.description,
                        'file_path': image.file_path,
                        'similarity_score': float(score)
                    })

        # Tính toán phân trang
        total = len(filtered_results)
        total_pages = (total + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        return jsonify({
            'results': filtered_results[start_idx:end_idx],
            'pagination': {
                'total': total,
                'pages': total_pages,
                'current_page': page,
                'per_page': per_page
            }
        })

    except Exception as e:
        return jsonify({'message': 'Error performing search', 'error': str(e)}), 500