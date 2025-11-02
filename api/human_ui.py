from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import redis
import json

app = FastAPI(title="Nova System Human UI")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Главная панель для человеческой оценки"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/evaluation", response_class=HTMLResponse)
async def evaluation_page(request: Request):
    """Страница оценки инсайтов"""
    
    # Получение последних решений для оценки
    messages = redis_client.xread({"cognitive_bus:lumen_decisions": 0}, count=5)
    insights = []
    
    if messages:
        for stream, message_list in messages:
            for message_id, message_data in message_list:
                insights.append({
                    "request_id": message_data["request_id"],
                    "insight": message_data["insight"],
                    "confidence": message_data["confidence"],
                    "strategy": message_data["meta"]["strategy"],
                    "rationale": message_data["rationale"]
                })
    
    return templates.TemplateResponse("evaluation.html", {
        "request": request, 
        "insights": insights
    })

@app.post("/submit_feedback")
async def submit_feedback(
    request_id: str = Form(...),
    rating: int = Form(...),
    comments: str = Form("")
):
    """Обработка отправки фидбека"""
    
    feedback_data = {
        "request_id": request_id,
        "rating": rating,
        "comments": comments,
        "timestamp": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}})
    }
    
    redis_client.xadd("cognitive_bus:feedback", feedback_data)
    
    return {"status": "success", "message": "Feedback submitted successfully"}

@app.get("/stats")
async def get_stats():
    """Получение статистики системы"""
    try:
        # Базовая статистика
        total_requests = redis_client.xlen("cognitive_bus:requests")
        total_decisions = redis_client.xlen("cognitive_bus:lumen_decisions")
        total_feedback = redis_client.xlen("cognitive_bus:feedback")
        
        return {
            "total_requests": total_requests,
            "total_decisions": total_decisions,
            "total_feedback": total_feedback,
            "system_health": "operational"
        }
    except Exception as e:
        return {"error": str(e)}
