# utils/file_handler.py
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image as PILImage
import imghdr
import posixpath 

class FileHandler:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_FILE_SIZE = 200 * 1024 * 1024  # 5MB

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in FileHandler.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_image(file):
        # Kiểm tra nếu tệp tồn tại
        if not file:
            return False, "No file uploaded"

        # Kiểm tra kích thước tệp
        if len(file.read()) > FileHandler.MAX_FILE_SIZE:
            file.seek(0)  # Đặt lại con trỏ tệp
            return False, "File size exceeds 5MB"
        file.seek(0)  # Đặt lại con trỏ tệp

        # Kiểm tra phần mở rộng tệp
        if not FileHandler.allowed_file(file.filename):
            return False, "File type not allowed. Allowed types: png, jpg, jpeg, gif"

        # Xác minh tệp thực sự là một hình ảnh
        try:
            img = PILImage.open(file)
            img.verify()
            file.seek(0)  # Đặt lại con trỏ tệp sau khi xác minh
            return True, "File is valid"
        except Exception:
            return False, "Invalid image file"

    @staticmethod
    def save_file(file, upload_folder):
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{original_filename}"
        
        # Create year/month based directory structure
        year_month = datetime.now().strftime('%Y/%m')
        
        # Sử dụng posixpath để đảm bảo forward slashes
        save_path = os.path.join(upload_folder, year_month)
        os.makedirs(save_path, exist_ok=True)
        
        # Full path để save file
        file_path = os.path.join(save_path, filename)
        file.save(file_path)
        
        # Return relative path với forward slashes
        return posixpath.join(year_month, filename)


    @staticmethod
    def delete_file(file_path, upload_folder):
        try:
            full_path = os.path.join(upload_folder, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                # Cố gắng xóa các thư mục trống
                dir_path = os.path.dirname(full_path)
                while dir_path != upload_folder:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        dir_path = os.path.dirname(dir_path)
                    else:
                        break
                return True
            return False
        except Exception:
            return False