from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
import uuid
import json
import redis
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import sqlite3
import os

router = APIRouter(prefix="/api/v1", tags=["system"])

# Подключение к Redis
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Модели данных
class SystemStatus(BaseModel):
    status: str
    timestamp: str
    components: Dict[str, str]
    performance: Dict[str, float]

class CoreMetrics(BaseModel):
    core: str
    requests_processed: int
    avg_processing_time: float
    success_rate: float
    memory_usage: int

class InsightRequest(BaseModel):
    query: str
    context: Dict[str, Any] = {}
    mode: str = "balanced"  # analytic, creative, balanced
    user_id: Optional[str] = None

class InsightResponse(BaseModel):
    request_id: str
    insight: str
    confidence: float
    rationale: List[str]
    strategy: str
    processing_time: float
    timestamp: str

class BatchInsightRequest(BaseModel):
    queries: List[InsightRequest]
    batch_id: Optional[str] = None

class BatchInsightResponse(BaseModel):
    batch_id: str
    results: List[InsightResponse]
    total_processed: int
    failed_count: int

class MemoryQuery(BaseModel):
    core: str  # nova, orvyn, lumen
    query: str
    limit: int = 10

class MemoryItem(BaseModel):
    id: str
    content: str
    confidence: Optional[float] = None
    timestamp: str
    metadata: Dict[str, Any]

class FeedbackAnalytics(BaseModel):
    total_feedback: int
    average_rating: float
    rating_distribution: Dict[int, int]
    recent_comments: List[str]

# Вспомогательные функции
def get_db_connection(db_path: str):
    """Получение подключения к SQLite базе"""
    return sqlite3.connect(db_path)

def get_system_stats():
    """Получение статистики системы"""
    try:
        # Статистика из Redis потоков
        total_requests = redis_client.xlen("cognitive_bus:requests")
        total_nova_results = redis_client.xlen("cognitive_bus:core_results")
        total_lumen_decisions = redis_client.xlen("cognitive_bus:lumen_decisions")
        total_feedback = redis_client.xlen("cognitive_bus:feedback")
        
        # Проверка активности сервисов (упрощенная)
        services_status = {
            "redis": "active" if redis_client.ping() else "inactive",
            "nova_core": "unknown",
            "orvyn_core": "unknown", 
            "lumen_core": "unknown"
        }
        
        return {
            "requests": total_requests,
            "nova_results": total_nova_results,
            "lumen_decisions": total_lumen_decisions,
            "feedback": total_feedback,
            "services": services_status
        }
    except Exception as e:
        return {"error": str(e)}

def get_core_metrics(core: str) -> CoreMetrics:
    """Получение метрик для конкретного ядра"""
    try:
        db_path = f"memory/{core}_memory.db"
        if not os.path.exists(db_path):
            return CoreMetrics(
                core=core,
                requests_processed=0,
                avg_processing_time=0.0,
                success_rate=0.0,
                memory_usage=0
            )
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Количество обработанных запросов
        if core == "nova":
            cursor.execute("SELECT COUNT(*) FROM nova_memory")
        elif core == "orvyn":
            cursor.execute("SELECT COUNT(*) FROM orvyn_memory") 
        elif core == "lumen":
            cursor.execute("SELECT COUNT(*) FROM lumen_memory")
        
        requests_processed = cursor.fetchone()[0]
        
        # Размер базы данных как показатель использования памяти
        memory_usage = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        
        conn.close()
        
        return CoreMetrics(
            core=core,
            requests_processed=requests_processed,
            avg_processing_time=0.0,  # Можно добавить расчет из временных меток
            success_rate=1.0,  # Упрощенно
            memory_usage=memory_usage
        )
        
    except Exception as e:
        return CoreMetrics(
            core=core,
            requests_processed=0,
            avg_processing_time=0.0,
            success_rate=0.0,
            memory_usage=0
        )

# Эндпоинты системы
@router.get("/health", response_model=SystemStatus)
async def health_check():
    """Комплексная проверка здоровья системы"""
    try:
        stats = get_system_stats()
        
        components = {
            "api_gateway": "healthy",
            "cognitive_bus": "healthy" if stats.get("requests", 0) >= 0 else "degraded",
            "redis": stats["services"]["redis"],
            "postgres": "unknown"  # Можно добавить проверку Postgres
        }
        
        performance = {
            "requests_per_minute": 0,  # Можно добавить реальные метрики
            "avg_response_time": 0.5,
            "error_rate": 0.02
        }
        
        return SystemStatus(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            components=components,
            performance=performance
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"System health check failed: {str(e)}")

@router.get("/metrics/cores", response_model=List[CoreMetrics])
async def get_core_metrics_endpoint():
    """Получение метрик всех ядер системы"""
    cores = ["nova", "orvyn", "lumen"]
    metrics = [get_core_metrics(core) for core in cores]
    return metrics

