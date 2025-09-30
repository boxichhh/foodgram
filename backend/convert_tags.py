import json

with open('tags.json', 'r', encoding='cp1251') as f:
    data = json.load(f)

with open('tags_utf8.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)