import re
with open('templates/base.html', 'r', encoding='utf-8') as f:
    data = f.read()
new_data = re.sub(r'<style>.*?</style>', '<link rel="stylesheet" href="{% static \"css/base.css\" %}">', data, flags=re.DOTALL)
with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(new_data)