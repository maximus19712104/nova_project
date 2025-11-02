from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
import json
import redis
import asyncio
from datetime import datetime
import time

# Импорт endpoints
from api.endpoints import setup_endpoints

app = FastAPI(title="Nova System API", version="1.0.0", docs_url="/docs")

# Подключение к Redis
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Регистрация дополнительных эндпоинтов
setup_endpoints(app)

class ThinkRequest(BaseModel):
    user_id: str
    query: str
    context: dict = {}
    mode: str = "balanced"

class ThinkResponse(BaseModel):
    request_id: str
    lumen: dict
    trace_id: str

class FeedbackRequest(BaseModel):
    request_id: str
    rating: int
    comments: str = ""

def wait_for_lumen_decision(request_id, timeout=10):
    """Ожидание решения от Lumen"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        messages = redis_client.xread(
            {"cognitive_bus:lumen_decisions": 0}, 
            count=10, 
            block=1000
        )
        
        if messages:
            for stream, message_list in messages:
                for message_id, message_data in message_list:
                    if message_data.get("request_id") == request_id:
                        return message_data
        
    return None

@app.post("/api/think", response_model=ThinkResponse)
async def think_endpoint(request: ThinkRequest, background_tasks: BackgroundTasks):
    """Основной эндпоинт для обработки запросов"""
    
    request_id = str(uuid.uuid4())
    
    try:
        # Публикация запроса в Cognitive Bus
        bus_message = {
            "request_id": request_id,
            "user_id": request.user_id,
            "query": request.query,
            "context": request.context,
            "mode": request.mode,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        redis_client.xadd("cognitive_bus:requests", bus_message)
        
        # Ожидание ответа от Lumen
        lumen_decision = wait_for_lumen_decision(request_id)
        
        if lumen_decision:
            response = {
                "request_id": request_id,
                "lumen": {
                    "insight": lumen_decision["insight"],
                    "confidence": lumen_decision["confidence"],
                    "rationale": lumen_decision["rationale"],
                    "activation_meta": lumen_decision["meta"]
                },
                "trace_id": f"trace_{request_id}"
            }
            
            # Сохранение трейса
            save_trace(request_id, bus_message, lumen_decision)
            
            return ThinkResponse(**response)
        else:
            raise HTTPException(status_code=408, detail="Timeout waiting for processing")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки запроса: {str(e)}")

@app.post("/api/feedback")
async def feedback_endpoint(feedback: FeedbackRequest):
    """Эндпоинт для обратной связи"""
    try:
        feedback_data = {
            "request_id": feedback.request_id,
            "rating": feedback.rating,
            "comments": feedback.comments,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        redis_client.xadd("cognitive_bus:feedback", feedback_data)
        
        return {"status": "feedback_received", "request_id": feedback.request_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения фидбека: {str(e)}")

def save_trace(request_id, request_data, decision_data):
    """Сохранение трейса выполнения"""
    trace_data = {
        "request_id": request_id,
        "request": request_data,
        "decision": decision_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    redis_client.set(f"trace:{request_id}", json.dumps(trace_data), ex=3600)

@app.get("/trace/{request_id}")
async def get_trace(request_id: str):
    """Получение трейса по ID запроса"""
    trace_data = redis_client.get(f"trace:{request_id}")
    
    if trace_data:
        return json.loads(trace_data)
    else:
        raise HTTPException(status_code=404, detail="Trace not found")

@app.get("/")
async def root():
    """Корневой эндпоинт с информацией о API"""
    return {
        "message": "Nova System Cognitive API",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/api/v1/health",
            "think": "/api/think",
            "metrics": "/api/v1/metrics/cores"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
