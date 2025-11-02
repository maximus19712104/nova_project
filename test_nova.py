import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import cores.core as core
    print("✔ cores.core импортирован")
except ImportError as e:
    print("❌ Ошибка импорта:", e)
    sys.exit(1)
except Exception as e:
    print("❌ Другая ошибка:", e)
    sys.exit(1)

def test_basic_functionality():
    print("=== Тест базового функционала ===")
    if hasattr(core, 'run_task'):
        print("✔ run_task найден")
    else:
        print("⚠ run_task отсутствует, нужно проверить core.py")

def main():
    print("=== Запуск тестов Nova ===")
    test_basic_functionality()
    print("=== Тесты завершены ===")

if __name__ == "__main__":
    main()

