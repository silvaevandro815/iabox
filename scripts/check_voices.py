import requests
from dotenv import dotenv_values

env = dotenv_values('.env')
key = env.get('ELEVENLABS_API_KEY')
r = requests.get('https://api.elevenlabs.io/v1/voices', headers={'xi-api-key': key})

if r.status_code == 200:
    voices = r.json()['voices']
    for v in voices:
        print(f"{v['name']} | ID: {v['voice_id']} | Labels: {v.get('labels')}")
else:
    print('Erro:', r.status_code, r.text)
