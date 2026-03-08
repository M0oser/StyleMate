import json
import subprocess
from typing import List, Dict

def generate_outfit_via_llm(wardrobe: List[Dict], scenario: str, style: str) -> dict:
    """
    Генерирует лук, вызывая Ollama напрямую через терминальную команду.
    """
    wardrobe_text = ""
    for item in wardrobe:
        wardrobe_text += f"- ID: {item['id']}, Вещь: {item['title']}, Категория: {item['category']}, Цвет: {item['color']}\n"

    system_prompt = f"""
    Ты - Fashion AI. Собери образ.
    Мероприятие: {scenario}. Стиль: {style}.
    Гардероб:
    {wardrobe_text}
    
    ПРАВИЛА:
    1. Выбери "верх", "низ" и "обувь".
    2. Верни ТОЛЬКО JSON, без маркдауна.
    Формат: {{"explanation": "почему", "item_ids": [1, 2, 3]}}
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
            return json.loads(json_str)
        else:
            raise ValueError("Модель не вернула JSON")
            
    except Exception as e:
        print(f"Ошибка RAG Агента (subprocess): {e}")
        return {"explanation": "Не удалось собрать лук", "item_ids": []}

if __name__ == "__main__":
    mock_wardrobe = [
        {"id": 1, "title": "White T-Shirt", "category": "tshirt", "color": "white"},
        {"id": 2, "title": "Blue Jeans", "category": "jeans", "color": "blue"},
        {"id": 3, "title": "Black Blazer", "category": "blazer", "color": "black"},
        {"id": 4, "title": "Red Sneakers", "category": "sneakers", "color": "red"},
        {"id": 5, "title": "Brown Loafers", "category": "loafers", "color": "brown"}
    ]
    
    print("Отправляю запрос в Qwen через терминал (subprocess)...")
    result = generate_outfit_via_llm(mock_wardrobe, scenario="Офис", style="Minimal")
    print(json.dumps(result, indent=2, ensure_ascii=False))
