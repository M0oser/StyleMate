import os
import json
import random
from typing import List, Dict
from gigachat import GigaChat

def get_gigachat_key():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(base_dir, '.env')
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('GIGACHAT_CREDENTIALS='):
                    return line.split('=', 1)[1].strip()
    except Exception:
        pass
    # Если .env не сработал, просто вставь свой ключ сюда (в кавычках)
    return "MDE5Y2Q5MTktMDE1Zi03MTljLTlhMDEtMTYyZmU4NTdlZDJmOmY3NzMwNjhlLTU5YzctNDhmMi1hZTA5LTQ0MWJkOWVmZWI4NQ=="

def generate_outfit_via_llm(wardrobe: List[Dict], scenario: str, style: str) -> dict:
    GIGACHAT_CREDENTIALS = get_gigachat_key()

    if not GIGACHAT_CREDENTIALS:
        return {"explanation": "Ошибка: нет ключа GigaChat", "items": []}

    # 1. РАЗБИВАЕМ ВЕЩИ ПО КАТЕГОРИЯМ
    tops = [w for w in wardrobe if w['category'] in ['tshirt', 'shirt', 'sweater', 'hoodie']]
    bottoms = [w for w in wardrobe if w['category'] in ['jeans', 'trousers', 'shorts', 'skirt']]
    shoes = [w for w in wardrobe if w['category'] in ['sneakers', 'boots', 'shoes', 'loafers']]
    outerwear = [w for w in wardrobe if w['category'] in ['jacket', 'coat', 'blazer']]

    if not tops or not bottoms or not shoes:
        return {"explanation": "В гардеробе не хватает базовых вещей для сборки лука.", "items": []}

    # 2. ПИТОН СОБИРАЕТ 5 СЛУЧАЙНЫХ ЛУКОВ (Идеально правильных)
    candidate_outfits = []
    for i in range(1, 6):
        t = random.choice(tops)
        b = random.choice(bottoms)
        s = random.choice(shoes)
        
        outfit_desc = f"Лук #{i}:\n- Верх: {t['title']} (Цвет: {t['color']})\n- Низ: {b['title']} (Цвет: {b['color']})\n- Обувь: {s['title']} (Цвет: {s['color']})"
        item_ids = [t['id'], b['id'], s['id']]
        
        # Добавляем куртку иногда
        if outerwear and (random.random() < 0.4 or "дождь" in scenario.lower() or "офис" in scenario.lower()):
            o = random.choice(outerwear)
            outfit_desc += f"\n- Верхняя одежда: {o['title']} (Цвет: {o['color']})"
            item_ids.append(o['id'])
            
        candidate_outfits.append({
            "id": i,
            "desc": outfit_desc,
            "item_ids": item_ids
        })

    candidates_text = "\n\n".join([c["desc"] for c in candidate_outfits])

    # 3. НЕЙРОСЕТЬ ТОЛЬКО ВЫБИРАЕТ НОМЕР ЛУКА И ОБЪЯСНЯЕТ
    system_prompt = f"""
    Ты - профессиональный Fashion-стилист.
    Твоя задача - выбрать ОДИН лучший образ из 5 предложенных.
    
    СЦЕНАРИЙ (Куда идет клиент): {scenario}
    ОСОБЫЕ ПОЖЕЛАНИЯ КЛИЕНТА: {style}
    
    Вот 5 готовых образов на выбор:
    {candidates_text}
    
    ПРАВИЛА:
    1. Изучи пожелания клиента. Если он просит "бежевые штаны" или "спортзал", найди тот Лук, в котором вещи максимально подходят под этот запрос.
    2. Выбери только ОДИН лучший Лук (укажи его номер от 1 до 5).
    3. В поле explanation подробно распиши, ПОЧЕМУ этот лук подходит клиенту. ОБЯЗАТЕЛЬНО называй вещи теми же цветами, которые указаны в описании Лука! Не выдумывай яркие цвета, если ты выбрал черные вещи.
    4. Верни строго JSON.
    
    Формат ответа:
    {{
        "best_outfit_id": 3,
        "explanation": "Я выбрал Лук #3, потому что серые брюки отлично сочетаются с..."
    }}
    """

    try:
        with GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False) as giga:
            response = giga.chat({
                "model": "GigaChat-Pro",
                "messages": [
                    {"role": "system", "content": "Ты ИИ-стилист. Отвечай только валидным JSON."},
                    {"role": "user", "content": system_prompt}
                ],
                "temperature": 0.3
            })
            
            content = response.choices[0].message.content
            
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                content = content[start:end]
            else:
                raise ValueError("Не найден JSON в ответе")
                
            parsed_json = json.loads(content)
            
            chosen_id = parsed_json.get("best_outfit_id", 1)
            if not isinstance(chosen_id, int) or chosen_id < 1 or chosen_id > 5:
                chosen_id = 1
                
            final_item_ids = candidate_outfits[chosen_id - 1]["item_ids"]
            
            # ВОТ ОН: ГАРАНТИРОВАННЫЙ ВОЗВРАТ ПОЛНЫХ ОБЪЕКТОВ, ЧТОБЫ ТЕКСТ СОВПАДАЛ С КАРТИНКАМИ
            final_items = [w for w in wardrobe if w['id'] in final_item_ids]
            
            return {
                "explanation": parsed_json.get("explanation", "Вот отличный образ для тебя!"),
                "items": final_items # Возвращаем список объектов
            }
            
    except Exception as e:
        print(f"Ошибка GigaChat API: {e}")
        fallback_ids = candidate_outfits[0]["item_ids"] if candidate_outfits else []
        fallback_items = [w for w in wardrobe if w['id'] in fallback_ids]
        return {
            "explanation": "Стилист задумался, но вот отличный случайный образ для тебя!", 
            "items": fallback_items
        }
