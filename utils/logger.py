import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import traceback

class JSONFormatter(logging.Formatter):
    """Форматтер для логов в JSON формате"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирование лог-записи в JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "process_id": record.process,
            "thread_id": record.thread
        }
        
        # Добавление экстра-полей
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        # Добавление информации об исключении
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False)

class CognitiveLogger:
    """Кастомный логгер для когнитивной системы"""
    
    def __init__(self, name: str = "nova_system", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Предотвращение дублирования логов
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Настройка обработчиков логов"""
        
        # Создание директории для логов
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Форматтеры
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s'
        )
        json_formatter = JSONFormatter()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_formatter)
        
        # File handler (текстовый)
        file_handler = logging.FileHandler(
            log_dir / f"nova_system_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        # JSON file handler
        json_handler = logging.FileHandler(
            log_dir / f"nova_system_json_{datetime.now().strftime('%Y%m%d')}.log"
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(json_formatter)
        
        # Error file handler
        error_handler = logging.FileHandler(
            log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        
        # Добавление обработчиков
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(json_handler)
        self.logger.addHandler(error_handler)
    
    def log_request(self, request_id: str, user_id: str, query: str, 
                   context: Dict[str, Any], mode: str):
        """Логирование входящего запроса"""
        extra_data = {
            "request_id": request_id,
            "user_id": user_id,
            "query": query,
            "context": context,
            "mode": mode,
            "event_type": "request_received"
        }
        self.logger.info(f"Request received: {request_id}", extra={'extra_data': extra_data})
    
    def log_core_processing(self, core: str, request_id: str, processing_time: float, 
                           result_count: int = None, confidence: float = None):
        """Логирование обработки ядром"""
        extra_data = {
            "core": core,
            "request_id": request_id,
            "processing_time_ms": round(processing_time * 1000, 2),
            "result_count": result_count,
            "confidence": confidence,
            "event_type": "core_processing"
        }
        self.logger.info(f"{core} processed request: {request_id}", 
                        extra={'extra_data': extra_data})
    
    def log_lumen_synthesis(self, request_id: str, strategy: str, alignment_score: float,
                           conflict_score: float, confidence: float, processing_time: float):
        """Логирование синтеза Lumen"""
        extra_data = {
            "request_id": request_id,
            "strategy": strategy,
            "alignment_score": alignment_score,
            "conflict_score": conflict_score,
            "confidence": confidence,
            "processing_time_ms": round(processing_time * 1000, 2),
            "event_type": "lumen_synthesis"
        }
        self.logger.info(f"Lumen synthesis completed: {request_id} (strategy: {strategy})", 
                        extra={'extra_data': extra_data})
    
    def log_feedback(self, request_id: str, rating: int, comments: str = ""):
        """Логирование фидбека"""
        extra_data = {
            "request_id": request_id,
            "rating": rating,
            "comments": comments,
            "event_type": "feedback_received"
        }
        self.logger.info(f"Feedback received for {request_id}: rating {rating}", 
                        extra={'extra_data': extra_data})
    
    def log_error(self, error_type: str, message: str, request_id: str = None,
                 exception: Exception = None, context: Dict[str, Any] = None):
        """Логирование ошибок"""
        extra_data = {
            "error_type": error_type,
            "request_id": request_id,
            "context": context or {},
            "event_type": "error"
        }
        
        if exception:
            extra_data["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception)
            }
        
        self.logger.error(f"{error_type}: {message}", extra={'extra_data': extra_data})
    
    def log_system_event(self, event_type: str, component: str, message: str,
                        details: Dict[str, Any] = None):
        """Логирование системных событий"""
        extra_data = {
            "event_type": event_type,
            "component": component,
            "details": details or {},
            "system_event": True
        }
        self.logger.info(f"System event [{component}]: {message}", 
                        extra={'extra_data': extra_data})
    
    def log_performance_metric(self, metric_name: str, value: float, 
                              tags: Dict[str, str] = None):
        """Логирование метрик производительности"""
        extra_data = {
            "metric_name": metric_name,
            "value": value,
            "tags": tags or {},
            "event_type": "performance_metric"
        }
        self.logger.info(f"Performance metric: {metric_name} = {value}", 
                        extra={'extra_data': extra_data})

    # Стандартные методы логгера
    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, extra={'extra_data': kwargs})
    
    def info(self, msg: str, **kwargs):
        self.logger.info(msg, extra={'extra_data': kwargs})
    
    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, extra={'extra_data': kwargs})
    
    def error(self, msg: str, **kwargs):
        self.logger.error(msg, extra={'extra_data': kwargs})
    
    def critical(self, msg: str, **kwargs):
        self.logger.critical(msg, extra={'extra_data': kwargs})

# Глобальные инстансы логгеров для разных компонентов
_nova_logger = None
_orvyn_logger = None
_lumen_logger = None
_system_logger = None

def get_nova_logger() -> CognitiveLogger:
    global _nova_logger
    if _nova_logger is None:
        _nova_logger = CognitiveLogger("nova_core")
    return _nova_logger

def get_orvyn_logger() -> CognitiveLogger:
    global _orvyn_logger
    if _orvyn_logger is None:
        _orvyn_logger = CognitiveLogger("orvyn_core")
    return _orvyn_logger

def get_lumen_logger() -> CognitiveLogger:
    global _lumen_logger
    if _lumen_logger is None:
        _lumen_logger = CognitiveLogger("lumen_core")
    return _lumen_logger

def get_system_logger() -> CognitiveLogger:
    global _system_logger
    if _system_logger is None:
        _system_logger = CognitiveLogger("nova_system")
    return _system_logger

# Утилитарные функции для логирования
def setup_logging(log_level: str = "INFO"):
    """Настройка базового логирования для всего приложения"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"logs/system_{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )

def log_exception(logger: CognitiveLogger, exception: Exception, 
                 context: str = "", request_id: str = None):
    """Утилита для логирования исключений с контекстом"""
    logger.log_error(
        error_type=type(exception).__name__,
        message=f"{context}: {str(exception)}",
        request_id=request_id,
        exception=exception,
        context={"traceback": traceback.format_exc()}
    )

# Декоратор для логирования выполнения функций
def log_execution(logger: CognitiveLogger, operation_name: str):
    """Декоратор для логирования времени выполнения функции"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger.info(f"Starting {operation_name}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                logger.log_performance_metric(
                    metric_name=f"{operation_name}_time",
                    value=execution_time,
                    tags={"operation": operation_name, "status": "success"}
                )
                
                logger.info(f"Completed {operation_name} in {execution_time:.2f}s")
                return result
                
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                
                logger.log_performance_metric(
                    metric_name=f"{operation_name}_time",
                    value=execution_time,
                    tags={"operation": operation_name, "status": "error"}
                )
                
                log_exception(logger, e, f"Error in {operation_name}")
                raise
        
        return wrapper
    return decorator
