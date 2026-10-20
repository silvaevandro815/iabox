"""
========================================================================================
MÓDULO 10: MOTOR COMPLETO SUNO OPEN-SOURCE (SUNO STUDIO & PARODY ENGINE)
========================================================================================
Engenharia Reversa da Arquitetura do Suno AI:
1. Compositor & Letrista (AI Lyricist):
   - Estruturação métrica com metatags musicais: [Verse], [Chorus], [Bridge], [Drop], [Outro].
   - Alinhamento de estilo: gênero musical, instrumentos, BPM, clima.
2. Motor de Música Completa (Full-Song Generation):
   - DiffRhythm (ASLP-lab) / YuE: Síntese de música completa com vocal + arranjo instrumental.
3. Clonagem Vocal no Canto (Personalized Persona):
   - Separação de stems com Demucs v4 (Meta AI).
   - Conversão de canto Zero-Shot via Seed-VC com afinação F0 automática.
   - Mixagem de masterização via FFmpeg.
4. Motor de Paródias Musicais (Parody Engine):
   - Isola o instrumental original de qualquer música famosa.
   - Aplica a nova letra cantada pela voz clonada com afinação perfeita no ritmo da música.
========================================================================================
"""

import os
import sys
import shutil
import argparse
import subprocess
import certifi
import requests
import json
from dotenv import dotenv_values

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

import gradio_client
from gradio_client import handle_file

class SunoStudioEngine:
    def __init__(self):
        self.env = dotenv_values('.env')
        self.gemini_key = self.env.get('GEMINI_API_KEY') or self.env.get('GOOGLE_API_KEY')
        self._diffrhythm_client = None
        self._demucs_client = None
        self._seed_vc_client = None

    def get_diffrhythm_client(self):
        if self._diffrhythm_client is None:
            print("[SunoEngine] Conectando ao cluster neural DiffRhythm...")
            self._diffrhythm_client = gradio_client.Client("ASLP-lab/DiffRhythm", httpx_kwargs={"timeout": 360.0})
        return self._diffrhythm_client

    def get_demucs_client(self):
        if self._demucs_client is None:
            print("[SunoEngine] Conectando ao separador de stems Demucs v4...")
            self._demucs_client = gradio_client.Client("abidlabs/music-separation", httpx_kwargs={"timeout": 300.0})
        return self._demucs_client

    def get_seed_vc_client(self):
        if self._seed_vc_client is None:
            print("[SunoEngine] Conectando ao motor de canto Seed-VC...")
            self._seed_vc_client = gradio_client.Client("Plachta/Seed-VC", httpx_kwargs={"timeout": 300.0})
        return self._seed_vc_client

    def compose_lyrics(self, theme, genre="sertanejo", duration_sec=95):
        """
        Gera letra estruturada com métrica musical e timestamps no padrão LRC/Suno.
        """
        print(f"\n[Suno Lyricist] Criando composição musical para tema: '{theme}' | Estilo: {genre}...")
        if not self.gemini_key:
            return self._fallback_lyrics(theme, genre)

        prompt = f"""
Você é um produtor musical e compositor profissional no estilo do Suno AI.
Crie a letra completa de uma música no gênero '{genre}' sobre o seguinte tema:
"{theme}"

A música deve ter duração total de aproximadamente {duration_sec} segundos.
Formate a letra EXATAMENTE no formato com timestamps em segundos para cada linha e metatags estruturais.
Exemplo:
[00:02.00] [Verse 1]
[00:05.00] Primeira frase cantada
[00:09.00] Segunda frase com melodia
[00:15.00] [Chorus]
[00:18.00] Refrão marcante e emocionante
[00:25.00] [Verse 2]
...
[01:20.00] [Outro]

Retorne APENAS o bloco de timestamps e letra, sem explicações ou introduções.
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={self.gemini_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            r = requests.post(url, json=payload, verify=False, timeout=30)
            if r.status_code == 200:
                lyrics = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                if lyrics.startswith('```') and lyrics.endswith('```'):
                    lines = lyrics.split('\n')[1:-1]
                    lyrics = '\n'.join(lines)
                print("[Suno Lyricist] Letra composta com sucesso!")
                print(lyrics[:250] + "...\n")
                return lyrics
        except Exception as e:
            print(f"[Suno Lyricist] Aviso: falha na API ({e}). Usando métrica padrão.")
        return self._fallback_lyrics(theme, genre)

    def _fallback_lyrics(self, theme, genre):
        return f"""[00:02.00] [Verse 1]
