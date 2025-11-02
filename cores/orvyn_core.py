import redis
import json
import asyncio
import numpy as np
from memory.orvyn_mem import OrvynMemory
from utils.logger import get_orvyn_logger
from utils.embeddings import get_embedding_manager

class OrvynCore:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.memory = OrvynMemory()
        self.is_running = False
        self.logger = get_orvyn_logger()
        self.embedding_manager = get_embedding_manager()
        
        # Инициализация с использованием embedding manager
        self.analogy_corpus = [
            "water conservation through rainwater harvesting",
            "energy saving with smart thermostats",
            "cost reduction via process optimization",
            # ... остальной корпус ...
        ]
        
        self.logger.log_system_event("initialized", "orvyn_core", 
                                   f"Orvyn core initialized with {len(self.analogy_corpus)} analogies")

    def find_analogies(self, query: str, top_k: int = 3):
        """Поиск аналогий с использованием embedding manager"""
        try:
            results = self.embedding_manager.batch_similarity([query], self.analogy_corpus, top_k)
            analogies = []
            
            for item in results[0]:
                analogies.append({
                    "snippet": item["corpus_text"],
                    "similarity": item["similarity"],
                    "tags": self._extract_tags(item["corpus_text"])
                })
            
            self.logger.debug(f"Found {len(analogies)} analogies for query", 
                            {"query": query, "analogies_count": len(analogies)})
            return analogies
            
        except Exception as e:
            self.logger.log_error("analogy_search_error", "Error finding analogies", 
                                exception=e, context={"query": query})
            return []
