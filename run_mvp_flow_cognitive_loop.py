#!/usr/bin/env python3
"""
Усовершенствованный тестовый скрипт для полного когнитивного цикла
"""

import asyncio
import requests
import json
import time
import sys
import os

# Добавляем путь к корню проекта для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cores.nova_core import NovaCore
from cores.orvyn_core import OrvynCore
from cores.lumen_core import LumenCore
from utils.logger import setup_logging, get_system_logger

# Настройка логирования
setup_logging()
logger = get_system_logger()

async def run_full_system_test():
    """Тест полной системы с тремя ядрами"""
    logger.log_system_event("test_start", "test_suite", "Starting full system test")
    
    print("🚀 Запуск полного теста когнитивной системы Nova+Orvyn+Lumen...")
    
    # Запуск всех ядер в фоне
    nova = NovaCore()
    orvyn = OrvynCore()
    lumen = LumenCore()
    
    nova_task = asyncio.create_task(nova.start_listening())
    orvyn_task = asyncio.create_task(orvyn.start_listening())
    lumen_task = asyncio.create_task(lumen.start_listening())
    
    # Даем время на запуск сервисов
    await asyncio.sleep(3)
    
    # Тестовые запросы
    test_cases = [
        {
            "user_id": "test_user_1",
            "query": "Как сократить расходы на воду в сельской местности?",
            "context": {"budget": "low", "location": "rural"},
            "mode": "balanced"
        },
        {
            "user_id": "test_user_2", 
            "query": "Инновационные методы экономии энергии в офисе",
            "context": {"budget": "medium", "innovation": "high"},
            "mode": "creative"
        },
        {
            "user_id": "test_user_3",
            "query": "Проверенные способы увеличения продуктивности команды",
            "context": {"risk": "low", "timeframe": "short"},
            "mode": "analytic"
        }
    ]
    
    results = []
    
    for i, test_data in enumerate(test_cases, 1):
        print(f"\n📝 Тестовый запрос {i}: {test_data['query']}")
        
        try:
            start_time = time.time()
            response = requests.post(
                "http://localhost:8000/api/think",
                json=test_data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                processing_time = time.time() - start_time
                
                print(f"✅ Успешный ответ за {processing_time:.2f}с:")
                print(f"   Insight: {result['lumen']['insight']}")
                print(f"   Confidence: {result['lumen']['confidence']:.2f}")
                print(f"   Strategy: {result['lumen']['activation_meta']['strategy']}")
                
                results.append({
                    "test_case": i,
                    "success": True,
                    "processing_time": processing_time,
                    "confidence": result['lumen']['confidence'],
                    "strategy": result['lumen']['activation_meta']['strategy']
                })
                
                # Симуляция человеческого фидбека
                if i == 1:
                    feedback_data = {
                        "request_id": result["request_id"],
                        "rating": 4,
                        "comments": "Полезный инсайт с практическими рекомендациями"
                    }
                    
                    feedback_resp = requests.post(
                        "http://localhost:8000/api/feedback",
                        json=feedback_data
                    )
                    
                    if feedback_resp.status_code == 200:
                        print("   📝 Feedback submitted successfully")
                
            else:
                print(f"❌ Ошибка API: {response.status_code} - {response.text}")
                results.append({
                    "test_case": i, 
                    "success": False,
                    "error": response.text
                })
                
        except Exception as e:
            print(f"❌ Ошибка при запросе: {e}")
            results.append({
                "test_case": i,
                "success": False, 
                "error": str(e)
            })
        
        await asyncio.sleep(2)
    
    # Статистика тестирования
    print(f"\n📊 Результаты тестирования:")
    successful_tests = [r for r in results if r['success']]
    if successful_tests:
        avg_confidence = sum(r['confidence'] for r in successful_tests) / len(successful_tests)
        avg_time = sum(r['processing_time'] for r in successful_tests) / len(successful_tests)
        
        print(f"   Успешных тестов: {len(successful_tests)}/{len(test_cases)}")
        print(f"   Средняя уверенность: {avg_confidence:.2f}")
        print(f"   Среднее время обработки: {avg_time:.2f}с")
        
        strategies = {}
        for r in successful_tests:
            strategies[r['strategy']] = strategies.get(r['strategy'], 0) + 1
        
        print(f"   Распределение стратегий: {strategies}")
    
    # Остановка сервисов
    print("\n🛑 Остановка сервисов...")
    nova.stop()
    orvyn.stop() 
    lumen.stop()
    
    await asyncio.sleep(2)
    logger.log_system_event("test_complete", "test_suite", "Full system test completed")
    print("Тестирование завершено.")

if __name__ == "__main__":
    print("Nova System MVP Testing Suite")
    print("=" * 50)
    
    asyncio.run(run_full_system_test())
