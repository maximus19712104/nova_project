import sqlite3
import json
from datetime import datetime

class NovaMemory:
    def __init__(self, db_path="memory/nova_memory.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Инициализация базы данных SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nova_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE,
                key TEXT,
                type TEXT,
                logic_tree TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def store_result(self, request_id, result_data):
        """Сохранение результата обработки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO nova_memory 
                (request_id, key, type, logic_tree, confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                request_id,
                result_data["payload"]["candidate_actions"][0],
                "rule",
                json.dumps(result_data["payload"]["logic_tree"]),
                result_data["payload"]["confidence"],
                json.dumps({"source": "nova_core"})
            ))
            
            conn.commit()
        except Exception as e:
            print(f"Ошибка сохранения в Nova memory: {e}")
        finally:
            conn.close()
