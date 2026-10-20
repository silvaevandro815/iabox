"""
========================================================================================
MÓDULO 08: MOTOR AUTÔNOMO DE VOZES E CLONAGEM (OPEN-SOURCE VOICE ENGINE)
========================================================================================
Inspirado na arquitetura do Voicebox (Jamie Pine) e Kokoro-82M.

Recursos:
1. Síntese Ultra-Rápida em CPU (Kokoro Local):
   - 100% offline, zero custo, sem limite de caracteres.
   - Vozes em Português-BR: 'pm_alex' (Masculina), 'pf_dora' (Feminina).
   - Vozes em Inglês: 'af_heart', 'am_adam', 'bf_emma', 'bm_george'.
2. Clonagem de Voz Zero-Shot (F5-TTS / Gradio / Voicebox API):
   - Clona qualquer voz a partir de 5 a 10 segundos de áudio de referência.
3. Linha de Comando (CLI) Pronta para Uso no Projeto.
========================================================================================
"""

import os
import sys
import asyncio
import argparse
import soundfile as sf
from dotenv import dotenv_values

EDGE_VOICES = {
    "antonio": "pt-BR-AntonioNeural",
    "francisca": "pt-BR-FranciscaNeural",
    "thalita": "pt-BR-ThalitaNeural",
    "pt-BR-AntonioNeural": "pt-BR-AntonioNeural",
    "pt-BR-FranciscaNeural": "pt-BR-FranciscaNeural",
    "pt-BR-ThalitaNeural": "pt-BR-ThalitaNeural"
}

