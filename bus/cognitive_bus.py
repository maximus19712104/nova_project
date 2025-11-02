import redis
import json

class CognitiveBus:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def publish_request(self, request_data):
        """Публикация запроса в шину"""
        return self.redis_client.xadd("cognitive_bus:requests", request_data)

    def publish_core_result(self, core_result):
        """Публикация результата работы ядра"""
        return self.redis_client.xadd("cognitive_bus:core_results", core_result)

    def publish_lumen_decision(self, decision):
        """Публикация решения Lumen"""
        return self.redis_client.xadd("cognitive_bus:lumen_decisions", decision)

    def get_pending_requests(self, count=10):
        """Получение ожидающих запросов"""
        return self.redis_client.xread({"cognitive_bus:requests": 0}, count=count)

    def subscribe_to_requests(self, callback):
        """Подписка на новые запросы (упрощенная версия)"""
        last_id = '0'
        while True:
            messages = self.redis_client.xread(
                {"cognitive_bus:requests": last_id}, 
                count=1, 
                block=5000
            )
            if messages:
                for stream, message_list in messages:
                    for message_id, message_data in message_list:
                        callback(message_data)
                        last_id = message_id
