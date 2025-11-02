import redis
import json
import asyncio
import time
import numpy as np  # Добавлен импорт numpy
from memory.nova_mem import NovaMemory
from utils.logger import get_nova_logger
from utils.embeddings import get_embedding_manager

class NovaCore:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.memory = NovaMemory()
        self.is_running = False
        self.logger = get_nova_logger()
        self.embedding_manager = get_embedding_manager()
        
        self.logger.log_system_event("initialized", "nova_core", "Nova core initialized successfully")

    async def process_request(self, request_data):
        """Обработка запроса Nova"""
        request_id = request_data["request_id"]
        query = request_data["query"]
        context = request_data.get("context", {})
        
        start_time = time.time()
        self.logger.log_request(request_id, request_data.get("user_id", "unknown"), query, context, request_data.get("mode", "balanced"))
        
        try:
            logic_tree = self._build_logic_tree(query, context)
            candidate_actions = self._generate_candidate_actions(query, logic_tree)
            confidence = self._calculate_confidence(query, candidate_actions)
            
            result = {
                "request_id": request_id,
                "core": "nova",
                "payload": {
                    "logic_tree": logic_tree,
                    "candidate_actions": candidate_actions,
                    "confidence": confidence
                }
            }
            
            processing_time = time.time() - start_time
            
            self.memory.store_result(request_id, result)
            self.redis_client.xadd("cognitive_bus:core_results", result)
            
            self.logger.log_core_processing("nova", request_id, processing_time, 
                                          len(candidate_actions), confidence)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.log_error("processing_error", f"Error processing request {request_id}", 
                                request_id, e)
            # Возвращаем заглушку вместо исключения
            return self._create_fallback_result(request_id, query)

    def _build_logic_tree(self, query: str, context: dict) -> dict:
        """Построение дерева логики"""
        main_concept = self._extract_main_concept(query)
        related_concepts = self._find_related_concepts(main_concept)
        
        logic_tree = {
            "root": main_concept,
            "query_analysis": {
                "complexity": self._assess_query_complexity(query),
                "domain": self._identify_domain(query),
                "constraints": context
            },
            "steps": [
                f"Анализ ключевого концепта: {main_concept}",
                f"Идентификация связанных концептов: {', '.join(related_concepts[:3])}",
                "Построение причинно-следственных связей",
                "Генерация гипотез решения"
            ],
            "related_concepts": related_concepts
        }
        
        return logic_tree

    def _extract_main_concept(self, query: str) -> str:
        """Извлечение основного концепта из запроса"""
        concepts = ["экономия", "оптимизация", "улучшение", "сокращение", "повышение"]
        try:
            query_embedding = self.embedding_manager.encode_texts([query])[0]
            concept_embeddings = self.embedding_manager.encode_texts(concepts)
            
            similarities = np.dot(concept_embeddings, query_embedding)
            best_match_idx = np.argmax(similarities)
            
            return concepts[best_match_idx]
        except:
            return "анализ"  # Fallback

    def _find_related_concepts(self, main_concept: str) -> List[str]:
        """Поиск связанных концептов"""
        # Упрощенная реализация для MVP
        concept_map = {
            "экономия": ["расходы", "бюджет", "ресурсы", "затраты"],
            "оптимизация": ["эффективность", "производительность", "процессы"],
            "улучшение": ["качество", "результаты", "показатели"],
            "сокращение": ["уменьшение", "минимизация", "снижение"],
            "повышение": ["рост", "увеличение", "улучшение"]
        }
        return concept_map.get(main_concept, ["решение", "подход", "метод"])

    def _assess_query_complexity(self, query: str) -> str:
        """Оценка сложности запроса"""
        word_count = len(query.split())
        if word_count > 15:
            return "high"
        elif word_count > 8:
            return "medium"
        return "low"

    def _identify_domain(self, query: str) -> str:
        """Идентификация домена запроса"""
        domains = {
            "water": ["вода", "водный", "расход воды"],
            "energy": ["энергия", "электричество", "энергосбережение"],
            "cost": ["стоимость", "бюджет", "расходы"],
            "productivity": ["продуктивность", "эффективность", "результативность"]
        }
        
        query_lower = query.lower()
        for domain, keywords in domains.items():
            if any(keyword in query_lower for keyword in keywords):
                return domain
        return "general"

    def _generate_candidate_actions(self, query: str, logic_tree: dict) -> List[str]:
        """Генерация кандидатных действий"""
        domain = logic_tree["query_analysis"]["domain"]
        main_concept = logic_tree["root"]
        
        actions = {
            "water": [
                f"Внедрение систем контроля расхода воды",
                f"Оптимизация процессов использования воды", 
                f"Модернизация водосберегающего оборудования"
            ],
            "energy": [
                f"Внедрение энергоэффективных технологий",
                f"Оптимизация режимов энергопотребления",
                f"Использование возобновляемых источников энергии"
            ],
            "cost": [
                f"Анализ и оптимизация текущих расходов",
                f"Внедрение системы бюджетного контроля",
                f"Поиск альтернативных поставщиков и решений"
            ],
            "general": [
                f"Разработка стратегии {main_concept}",
                f"Внедрение системы мониторинга и контроля",
                f"Оптимизация текущих процессов и процедур"
            ]
        }
        
        return actions.get(domain, actions["general"])

    def _calculate_confidence(self, query: str, actions: List[str]) -> float:
        """Расчет уверенности в результатах"""
        # Упрощенный расчет на основе длины запроса и количества действий
        base_confidence = min(len(query) / 100, 0.8)  # Максимум 0.8
        action_bonus = len(actions) * 0.05  # Бонус за количество действий
        return min(base_confidence + action_bonus, 0.95)  # Максимум 0.95

    def _create_fallback_result(self, request_id: str, query: str) -> dict:
        """Создание fallback результата при ошибке"""
        return {
            "request_id": request_id,
            "core": "nova",
            "payload": {
                "logic_tree": {
                    "root": "анализ",
                    "steps": ["Базовый анализ запроса", "Формирование рекомендаций"],
                    "query_analysis": {"complexity": "unknown", "domain": "general"}
                },
                "candidate_actions": [f"Базовое решение для: {query}"],
                "confidence": 0.3
            }
        }

    async def start_listening(self):
        """Запуск прослушивания Cognitive Bus"""
        self.is_running = True
        self.logger.log_system_event("started", "nova_core", "Nova core started listening")
        
        while self.is_running:
            try:
                messages = self.redis_client.xread(
                    {"cognitive_bus:requests": 0}, 
                    count=1, 
                    block=5000
                )
                
                if messages:
                    for stream, message_list in messages:
                        for message_id, message_data in message_list:
                            await self.process_request(message_data)
                            
            except Exception as e:
                self.logger.log_error("listening_error", "Error in listening loop", exception=e)
                await asyncio.sleep(1)

    def stop(self):
        """Остановка сервиса"""
        self.is_running = False
        self.logger.log_system_event("stopped", "nova_core", "Nova core stopped")

if __name__ == "__main__":
    nova = NovaCore()
    asyncio.run(nova.start_listening())
