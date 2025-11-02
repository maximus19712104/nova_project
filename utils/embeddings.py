import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import json
import pickle
from typing import List, Dict, Any, Union, Optional
import logging
from pathlib import Path

class EmbeddingManager:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', cache_dir: str = "cache/embeddings"):
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = self._load_model()
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        self.embedding_cache = {}
        self.faiss_index = None
        self.indexed_texts = []  # Добавлено отсутствующее поле
        
        logging.info(f"EmbeddingManager initialized with model: {model_name}, dim: {self.embedding_dim}")

    def _load_model(self):
        """Загрузка модели с кэшированием"""
        model_cache_file = self.cache_dir / f"{self.model_name.replace('/', '_')}.pkl"
        
        try:
            if model_cache_file.exists():
                with open(model_cache_file, 'rb') as f:
                    model = pickle.load(f)
                logging.info(f"Model loaded from cache: {model_cache_file}")
            else:
                model = SentenceTransformer(self.model_name)
                with open(model_cache_file, 'wb') as f:
                    pickle.dump(model, f)
                logging.info(f"Model downloaded and cached: {model_cache_file}")
            
            return model
        except Exception as e:
            logging.error(f"Error loading model {self.model_name}: {e}")
            return SentenceTransformer('all-MiniLM-L6-v2')

    def encode_texts(self, texts: List[str], batch_size: int = 32, 
                    normalize: bool = True, cache_key: Optional[str] = None) -> np.ndarray:
        if not texts:
            return np.array([])
        
        if cache_key and cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=normalize
            )
            
            if cache_key:
                self.embedding_cache[cache_key] = embeddings
                
            return embeddings
            
        except Exception as e:
            logging.error(f"Error encoding texts: {e}")
            return np.random.randn(len(texts), self.embedding_dim).astype(np.float32)

    # ... остальные методы остаются без изменений ...

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Вычисление косинусной схожести между двумя векторами"""
    try:
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
    except Exception:
        return 0.0

def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """Нормализация эмбеддингов к единичной длине"""
    try:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # Избегаем деления на ноль
        return embeddings / norms
    except Exception:
        return embeddings

def create_embedding_batch_generator(texts: List[str], batch_size: int = 32):
    """Генератор для пакетной обработки больших наборов текстов"""
    for i in range(0, len(texts), batch_size):
        yield texts[i:i + batch_size]
