# run.py
from fastapi import FastAPI
from api.endpoints import router  # импортируем router из endpoints.py

# создаём объект FastAPI
app = FastAPI(title="Nova DeepSeek Project")

# подключаем маршруты
app.include_router(router)

# точка входа (необязательно, если запускаем через uvicorn)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("run:app", host="127.0.0.1", port=8000, reload=True)

