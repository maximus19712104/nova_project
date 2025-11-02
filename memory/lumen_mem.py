import sqlite3
import json
from datetime import datetime

class LumenMemory:
    def __init__(self, db_path="memory/lumen_memory.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lumen_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE,
                insight_text TEXT,
                trace_refs TEXT,
                activation_meta TEXT,
                result_outcome TEXT,
                human_rating INTEGER,
                confidence REAL,
                strategy_used TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    def store_decision(self, request_id, decision_data, nova_result, orvyn_result):
        """Сохранение решения Lumen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            trace_refs = {
                "nova_steps": nova_result["payload"]["logic_tree"]["steps"],
                "orvyn_analogies": [a["snippet"] for a in orvyn_result["payload"]["analogies"]]
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO lumen_memory 
                (request_id, insight_text, trace_refs, activation_meta, 
                 confidence, strategy_used, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request_id,
                decision_data["insight"],
                json.dumps(trace_refs),
                json.dumps(decision_data["meta"]),
                decision_data["confidence"],
                decision_data["meta"]["strategy"],
                datetime.utcnow(),
                datetime.utcnow()
            ))
            
            conn.commit()
        except Exception as e:
            print(f"Ошибка сохранения в Lumen memory: {e}")
        finally:
            conn.close()

    def get_learning_data(self, limit=100):
        """Получение данных для обучения"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT insight_text, activation_meta, human_rating, confidence, strategy_used
            FROM lumen_memory 
            WHERE human_rating IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        learning_data = []
        for row in results:
            learning_data.append({
                "insight": row[0],
                "meta": json.loads(row[1]),
                "rating": row[2],
                "confidence": row[3],
                "strategy": row[4]
            })
        
        return learning_data
