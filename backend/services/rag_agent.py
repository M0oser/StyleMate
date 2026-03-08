import json
import subprocess
from typing import List, Dict

def generate_outfit_via_llm(wardrobe: List[Dict], scenario: str, style: str) -> dict:
    """
    Генерирует лук, вызывая Ollama напрямую через терминальную команду.
    Использует жесткую структуру JSON для гарантии наличия всех элементов одежды.
    """
    wardrobe_text = ""
    for item in wardrobe:
        wardrobe_text += f"- ID: {item['id']}, Вещь: {item['title']}, Категория: {item['category']}, Цвет: {item['color']}\n"

    system_prompt = f"""
    Ты - профессиональный стилист (Fashion AI). 
    Собери стильный образ для пользователя из его гардероба.
    Мероприятие: {scenario}.
    Предпочитаемый стиль: {style}.
    
    Доступный гардероб:
    {wardrobe_text}
    
    ПРАВИЛА (ОЧЕНЬ ВАЖНО - СТРОГО СОБЛЮДАЙ СЛОТЫ):
    1. Слот "top_id" (Верх): ОБЯЗАТЕЛЬНО выбери ровно одну базовую вещь (tshirt, shirt, hoodie, sweater).
    2. Слот "bottom_id" (Низ): ОБЯЗАТЕЛЬНО выбери ровно одну вещь (jeans, trousers, shorts).
    3. Слот "shoes_id" (Обувь): ОБЯЗАТЕЛЬНО выбери ровно одну пару (sneakers, boots, shoes).
    4. Слот "outerwear_id" (Верхняя одежда): Если сценарий предполагает выход на улицу в плохую погоду ("дождь") или строгий стиль ("офис"), выбери поверх "top_id" еще одну вещь (jacket, coat, blazer). Если верхняя одежда не нужна, напиши null.
    5. Вещи должны сочетаться по цвету и стилю.
    6. Верни результат СТРОГО в формате JSON без маркдауна.

    
    Формат ответа:
    {{
        "explanation": "краткое объяснение, почему ты выбрал эти вещи",
        "top_id": 1,
        "bottom_id": 2,
        "shoes_id": 3,
        "outerwear_id": 4
    }}
    Если верхней одежды нет, передай null вместо ID.
    """

    try:
        # Вызываем Ollama как если бы ты писал в терминале
        # Команда: ollama run qwen2.5:latest "system prompt"
        result = subprocess.run(
            ["ollama", "run", "qwen2.5:latest", system_prompt],
            capture_output=True,
            text=True,
            check=True
        )
        
        content = result.stdout.strip()
        
        # Чистим ответ, чтобы оставить только JSON
        if "{" in content and "}" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            json_str = content[start:end]
            parsed_json = json.loads(json_str)
            
            # Собираем ID из новой структуры в один список для нашего бэкенда
            item_ids = []
            for key in ["top_id", "bottom_id", "shoes_id", "outerwear_id"]:
                if key in parsed_json and parsed_json[key] is not None:
                    # Убеждаемся, что ID это число
                    try:
                        item_ids.append(int(parsed_json[key]))
                    except (ValueError, TypeError):
                        pass
                    
            return {
                "explanation": parsed_json.get("explanation", "Мой выбор для тебя"),
                "item_ids": item_ids
            }
        else:
            raise ValueError("Модель не вернула JSON")
            
    except Exception as e:
        print(f"Ошибка RAG Агента (subprocess): {e}")
        return {"explanation": "Не удалось собрать лук", "item_ids": []}

if __name__ == "__main__":
    # Тестовый запуск
    mock_wardrobe = [
        {"id": 1, "title": "White T-Shirt", "category": "tshirt", "color": "white"},
        {"id": 2, "title": "Blue Jeans", "category": "jeans", "color": "blue"},
        {"id": 3, "title": "Black Blazer", "category": "jacket", "color": "black"},
        {"id": 4, "title": "Red Sneakers", "category": "sneakers", "color": "red"},
        {"id": 5, "title": "Brown Loafers", "category": "shoes", "color": "brown"}
    ]
    
    print("Отправляю запрос в Qwen через терминал (subprocess)...")
    result = generate_outfit_via_llm(mock_wardrobe, scenario="Офис", style="Minimal")
    print(json.dumps(result, indent=2, ensure_ascii=False))
