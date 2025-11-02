import redis
import json
import asyncio
import numpy as np
from sentence_transformers import SentenceTransformer
from memory.lumen_mem import LumenMemory
from datetime import datetime

class LumenCore:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.memory = LumenMemory()
        self.is_running = False
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Политики принятия решений
        self.policy_thresholds = {
            "alignment_high": 0.75,
            "alignment_mid": 0.45,
            "conflict_mid": 0.35
        }

    async def process_core_results(self, nova_result, orvyn_result):
        """Обработка результатов от Nova и Orvyn"""
        request_id = nova_result["request_id"]
        
        print(f"Lumen: Синтез результатов для {request_id}")
        
        # Вычисление метрик
        alignment_score = self.calculate_alignment_score(nova_result, orvyn_result)
        conflict_score = self.calculate_conflict_score(nova_result, orvyn_result)
        novelty_score = self.calculate_novelty_score(nova_result, orvyn_result)
        
        # Выбор стратегии
        strategy = self.select_strategy(alignment_score, conflict_score, novelty_score)
        
        # Генерация инсайта
        insight, rationale = self.generate_insight(
            nova_result, orvyn_result, strategy, 
            alignment_score, conflict_score
        )
        
        # Расчет уверенности
        confidence = self.calculate_confidence(
            alignment_score, conflict_score, novelty_score,
            nova_result["payload"]["confidence"],
            orvyn_result["payload"]["confidence"]
        )
        
        decision = {
            "request_id": request_id,
            "insight": insight,
            "meta": {
                "alignment_score": alignment_score,
                "conflict_score": conflict_score,
                "novelty_score": novelty_score,
                "strategy": strategy,
                "nova_confidence": nova_result["payload"]["confidence"],
                "orvyn_confidence": orvyn_result["payload"]["confidence"]
            },
            "rationale": rationale,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Сохранение в память Lumen
        self.memory.store_decision(request_id, decision, nova_result, orvyn_result)
        
        # Публикация решения
        self.redis_client.xadd("cognitive_bus:lumen_decisions", decision)
        
        return decision

    def calculate_alignment_score(self, nova_result, orvyn_result):
        """Вычисление скора выравнивания между Nova и Orvyn"""
        try:
            # Эмбеддинги ключевых элементов
            nova_text = " ".join(nova_result["payload"]["candidate_actions"])
            orvyn_text = " ".join([a["snippet"] for a in orvyn_result["payload"]["analogies"]])
            
            nova_embedding = self.model.encode([nova_text])
            orvyn_embedding = self.model.encode([orvyn_text])
            
            # Косинусная схожесть
            alignment = np.dot(nova_embedding, orvyn_embedding.T).flatten()[0]
            return float(max(0, min(1, alignment)))  # Нормализация до [0,1]
            
        except Exception as e:
            print(f"Lumen alignment calculation error: {e}")
            return 0.5

    def calculate_conflict_score(self, nova_result, orvyn_result):
        """Вычисление скора конфликта (упрощенная версия)"""
        # Анализ противоречий между аналитическим и аналоговым подходами
        nova_actions = nova_result["payload"]["candidate_actions"]
        orvyn_domains = set(tag for a in orvyn_result["payload"]["analogies"] for tag in a['tags'])
        
        conflict_indicators = 0
        total_checks = 0
        
        # Проверка на противоречия между действиями и доменами
        for action in nova_actions:
            action_lower = action.lower()
            if "traditional" in action_lower and "innovation" in orvyn_domains:
                conflict_indicators += 1
            if "reduce" in action_lower and "increase" in str(orvyn_result).lower():
                conflict_indicators += 1
            total_checks += 1
        
        return conflict_indicators / max(total_checks, 1)

    def calculate_novelty_score(self, nova_result, orvyn_result):
        """Вычисление скора новизны"""
        orvyn_innovation = orvyn_result["payload"]["resonance_map"]["innovation_potential"]
        domain_coverage = orvyn_result["payload"]["domain_coverage"]
        
        # Комбинированная оценка новизны
        novelty = (orvyn_innovation * 0.7) + (domain_coverage / 5 * 0.3)
        return float(min(novelty, 1.0))

    def select_strategy(self, alignment, conflict, novelty):
        """Выбор стратегии синтеза"""
        if alignment >= self.policy_thresholds["alignment_high"]:
            return "harmony"
        elif (alignment >= self.policy_thresholds["alignment_mid"] and 
              conflict >= self.policy_thresholds["conflict_mid"]):
            return "creative"
        else:
            return "conservative"

    def generate_insight(self, nova_result, orvyn_result, strategy, alignment, conflict):
        """Генерация финального инсайта на основе стратегии"""
        
        nova_actions = nova_result["payload"]["candidate_actions"]
        orvyn_analogies = orvyn_result["payload"]["analogies"]
        
        rationale = [
            f"nova: {len(nova_actions)} candidate actions",
            f"orvyn: {len(orvyn_analogies)} analogies across {orvyn_result['payload']['domain_coverage']} domains",
            f"synthesis: {strategy} strategy (alignment: {alignment:.2f}, conflict: {conflict:.2f})"
        ]
        
        if strategy == "harmony":
            insight = self._harmony_fusion(nova_actions, orvyn_analogies)
        elif strategy == "creative":
            insight = self._creative_fusion(nova_actions, orvyn_analogies)
        else:  # conservative
            insight = self._conservative_synthesis(nova_actions, orvyn_analogies)
        
        return insight, rationale

    def _harmony_fusion(self, nova_actions, orvyn_analogies):
        """Гармоничное слияние - сильные общие тезисы"""
        strongest_analogy = max(orvyn_analogies, key=lambda x: x['similarity'])
        
        insight = f"Based on analytical planning and supported by {strongest_analogy['snippet']}, " \
                 f"focus on {nova_actions[0] if nova_actions else 'the identified solution'} " \
                 f"with cross-domain validation."
        
        return insight

    def _creative_fusion(self, nova_actions, orvyn_analogies):
        """Креативный синтез - генерация новых гипотез"""
        diverse_analogies = sorted(orvyn_analogies, key=lambda x: x['similarity'])[:2]  # Более разнообразные
        
        insight = f"Creative synthesis suggests combining {nova_actions[0] if nova_actions else 'analytical approach'} " \
                 f"with insights from {diverse_analogies[0]['snippet']} and {diverse_analogies[1]['snippet']} " \
                 f"for innovative solutions."
        
        return insight

    def _conservative_synthesis(self, nova_actions, orvyn_analogies):
        """Консервативный синтез - приоритет аналитике с подсказками"""
        if orvyn_analogies:
            hint = f" Consider parallels with {orvyn_analogies[0]['snippet']} for additional context."
        else:
            hint = ""
            
        insight = f"Primary recommendation: {nova_actions[0] if nova_actions else 'proceed with analytical framework'}.{hint}"
        
        return insight

    def calculate_confidence(self, alignment, conflict, novelty, nova_conf, orvyn_conf):
        """Расчет общей уверенности"""
        # Взвешенная комбинация факторов
        base_confidence = (nova_conf * 0.4) + (orvyn_conf * 0.3)
        alignment_boost = alignment * 0.2
        conflict_penalty = conflict * 0.1
        
        confidence = base_confidence + alignment_boost - conflict_penalty
        return float(max(0, min(1, confidence)))

    async def start_listening(self):
        """Запуск прослушивания результатов ядер"""
        self.is_running = True
        print("LumenCore: Запуск прослушивания core_results...")
        
        # Кэш для ожидания парных результатов
        results_cache = {}
        
        while self.is_running:
            try:
                messages = self.redis_client.xread(
                    {"cognitive_bus:core_results": 0}, 
                    count=10, 
                    block=5000
                )
                
                if messages:
                    for stream, message_list in messages:
                        for message_id, message_data in message_list:
                            request_id = message_data["request_id"]
                            core = message_data["core"]
                            
                            # Сохранение в кэш
                            if request_id not in results_cache:
                                results_cache[request_id] = {}
                            results_cache[request_id][core] = message_data
                            
                            # Проверка готовности обоих результатов
                            if len(results_cache[request_id]) == 2:
                                nova_result = results_cache[request_id].get("nova")
                                orvyn_result = results_cache[request_id].get("orvyn")
                                
                                if nova_result and orvyn_result:
                                    await self.process_core_results(nova_result, orvyn_result)
                                    # Удаление обработанного запроса
                                    del results_cache[request_id]
                            
            except Exception as e:
                print(f"LumenCore ошибка: {e}")
                await asyncio.sleep(1)

    def stop(self):
        """Остановка сервиса"""
        self.is_running = False

if __name__ == "__main__":
    lumen = LumenCore()
    asyncio.run(lumen.start_listening())
