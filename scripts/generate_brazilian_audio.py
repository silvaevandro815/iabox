import requests
import json
from dotenv import dotenv_values

env = dotenv_values('.env')
key = env.get('ELEVENLABS_API_KEY')

# Márcio Duarte: Voz 100% nativa do Brasil (accent: brazilian, deep, narrative_story)
voice_id = "cXmaMIwfUQ3FpdM3KmoB"
url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

text = (
    "Fala Evandro! Esta voz é cem por cento em português do Brasil, "
    "sem nenhum sotaque estrangeiro, com dicção limpa, naturalidade absoluta "
    "e pronta para narrar os nossos vídeos virais."
)

payload = {
    "text": text,
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
        "stability": 0.65,
        "similarity_boost": 0.90,
        "style": 0.25,
        "use_speaker_boost": True
    }
}

headers = {
    "xi-api-key": key,
    "Content-Type": "application/json"
}

print(f"Gerando áudio com a voz brasileira nativa 'Márcio Duarte' (ID: {voice_id})...")
r = requests.post(url, json=payload, headers=headers)

output_file = "output/narracao_brasileira_10s.mp3"

if r.status_code == 200:
    with open(output_file, "wb") as f:
        f.write(r.content)
    print(f"Áudio brasileiro nativo gerado com sucesso em: {output_file}")
else:
    print(f"Erro ao gerar áudio ({r.status_code}): {r.text}")
