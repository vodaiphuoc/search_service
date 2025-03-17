import torch
from PIL import Image
import numpy as np
from transformers import CLIPProcessor, CLIPModel
import faiss
import threading
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

class AIService:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AIService, cls).__new__(cls)
                    cls._instance.model = None
                    cls._instance.processor = None
                    cls._instance.index = None
                    # Nếu có GPU và đủ VRAM, dùng CUDA
                    cls._instance.device = "cuda" if torch.cuda.is_available() else "cpu"
        return cls._instance

    def load_model(self):
        """Lazy load CLIP model"""
        if self.model is None:
            try:
                # Dùng mô hình lớn hơn: clip-vit-large-patch14
                self.model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14", revision="main")
                self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14", revision="main")
                self.model.to(self.device)
                print(f"CLIP model (ViT-L/14) loaded successfully on {self.device}")
            except Exception as e:
                print(f"Error loading CLIP model: {str(e)}")
                raise

    def get_image_embedding(self, image_path_or_object):
        """
        Generate embedding for an image (có thể là đường dẫn hoặc PIL.Image).
        """
        try:
            self.load_model()  # Ensure model is loaded
            
            # Nếu truyền vào là đường dẫn, mở ảnh bằng PIL
            if isinstance(image_path_or_object, str):
                image = Image.open(image_path_or_object).convert("RGB")
            else:
                image = image_path_or_object.convert("RGB")

            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            # Chuyển sang numpy, chuẩn hóa vector
            embedding = image_features.cpu().numpy()[0]
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            print(f"Error generating image embedding: {str(e)}")
            raise

    def get_text_embedding(self, text):
        """Generate embedding for text query"""
        try:
            self.load_model()  # Ensure model is loaded
            
            inputs = self.processor(
                text=[text],
                return_tensors="pt",
                padding=True,
                truncation=True,      # <-- Bắt buộc (quan trọng)
                max_length=77         # <-- Giới hạn của CLIP text encoder
            ).to(self.device)
                        
            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
            
            # Chuyển sang numpy, chuẩn hóa
            embedding = text_features.cpu().numpy()[0]
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            print(f"Error generating text embedding: {str(e)}")
            raise

    def init_faiss_index(self, dimension=768):
        """
        Initialize FAISS index với IndexIDMap (để lưu ID = image_id thật).
        Mặc định CLIP ViT-L/14 => 768 chiều
        """
        try:
            index_flat = faiss.IndexFlatIP(dimension)  # Inner product similarity
            self.index = faiss.IndexIDMap(index_flat)
            print("FAISS index (IDMap) initialized with dimension =", dimension)
        except Exception as e:
            print(f"Error initializing FAISS index: {str(e)}")
            raise

    def add_to_index(self, embedding, image_id):
        try:
            if self.index is None:
                self.init_faiss_index(dimension=embedding.shape[0])
            
            # Thêm embedding vào index
            embedding_f32 = embedding.reshape(1, -1).astype(np.float32)
            ids = np.array([image_id], dtype=np.int64)
            self.index.add_with_ids(embedding_f32, ids)
            
            # Lưu index ngay sau khi thêm
            self.save_faiss_index("faiss_index.bin")
            return True
        except Exception as e:
            print(f"Error adding to FAISS index: {str(e)}")
            raise
    def add_batch_to_index(self, embeddings, image_ids):
        """Thêm nhiều embeddings vào FAISS index cùng lúc"""
        try:
            if self.index is None:
                self.init_faiss_index(dimension=embeddings.shape[1])
            
            # Thêm tất cả embeddings vào index
            self.index.add_with_ids(embeddings, image_ids)
            
            # Lưu index sau khi thêm batch
            self.save_faiss_index("faiss_index.bin")
            return True
        except Exception as e:
            print(f"Error adding batch to FAISS index: {str(e)}")
            raise
    def search_similar(self, query_embedding, k=5):
        """Search for similar embeddings, trả về list (image_id, distance)"""
        try:
            if self.index is None or self.index.ntotal == 0:
                return []
            
            # Ép query_embedding sang float32
            query_embedding_f32 = query_embedding.reshape(1, -1).astype(np.float32)
            
            distances, ids = self.index.search(query_embedding_f32, min(k, self.index.ntotal))
            
            return list(zip(ids[0], distances[0]))
            
        except Exception as e:
            print(f"Error searching index: {str(e)}")
            raise
        
    def save_faiss_index(self, file_path):
        """
        Lưu FAISS index ra file.
        Giúp chúng ta không bị mất index khi server dừng.
        """
        try:
            if self.index is not None:
                faiss.write_index(self.index, file_path)
                print(f"FAISS index saved to {file_path}")
        except Exception as e:
            print(f"Error saving FAISS index: {str(e)}")

    def load_faiss_index(self, file_path):
        """
        Tải FAISS index từ file. Nếu file không tồn tại, tạo index trống.
        """
        try:
            if os.path.exists(file_path):
                self.index = faiss.read_index(file_path)
                print(f"FAISS index loaded from {file_path}")
            else:
                print(f"No FAISS index file found at {file_path}. Initializing a new index...")
                self.init_faiss_index()
        except Exception as e:
            print(f"Error loading FAISS index: {str(e)}")
            # Nếu có lỗi, khởi tạo index rỗng
            self.init_faiss_index()

    def load_embeddings_from_db(self, session):
        """
        Đọc tất cả embedding từ DB và thêm vào FAISS index.
        Dùng khi ta không có sẵn file FAISS hoặc muốn đồng bộ lại từ DB.
        """
        try:
            from models import ImageEmbedding  # import tại đây để tránh vòng lặp import

            embeddings = session.query(ImageEmbedding).all()
            if not embeddings:
                print("No embeddings found in the database.")
                return

            # Khởi tạo lại FAISS index
            self.init_faiss_index()

            for emb in embeddings:
                vector = np.frombuffer(emb.embedding_vector, dtype=np.float32)
                self.add_to_index(vector, emb.image_id)

            print(f"Loaded {len(embeddings)} embeddings from the database into FAISS index.")
        except Exception as e:
            print(f"Error loading embeddings from database: {str(e)}")
            raise


# Singleton instance
ai_service = AIService()