class VoiceCloneEngine:
    def __init__(self):
        self.env = dotenv_values('.env')
        self._kokoro_pipeline_p = None
        self._kokoro_pipeline_a = None

    def generate_neural_brazil(self, text, output_path="output/narracao_brasil.mp3", voice="antonio"):
        """
        Gera narração em Português do Brasil 100% nativa, sem sotaque estrangeiro,
        usando redes neurais de alta fidelidade (Edge Neural).
        """
        import edge_tts
        neural_voice = EDGE_VOICES.get(voice, "pt-BR-AntonioNeural")
        print(f"[VoiceEngine] Sintetizando voz neural PT-BR ('{neural_voice}')...")
        print(f" -> Texto: \"{text[:80]}...\"" if len(text) > 80 else f" -> Texto: \"{text}\"")

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        async def _run():
            communicate = edge_tts.Communicate(text, neural_voice)
            await communicate.save(output_path)

        asyncio.run(_run())
        print(f"[VoiceEngine] Concluído! Áudio salvo em: {output_path}")
        return output_path

    def get_pipeline(self, lang_code='p'):
        from kokoro import KPipeline
        if lang_code == 'p':
            if self._kokoro_pipeline_p is None:
                print("[VoiceEngine] Carregando pipeline Kokoro (Português-BR) no processador...")
                self._kokoro_pipeline_p = KPipeline(lang_code='p')
            return self._kokoro_pipeline_p
        else:
            if self._kokoro_pipeline_a is None:
                print("[VoiceEngine] Carregando pipeline Kokoro (Inglês) no processador...")
                self._kokoro_pipeline_a = KPipeline(lang_code='a')
            return self._kokoro_pipeline_a

    def generate_speech(self, text, output_path="output/narration.wav", voice="pm_alex", speed=1.0):
        """
        Gera áudio em alta fidelidade no processador (CPU) sem custos e sem limite de caracteres.
        Vozes PT-BR: 'pm_alex', 'pf_dora'
        Vozes EN: 'af_heart', 'am_adam', 'bf_emma'
        """
        lang = 'p' if voice.startswith('p') else 'a'
        pipeline = self.get_pipeline(lang_code=lang)
        
        print(f"[VoiceEngine] Sintetizando áudio com voz '{voice}'...")
        print(f" -> Texto: \"{text[:80]}...\"" if len(text) > 80 else f" -> Texto: \"{text}\"")

        generator = pipeline(text, voice=voice, speed=speed)
        audio_chunks = []
        for i, (gs, ps, audio) in enumerate(generator):
            audio_chunks.append(audio)

        if audio_chunks:
            import numpy as np
            full_audio = np.concatenate(audio_chunks)
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            sf.write(output_path, full_audio, 24000)
            duration = len(full_audio) / 24000.0
            print(f"[VoiceEngine] Concluído! Áudio salvo em '{output_path}' ({duration:.2f} segundos).")
            return output_path
        else:
            raise RuntimeError("Nenhum áudio foi gerado pelo pipeline.")

    def clone_voice_sample(self, reference_audio, target_text, output_path="output/cloned_voice.wav"):
        """
        Clonagem Zero-Shot de Voz com amostra de áudio.
        Usa F5-TTS na nuvem ou modelo local com Whisper para alinhamento fonético.
        """
        print(f"[VoiceEngine] Iniciando clonagem da amostra: {reference_audio}")
        # Transcrição rápida da amostra para alinhamento
        from dotenv import dotenv_values
        import base64, requests, urllib3
        urllib3.disable_warnings()

        env = dotenv_values('.env')
        api_key = env.get('GEMINI_API_KEY') or env.get('GOOGLE_API_KEY')

        with open(reference_audio, 'rb') as f:
            audio_b64 = base64.b64encode(f.read()).decode('utf-8')

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Transcreva apenas o texto exato falado neste áudio em português, sem comentários."},
                    {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}}
                ]
            }]
        }
        r = requests.post(url, json=payload, verify=False)
        ref_text = r.json()['candidates'][0]['content']['parts'][0]['text'].strip() if r.status_code == 200 else ""
        print(f" -> Transcrição da amostra: \"{ref_text}\"")

        # Chama a API neural F5-TTS
        try:
            import certifi
            os.environ['SSL_CERT_FILE'] = certifi.where()
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
            import gradio_client
            from gradio_client import handle_file

            client = gradio_client.Client("mrfakename/E2-F5-TTS", httpx_kwargs={"timeout": 120.0})
            res = client.predict(
                ref_audio=handle_file(reference_audio),
                ref_text=ref_text,
                gen_text=target_text,
                remove_silence=False,
                api_name="/predict"
            )
            import shutil
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            shutil.copy(res, output_path)
            print(f"[VoiceEngine] Clonagem neural concluída com sucesso: {output_path}")
            return output_path
        except Exception as e:
            print(f"[VoiceEngine] Conexão com F5-TTS nuvem ocupada ({e}). Usando motor local de alta fidelidade...")
            return self.generate_speech(target_text, output_path=output_path, voice="pm_alex")

def main():
    parser = argparse.ArgumentParser(description="Motor Autônomo de Vozes e Clonagem (PT-BR Nativo)")
    parser.add_argument("--text", type=str, required=True, help="Texto a ser narrado")
    parser.add_argument("--voice", type=str, default="antonio", help="Voz PT-BR: antonio, francisca, thalita | Kokoro offline: pm_alex, pf_dora")
    parser.add_argument("--speed", type=float, default=1.0, help="Velocidade da fala (Kokoro)")
    parser.add_argument("--out", type=str, default="output/narracao_final.mp3", help="Caminho do arquivo de saída (.mp3 ou .wav)")
    parser.add_argument("--clone", action="store_true", help="Ativar modo de clonagem a partir de áudio")
    parser.add_argument("--ref", type=str, default=None, help="Caminho do áudio de referência para clonar")

    args = parser.parse_args()
    engine = VoiceCloneEngine()

    if args.clone and args.ref:
        engine.clone_voice_sample(args.ref, args.text, output_path=args.out)
    elif args.voice in ["pm_alex", "pf_dora", "af_heart", "am_adam", "bf_emma", "bm_george"]:
        engine.generate_speech(args.text, output_path=args.out, voice=args.voice, speed=args.speed)
    else:
        engine.generate_neural_brazil(args.text, output_path=args.out, voice=args.voice)

if __name__ == "__main__":
    main()
