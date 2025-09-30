import json

with open('ingredients.json', 'r', encoding='cp1251') as f:  # или 'latin1', если cp1251 не подходит
    data = json.load(f)

with open('ingredients_utf8.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)