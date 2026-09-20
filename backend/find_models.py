import os, requests
from dotenv import load_dotenv
load_dotenv('.env')

key = os.environ.get('GROQ_API_KEY')
res = requests.get('https://api.groq.com/openai/v1/models', headers={'Authorization': f'Bearer {key}'})
import json
data = res.json()
with open('models.json', 'w') as f:
    json.dump(data.get('data', []), f, indent=2)
