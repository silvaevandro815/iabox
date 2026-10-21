"""
========================================================================================
MÓDULO 10: MOTOR COMPLETO SUNO OPEN-SOURCE (SUNO STUDIO & PARODY ENGINE)
========================================================================================
"""

import os
import sys
import uuid
import re
import shutil
import argparse
import subprocess
import certifi
import requests
from dotenv import dotenv_values

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

import gradio_client
from gradio_client import handle_file


class SunoStudioEngine:
    def __init__(self):
        env = dotenv_values('.env')
        if not env:
            env = os.environ
        self.env = env
        self.gemini_key = env.get('GEMINI_API_KEY') or env.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY', '')
        self.hf_token = env.get('HF_TOKEN') or env.get('HUGGINGFACE_TOKEN') or os.environ.get('HF_TOKEN', '')
        self._diffrhythm_client = None

    def get_diffrhythm_client(self):
        if self._diffrhythm_client is None:
            self._diffrhythm_client = gradio_client.Client(
                "ASLP-lab/DiffRhythm",
                token=self.hf_token or None,
                httpx_kwargs={"timeout": 240.0}
            )
        return self._diffrhythm_client

    def compose_lyrics(self, theme, genre="sertanejo", duration_sec=95):
        if not self.gemini_key:
            return self._fallback_lyrics(theme, genre)

        prompt = f"""Você é um produtor musical e compositor profissional no estilo do Suno AI.
Crie a letra completa em Português do Brasil de uma música no gênero '{genre}' sobre o tema: "{theme}".
Formate a letra com timestamps em segundos para cada linha:
[00:02.00] [Verse 1]
[00:05.00] Primeira frase cantada
[00:15.00] [Chorus]
[00:18.00] Refrão marcante
Retorne APENAS o bloco de timestamps e letra, sem explicações."""

        for m_name in ("gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash-preview"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={self.gemini_key}"
            try:
                r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
                if r.status_code == 200:
                    c_parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    for cp in c_parts:
                        if "text" in cp and not cp.get("thought", False):
                            lyrics = cp["text"].strip()
                            if lyrics:
                                return lyrics
            except Exception as e:
                print(f"[Suno Lyricist] Info ({e}).")
        return self._fallback_lyrics(theme, genre)

    def _fallback_lyrics(self, theme, genre):
        return f"""[00:02.00] [Verse 1]
[00:05.00] Essa é uma canção no estilo {genre}
[00:09.00] Falando sobre {theme} com emoção
[00:15.00] [Chorus]
[00:18.00] O ritmo acelera e toca o coração
[00:24.00] Uma melodia feita com paixão"""

    def generate_full_song(self, lyrics, style_prompt, output_path="output/musica_suno.mp3", duration=95):
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        try:
            client = self.get_diffrhythm_client()
            res = client.predict(
                lrc=lyrics,
                ref_audio_path=handle_file("https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav"),
                text_prompt=style_prompt,
                seed=42,
                randomize_seed=True,
                steps=25,
                cfg_strength=4.5,
                file_type="mp3",
                odeint_method="euler",
                preference_infer="quality first",
                Music_Duration=float(duration),
                api_name="/infer_music"
            )
            shutil.copy(str(res), output_path)
            return output_path
        except Exception as e:
            print(f"[SunoEngine] DiffRhythm nuvem ocupado ({e}). Sintetizando faixa musical vocal + harmonia local...")
            clean_lines = []
            for line in (lyrics or "").splitlines():
                txt = re.sub(r"\[.*?\]", "", line).strip()
                if txt:
                    clean_lines.append(txt)
            sung_text = ". ".join(clean_lines[:10]) or f"Canção original sobre {style_prompt}."

            from scripts.voice_clone_engine import VoiceCloneEngine
            v_eng = VoiceCloneEngine()
            vocal_tmp = output_path + ".vocal.mp3"
            v_eng.generate_neural_brazil(sung_text, output_path=vocal_tmp, voice="antonio")

            # Mixa vocal com base harmônica rítmica em lá menor / dó maior
            cmd = [
                "ffmpeg", "-y",
                "-i", vocal_tmp,
                "-f", "lavfi", "-i", "sine=frequency=110:duration=45",
                "-f", "lavfi", "-i", "sine=frequency=164.81:duration=45",
                "-f", "lavfi", "-i", "sine=frequency=220:duration=45",
                "-filter_complex",
                "[1:a][2:a][3:a]amix=inputs=3:duration=shortest,aecho=0.8:0.88:120:0.4,lowpass=f=900,volume=0.18[inst];"
                "[0:a]aecho=0.8:0.85:55:0.22,volume=1.2[voc];"
                "[voc][inst]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:a", "libmp3lame", "-b:a", "320k",
                output_path
            ]
            subprocess.run(cmd, capture_output=True)
            if not os.path.exists(output_path):
                shutil.copy(vocal_tmp, output_path)
            if os.path.exists(vocal_tmp):
                os.remove(vocal_tmp)
            return output_path

    def clone_singer_on_song(self, song_path, voice_reference_path, output_path="output/musica_com_sua_voz.mp3", pitch_shift=0):
        import importlib
        mod = importlib.import_module("scripts.09_ai_song_cover_engine")
        cover_engine = mod.AISongCoverEngine()
        return cover_engine.create_ai_song_cover(
            song_path=song_path,
            user_voice_path=voice_reference_path,
            output_song=output_path,
            pitch_shift=pitch_shift
        )

    def create_parody(self, original_song_path, parody_vocal_guide=None, user_voice_path=None, output_path="output/parodia_final.mp3", pitch_shift=0, use_original_singer=False, lyrics=""):
        import importlib
        mod = importlib.import_module("scripts.09_ai_song_cover_engine")
        cover_engine = mod.AISongCoverEngine()

        # 1. Separa instrumental e o vocal original isolado dos cantores (ex: Jeninho & Mariana Fagundes)
        isolated_vocals, instrumental = cover_engine.separate_vocals_and_instrumental(original_song_path)

        # 2. Se for modo "Manter Cantores Originais", a voz de referência é o próprio vocal isolado da faixa
        target_voice = isolated_vocals if (use_original_singer or not user_voice_path) else user_voice_path

        # 3. Se não houver áudio guia mas houver letra escrita, sintetiza guia neural brasileiro
        actual_guide = parody_vocal_guide
        if not actual_guide and lyrics:
            try:
                from scripts.voice_clone_engine import VoiceCloneEngine
                v_eng = VoiceCloneEngine()
                guide_tmp = os.path.join("output/stems", f"neural_guide_{uuid.uuid4().hex[:6]}.mp3")
                v_eng.generate_neural_brazil(lyrics, output_path=guide_tmp, voice="antonio")
                if os.path.exists(guide_tmp):
                    actual_guide = guide_tmp
            except Exception as e:
                print(f"[ParodyEngine] Síntese de guia vocal neural: {e}")

        if not actual_guide:
            actual_guide = isolated_vocals

        # 4. Converte a melodia e as palavras da nova letra para o timbre dos cantores
        converted_vocal = cover_engine.convert_singing_voice(
            actual_guide,
            target_voice,
            output_path=os.path.join("output/stems", f"parody_voc_{uuid.uuid4().hex[:6]}.wav"),
            pitch_shift=pitch_shift
        )

        # 5. Mixa o vocal com a nova letra sobre o instrumental original da música
        return cover_engine.mix_vocals_and_instrumental(
            converted_vocal,
            instrumental,
            output_song=output_path
        )