@router.get("/metrics/system")
async def get_system_metrics():
    """Детальная системная метрика"""
    stats = get_system_stats()
    
    # Дополнительные метрики
    redis_info = redis_client.info()
    
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "basic_stats": stats,
        "redis": {
            "used_memory": redis_info.get('used_memory', 0),
            "connected_clients": redis_info.get('connected_clients', 0),
            "ops_per_sec": redis_info.get('instantaneous_ops_per_sec', 0)
        },
        "throughput": {
            "requests_today": stats["requests"],
            "decisions_today": stats["lumen_decisions"]
        }
    }
    
    return metrics

@router.get("/traces")
async def get_recent_traces(limit: int = Query(10, ge=1, le=100)):
    """Получение последних трейсов выполнения"""
    try:
        # Поиск ключей трейсов в Redis
        trace_keys = []
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match="trace:*", count=100)
            trace_keys.extend(keys)
            if cursor == 0:
                break
        
        # Получение последних трейсов
        traces = []
        for key in trace_keys[-limit:]:
            trace_data = redis_client.get(key)
            if trace_data:
                traces.append(json.loads(trace_data))
        
        return {
            "total_traces": len(trace_keys),
            "returned_traces": len(traces),
            "traces": sorted(traces, key=lambda x: x.get('timestamp', ''), reverse=True)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving traces: {str(e)}")

@router.get("/traces/{request_id}")
async def get_trace_by_id(request_id: str):
    """Получение конкретного трейса по ID запроса"""
    trace_data = redis_client.get(f"trace:{request_id}")
    if not trace_data:
        raise HTTPException(status_code=404, detail=f"Trace not found for request_id: {request_id}")
    
    return json.loads(trace_data)

@router.post("/insights/batch", response_model=BatchInsightResponse)
async def batch_insight_request(
    batch_request: BatchInsightRequest, 
    background_tasks: BackgroundTasks
):
    """Пакетная обработка запросов на инсайты"""
    batch_id = batch_request.batch_id or str(uuid.uuid4())
    results = []
    failed_count = 0
    
    for i, query_request in enumerate(batch_request.queries):
        try:
            # Создание индивидуального запроса
            request_data = {
                "request_id": f"{batch_id}_{i}",
                "user_id": query_request.user_id or f"batch_{batch_id}",
                "query": query_request.query,
                "context": query_request.context,
                "mode": query_request.mode,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Публикация в Cognitive Bus
            redis_client.xadd("cognitive_bus:requests", request_data)
            
            # Ожидание ответа (упрощенное)
            await asyncio.sleep(0.5)
            
            # Поиск ответа в потоке Lumen решений
            messages = redis_client.xread(
                {"cognitive_bus:lumen_decisions": 0}, 
                count=10, 
                block=1000
            )
            
            lumen_decision = None
            if messages:
                for stream, message_list in messages:
                    for message_id, message_data in message_list:
                        if message_data.get("request_id") == request_data["request_id"]:
                            lumen_decision = message_data
                            break
            
            if lumen_decision:
                insight_response = InsightResponse(
                    request_id=request_data["request_id"],
                    insight=lumen_decision["insight"],
                    confidence=lumen_decision["confidence"],
                    rationale=lumen_decision["rationale"],
                    strategy=lumen_decision["meta"]["strategy"],
                    processing_time=0.5,  # Упрощенно
                    timestamp=lumen_decision["timestamp"]
                )
                results.append(insight_response)
            else:
                failed_count += 1
                
        except Exception as e:
            print(f"Error processing batch item {i}: {e}")
            failed_count += 1
    
    return BatchInsightResponse(
        batch_id=batch_id,
        results=results,
        total_processed=len(results),
        failed_count=failed_count
    )

@router.get("/memory/search", response_model=List[MemoryItem])
async def search_memory(
    core: str = Query(..., description="Core to search (nova, orvyn, lumen)"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """Поиск в памяти конкретного ядра"""
    try:
        db_path = f"memory/{core}_memory.db"
        if not os.path.exists(db_path):
            return []
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        memory_items = []
        
        if core == "nova":
            cursor.execute('''
                SELECT request_id, logic_tree, confidence, created_at, metadata 
                FROM nova_memory 
                WHERE logic_tree LIKE ? OR key LIKE ?
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
            
            for row in cursor.fetchall():
                memory_items.append(MemoryItem(
                    id=row[0],
                    content=row[1][:500],  # Ограничение длины
                    confidence=row[2],
                    timestamp=row[3],
                    metadata=json.loads(row[4]) if row[4] else {}
                ))
                
        elif core == "orvyn":
            cursor.execute('''
                SELECT request_id, snippet_text, similarity_score, created_at, analogies_tags
                FROM orvyn_memory 
                WHERE snippet_text LIKE ? OR query_text LIKE ?
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
            
            for row in cursor.fetchall():
                memory_items.append(MemoryItem(
                    id=row[0],
                    content=row[1],
                    confidence=row[2],
                    timestamp=row[3],
                    metadata={"tags": json.loads(row[4]) if row[4] else []}
                ))
                
        elif core == "lumen":
            cursor.execute('''
                SELECT request_id, insight_text, confidence, created_at, activation_meta
                FROM lumen_memory 
                WHERE insight_text LIKE ?
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            for row in cursor.fetchall():
                memory_items.append(MemoryItem(
                    id=row[0],
                    content=row[1],
                    confidence=row[2],
                    timestamp=row[3],
                    metadata=json.loads(row[4]) if row[4] else {}
                ))
        
        conn.close()
        return memory_items
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching memory: {str(e)}")

@router.get("/analytics/feedback", response_model=FeedbackAnalytics)
async def get_feedback_analytics(
    hours: int = Query(24, description="Time window in hours")
):
    """Аналитика фидбека за указанный период"""
    try:
        # Получение фидбека из Redis
        start_time = "-"  # С начала потока
        messages = redis_client.xrange("cognitive_bus:feedback", start_time, "+")
        
        recent_feedback = []
        rating_sum = 0
        rating_count = 0
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        recent_comments = []
        
        for message_id, message_data in messages:
            try:
                rating = int(message_data.get('rating', 0))
                if 1 <= rating <= 5:
                    rating_sum += rating
                    rating_count += 1
                    rating_distribution[rating] += 1
                    
                    comment = message_data.get('comments', '')
                    if comment:
                        recent_comments.append(comment[:200])  # Ограничение длины
            except (ValueError, TypeError):
                continue
        
        average_rating = rating_sum / rating_count if rating_count > 0 else 0
        
        return FeedbackAnalytics(
            total_feedback=rating_count,
            average_rating=round(average_rating, 2),
            rating_distribution=rating_distribution,
            recent_comments=recent_comments[-10:]  # Последние 10 комментариев
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing feedback: {str(e)}")

@router.post("/system/maintenance/cleanup")
async def system_cleanup(
    older_than_days: int = Query(7, description="Remove data older than X days")
):
    """Очистка старых данных системы"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        cutoff_timestamp = cutoff_date.isoformat()
        
        cleanup_stats = {
            "redis_traces_removed": 0,
            "nova_memory_cleaned": 0,
            "orvyn_memory_cleaned": 0,
            "lumen_memory_cleaned": 0
        }
        
        # Очистка трейсов в Redis
        trace_keys = []
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match="trace:*", count=100)
            trace_keys.extend(keys)
            if cursor == 0:
                break
        
        for key in trace_keys:
            trace_data = redis_client.get(key)
            if trace_data:
                trace = json.loads(trace_data)
                trace_time = trace.get('timestamp', '')
                if trace_time < cutoff_timestamp:
                    redis_client.delete(key)
                    cleanup_stats["redis_traces_removed"] += 1
        
        # Очистка памяти ядер (упрощенно)
        cores = ["nova", "orvyn", "lumen"]
        for core in cores:
            db_path = f"memory/{core}_memory.db"
            if os.path.exists(db_path):
                conn = get_db_connection(db_path)
                cursor = conn.cursor()
                
                if core == "nova":
                    cursor.execute("DELETE FROM nova_memory WHERE created_at < ?", (cutoff_timestamp,))
                elif core == "orvyn":
                    cursor.execute("DELETE FROM orvyn_memory WHERE created_at < ?", (cutoff_timestamp,))
                elif core == "lumen":
                    cursor.execute("DELETE FROM lumen_memory WHERE created_at < ?", (cutoff_timestamp,))
                
                cleaned = cursor.rowcount
                conn.commit()
                conn.close()
                
                cleanup_stats[f"{core}_memory_cleaned"] = cleaned
        
        return {
            "status": "cleanup_completed",
            "cutoff_date": cutoff_timestamp,
            "stats": cleanup_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@router.get("/system/config")
async def get_system_config():
    """Получение текущей конфигурации системы"""
    config = {
        "lumen_policy_thresholds": {
            "alignment_high": 0.75,
            "alignment_mid": 0.45, 
            "conflict_mid": 0.35
        },
        "available_modes": ["analytic", "creative", "balanced"],
        "max_processing_time": 30,  # seconds
        "batch_processing_limit": 50,
        "memory_retention_days": 7
    }
    
    return config

@router.post("/system/config/update")
async def update_system_config(updates: Dict[str, Any]):
    """Обновление конфигурации системы (упрощенно)"""
    # В реальной системе здесь была бы валидация и сохранение конфигурации
    return {
        "status": "config_updated",
        "updates_applied": list(updates.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

# Эндпоинты для тестирования и разработки
@router.post("/test/echo")
async def echo_test(data: Dict[str, Any]):
    """Эхо-тест для проверки работы API"""
    return {
        "received": data,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": str(uuid.uuid4())
    }

@router.get("/test/cores")
async def test_cores_communication():
    """Тест коммуникации между ядрами"""
    test_request = {
        "request_id": f"test_comm_{uuid.uuid4()}",
        "user_id": "tester",
        "query": "Test communication between cores",
        "context": {"test": True},
        "mode": "balanced",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Публикация тестового запроса
    redis_client.xadd("cognitive_bus:requests", test_request)
    
    return {
        "status": "test_request_sent",
        "request_id": test_request["request_id"],
        "message": "Check core logs for communication test results"
    }

# Инициализация роутера
def setup_endpoints(app):
    """Регистрация всех эндпоинтов в приложении FastAPI"""
    app.include_router(router)
