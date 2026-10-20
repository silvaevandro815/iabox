import os
import json
import base64
import requests
import urllib3
from dotenv import dotenv_values

urllib3.disable_warnings()

def transcribe_with_timestamps(audio_path, output_json_path):
    """
    Transcreve o áudio gerando timestamps precisos palavra por palavra e sentença por sentença
    usando a API do Gemini já configurada no .env.
    """
    env = dotenv_values('.env')
    api_key = env.get('GEMINI_API_KEY') or env.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("Chave de API não encontrada no .env!")

    with open(audio_path, 'rb') as f:
        audio_b64 = base64.b64encode(f.read()).decode('utf-8')

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    
    prompt = """
    Você é um motor de transcrição fonética profissional para motion design.
    Transcreva o áudio em português com altíssima fidelidade.
    Retorne OBRIGATORIAMENTE um JSON com a seguinte estrutura:
    {
      "duration_seconds": float,
      "segments": [
        {
          "start_sec": float,
          "end_sec": float,
          "text": string,
          "motion_concept": string (ex: "mapa", "casa_3d", "estudio_3d", "terra_3d", "dinheiro", "pergunta", "enfase"),
          "visual_effect_suggested": string (ex: "behind_head_3d", "vox_map_tracking", "background_fade_out", "hologram_card"),
          "words": [
            {"word": string, "start_sec": float, "end_sec": float}
          ]
        }
      ]
    }
    """

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "audio/wav",
                        "data": audio_b64
                    }
                }
            ]
        }],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    print(f"Enviando {audio_path} para transcrição com detecção de conceitos de motion design...")
    r = requests.post(url, json=payload, verify=False)
    
    if r.status_code == 200:
        result = r.json()['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(result)
        os.makedirs(os.path.dirname(output_json_path) or '.', exist_ok=True)
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Transcrição e mapa de motion salvos com sucesso em: {output_json_path}")
        return data
    else:
        raise RuntimeError(f"Erro na API ({r.status_code}): {r.text}")

if __name__ == "__main__":
    import sys
    audio_file = sys.argv[1] if len(sys.argv) > 1 else "temp_claudio_inspect/audio.wav"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "temp_claudio_inspect/motion_map.json"
    transcribe_with_timestamps(audio_file, out_file)
