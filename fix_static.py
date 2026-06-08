import re

file_path = 'main.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = 'app = FastAPI(title="Heimdall", description="Malaysian Address Parser for EasyParcel")'
replacement = target + """
import os
if not os.path.exists('static'):
    os.makedirs('static')
app.mount('/static', StaticFiles(directory='static'), name='static')
"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Static mount added!")
else:
    print("Target not found!")
