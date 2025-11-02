import sqlite3
import json
import numpy as np
from datetime import datetime

class OrvynMemory:
    def __init__(self, db_path="memory/orvyn_memory.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orvyn_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE,
                query_text TEXT,
                snippet_text TEXT,
                embedding BLOB,
                analogies_tags TEXT,
                context_tags TEXT,
                similarity_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                relevance_score REAL DEFAULT 1.0,
                usage_count INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()

    def store_result(self, request_id, result_data, query):
        """Сохранение результатов Orvyn"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for analogy in result_data["payload"]["analogies"]:
                cursor.execute('''
                    INSERT INTO orvyn_memory 
                    (request_id, query_text, snippet_text, analogies_tags, 
                     similarity_score, relevance_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    f"{request_id}_{analogy['snippet'][:10]}",
                    query,
                    analogy['snippet'],
                    json.dumps(analogy['tags']),
                    analogy['similarity'],
                    result_data["payload"]["confidence"]
                ))
            
            conn.commit()
        except Exception as e:
            print(f"Ошибка сохранения в Orvyn memory: {e}")
        finally:
            conn.close()
