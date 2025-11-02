from fastapi import APIRouter
import torch

router = APIRouter()

# -----------------------------
# 1️⃣ ML Test
# -----------------------------
@router.get("/ml-test")
def ml_test():
    """
    Проверка доступности PyTorch и базовых операций.
    """
    try:
        x = torch.tensor([1.0, 2.0, 3.0])
        y = x * 2
        return {"status": "ok", "input": x.tolist(), "output": y.tolist()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# -----------------------------
# 2️⃣ Nova test (dummy pipeline)
# -----------------------------
@router.get("/nova-test")
def nova_test():
    """
    Простая проверка функционала Nova без ML.
    Можно расширять по мере добавления реальных функций.
    """
    try:
        sample_data = {"text": "Hello Nova"}
        # имитация обработки данных
        processed_data = {k: v.upper() for k, v in sample_data.items()}
        return {"status": "ok", "processed_data": processed_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# -----------------------------
# 3️⃣ Health check
# -----------------------------
@router.get("/health")
def health_check():
    """
    Проверка состояния сервиса.
    """
    return {"status": "healthy"}