[00:05.00] Essa é uma canção no estilo {genre}
[00:09.00] Falando sobre {theme} com emoção
[00:15.00] [Chorus]
[00:18.00] O ritmo acelera e toca o coração
[00:24.00] Uma melodia feita com paixão
[00:32.00] [Verse 2]
[00:35.00] Cada nota afinada no compasso certo
[00:40.00] O som que contagia e chega perto
[00:48.00] [Chorus]
[00:52.00] O ritmo acelera e toca o coração
[01:05.00] [Outro]
[01:10.00] Finalizando essa canção"""

    def generate_full_song(self, lyrics, style_prompt, output_path="output/musica_suno.mp3", duration=95):
        """
        Gera a música completa (vocais + instrumentos) a partir de letra e prompt de estilo.
        """
        print(f"\n[Suno Engine] Gerando música completa via DiffRhythm...")
        print(f" -> Estilo / Prompt: {style_prompt}")
        print(f" -> Duração: {duration} segundos")

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
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

        shutil.copy(res, output_path)
        print(f" -> Música completa gerada com sucesso: {output_path}")
        return output_path

    def clone_singer_on_song(self, song_path, voice_reference_path, output_path="output/musica_com_sua_voz.mp3", pitch_shift=0):
        """
        Pega qualquer música gerada e substitui os vocais pela voz clonada do usuário.
        """
        import importlib
        mod = importlib.import_module("scripts.09_ai_song_cover_engine")
        cover_engine = mod.AISongCoverEngine()
        return cover_engine.create_ai_song_cover(
            song_path=song_path,
            user_voice_path=voice_reference_path,
            output_song=output_path,
            pitch_shift=pitch_shift
        )

    def create_parody(self, original_song_path, parody_vocal_guide, user_voice_path, output_path="output/parodia_final.mp3", pitch_shift=0):
        """
        Cria paródia musical: mantém o instrumental da música famosa e coloca a nova letra
        cantada com a sua voz clonada (ou de qualquer personagem) afinada perfeitamente.
        """
        print(f"\n[Suno Parody] Criando paródia da música: {original_song_path}...")
        # 1. Isola o instrumental da música original
        demucs = self.get_demucs_client()
        res = demucs.predict(audio=handle_file(original_song_path), api_name="/inference")
        instrumental = res[1]

        # 2. Converte a voz da guia da paródia para a voz clonada afinada
        seed_vc = self.get_seed_vc_client()
        converted_vocal = seed_vc.predict(
            source_audio_path=handle_file(parody_vocal_guide),
            target_audio_path=handle_file(user_voice_path),
            diffusion_steps=12,
            length_adjust=1.0,
            inference_cfg_rate=0.7,
            f0_condition=True,
            auto_f0_adjust=True,
            pitch_shift=float(pitch_shift),
            api_name="/predict_1"
        )[1]

        # 3. Mixa com o instrumental original
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", converted_vocal,
            "-i", instrumental,
            "-filter_complex",
            "[0:a]volume=1.0[v];[1:a]volume=0.9[i];[v][i]amix=inputs=2:duration=longest:dropout_transition=2",
            "-c:a", "libmp3lame",
            "-b:a", "320k",
            output_path
        ]
        subprocess.run(cmd, check=True)
        print(f"\n🎉 PARÓDIA CONCLUÍDA: {output_path}")
        return output_path

def main():
    parser = argparse.ArgumentParser(description="Motor Completo Suno AI Open-Source (Criação de Músicas e Paródias)")
    parser.add_argument("--mode", type=str, default="create", choices=["create", "parody", "lyrics"], help="Modo: create (música nova), parody (paródia com instrumental original), lyrics (só letra)")
    parser.add_argument("--theme", type=str, default="Amor e superação", help="Tema ou história da música")
    parser.add_argument("--genre", type=str, default="sertanejo pop, violao, sanfona e bateria", help="Gênero e instrumentos (ex: funk 130bpm, rock anos 80, trap, sertanejo)")
    parser.add_argument("--voice", type=str, default=None, help="Áudio de referência da voz clonada (1 minuto)")
    parser.add_argument("--song", type=str, default=None, help="Música original para paródia")
    parser.add_argument("--guide", type=str, default=None, help="Áudio da guia cantando a paródia")
    parser.add_argument("--out", type=str, default="output/musica_suno_final.mp3", help="Caminho do arquivo de saída")
    parser.add_argument("--duration", type=int, default=95, help="Duração da música em segundos (mínimo 95)")

    args = parser.parse_args()
    engine = SunoStudioEngine()

    if args.mode == "lyrics":
        lyrics = engine.compose_lyrics(args.theme, genre=args.genre, duration_sec=args.duration)
        print("\n--- LETRA GERADA ---\n", lyrics)

    elif args.mode == "create":
        lyrics = engine.compose_lyrics(args.theme, genre=args.genre, duration_sec=args.duration)
        raw_song = engine.generate_full_song(
            lyrics=lyrics,
            style_prompt=args.genre,
            output_path="output/temp_suno_song.mp3",
            duration=args.duration
        )

        if args.voice:
            engine.clone_singer_on_song(
                song_path=raw_song,
                voice_reference_path=args.voice,
                output_path=args.out
            )
        else:
            shutil.copy(raw_song, args.out)
            print(f"\n[SunoEngine] Música original gerada salva em: {args.out}")

    elif args.mode == "parody":
        if not args.song or not args.guide or not args.voice:
            print("[Erro] Modo parody exige --song (música original), --guide (guia cantada) e --voice (voz referência).")
            sys.exit(1)
        engine.create_parody(
            original_song_path=args.song,
            parody_vocal_guide=args.guide,
            user_voice_path=args.voice,
            output_path=args.out
        )

if __name__ == '__main__':
    main()
