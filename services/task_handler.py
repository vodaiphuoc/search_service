# services/task_handler.py
from threading import Thread
from queue import Queue
import time
from database.db import db
from models import Image, ImageEmbedding
from services.ai_service import ai_service
import numpy as np
import os
from queue import Queue, Empty

class TaskHandler:
    def __init__(self):
        self.task_queue = Queue()
        self.batch_size = 100
        self.batch_timeout = 10
        self.is_running = True
        self.worker_thread = Thread(target=self._process_tasks)
        self.worker_thread.daemon = True
        self.worker_thread.start()

        # Thêm thread backup định kỳ
        self.backup_thread = Thread(target=self._periodic_backup)
        self.backup_thread.daemon = True
        self.backup_thread.start()

        
    def _periodic_backup(self):
        while self.is_running:
            try:
                # Backup mỗi 5 phút
                time.sleep(300)
                from services.ai_service import ai_service
                ai_service.save_faiss_index("faiss_index.bin")
                print("Periodic FAISS index backup completed")
            except Exception as e:
                print(f"Error in periodic backup: {str(e)}")
          
    def _process_tasks(self):
        while self.is_running:
            try:
                batch = []
                batch_start = time.time()

                while len(batch) < self.batch_size and \
                      time.time() - batch_start < self.batch_timeout:
                    try:
                        task = self.task_queue.get(timeout=0.5)
                        batch.append(task)
                    except Empty:  # Sử dụng Empty thay vì Queue.Empty
                        if batch:
                            break
                        continue

                if batch:
                    self._handle_batch_embedding(batch)
                    
            except Exception as e:
                print(f"Error processing batch: {str(e)}")
    def _handle_batch_embedding(self, batch):
        try:
            app = batch[0]['app']  # Lấy app context từ task đầu tiên
            
            with app.app_context():
                embeddings = []
                image_ids = []

                # 1. Tạo embeddings cho cả batch
                for task in batch:
                    image_id = task['image_id']
                    image = Image.query.get(image_id)
                    if not image:
                        continue
                        
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.file_path)
                    embedding = ai_service.get_image_embedding(image_path)
                    
                    embeddings.append(embedding)
                    image_ids.append(image_id)

                if not embeddings:
                    return

                # 2. Lưu vào database trong một transaction
                image_embedding_objects = []
                for idx, image_id in enumerate(image_ids):
                    image_embedding = ImageEmbedding(
                        image_id=image_id,
                        embedding_vector=embeddings[idx].tobytes(),
                        model='clip-vit-large-patch14'
                    )
                    image_embedding_objects.append(image_embedding)

                db.session.bulk_save_objects(image_embedding_objects)
                db.session.commit()

                # 3. Thêm vào FAISS index trong một lần
                embeddings_array = np.vstack(embeddings).astype(np.float32)
                ids_array = np.array(image_ids, dtype=np.int64)
                ai_service.add_batch_to_index(embeddings_array, ids_array)

                print(f"Processed batch of {len(batch)} images")

        except Exception as e:
            db.session.rollback()
            print(f"Error processing embedding batch: {str(e)}")
    def _handle_embedding_generation(self, task):
        try:
            app = task['app']
            image_id = task['image_id']
            
            with app.app_context():
                # Lấy image từ DB
                image = Image.query.get(image_id)
                if not image:
                    return
                
                # Tạo embedding
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.file_path)
                embedding = ai_service.get_image_embedding(image_path)
                
                # Lưu embedding vào DB
                image_embedding = ImageEmbedding(
                    image_id=image_id,
                    embedding_vector=embedding.tobytes(),
                    model='clip-vit-large-patch14'
                )
                
                db.session.add(image_embedding)
                db.session.commit()
                
                # Thêm vào Faiss index
                ai_service.add_to_index(embedding, image_id)
                
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")

    def add_task(self, task_type, **kwargs):
        self.task_queue.put({'type': task_type, **kwargs})

    def stop(self):
        self.is_running = False
        self.worker_thread.join()

# Singleton instance
task_handler = TaskHandler()
