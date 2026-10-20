"""
========================================================================================
MÓDULO 09: MOTOR DE SUBSTITUIÇÃO VOCAL EM MÚSICAS (AI SONG COVER ENGINE)
========================================================================================
1. Stem Separation (Demucs v4 / Meta):
   - Isola o vocal do cantor original ('vocals.wav') e o instrumental ('instrumental.wav').
2. Zero-Shot Singing Voice Conversion (Seed-VC com F0 Pitch Tracking):
   - Transfere o timbre vocal do usuário para a melodia cantada original,
     preservando 100% da afinação, notas, vibrato e tempo da música.
3. Masterização e Mixagem (FFmpeg):
   - Junta o vocal convertido com o instrumental original sem perda de qualidade.
========================================================================================
"""

import os
import sys
import shutil
import argparse
import subprocess
import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

import gradio_client
from gradio_client import handle_file

class AISongCoverEngine:
    def __init__(self, demucs_space="abidlabs/music-separation", seed_vc_space="Plachta/Seed-VC"):
        self.demucs_space = demucs_space
        self.seed_vc_space = seed_vc_space
        self._demucs_client = None
        self._seed_vc_client = None

    def get_demucs_client(self):
        if self._demucs_client is None:
            print(f"[AI Cover] Conectando ao motor de separação musical Demucs v4 ({self.demucs_space})...")
            self._demucs_client = gradio_client.Client(self.demucs_space, httpx_kwargs={"timeout": 300.0})
        return self._demucs_client

    def get_seed_vc_client(self):
        if self._seed_vc_client is None:
            print(f"[AI Cover] Conectando ao motor neural de conversão de canto Seed-VC ({self.seed_vc_space})...")
            self._seed_vc_client = gradio_client.Client(self.seed_vc_space, httpx_kwargs={"timeout": 300.0})
        return self._seed_vc_client

    def separate_vocals_and_instrumental(self, song_path, output_dir="output/stems"):
        print(f"\n[Passo 1/3] Isolando voz e instrumental da música: {song_path}")
        os.makedirs(output_dir, exist_ok=True)

        client = self.get_demucs_client()
        res = client.predict(audio=handle_file(song_path), api_name="/inference")

        vocals_tmp, inst_tmp = res[0], res[1]

        vocals_dest = os.path.join(output_dir, "vocals.wav")
        inst_dest = os.path.join(output_dir, "instrumental.wav")

        shutil.copy(vocals_tmp, vocals_dest)
        shutil.copy(inst_tmp, inst_dest)

        print(f" -> Vocal do cantor isolado: {vocals_dest}")
        print(f" -> Instrumental limpo: {inst_dest}")
        return vocals_dest, inst_dest

    def convert_singing_voice(self, original_vocals_path, user_voice_path, output_path="output/vocal_clonado.wav", pitch_shift=0, diffusion_steps=10):
        print(f"\n[Passo 2/3] Transferindo a melodia e afinação para a sua voz...")
        print(f" -> Vocal original: {original_vocals_path}")
        print(f" -> Voz de referência: {user_voice_path}")
        print(f" -> Pitch shift: {pitch_shift} semitons | Passos de difusão: {diffusion_steps}")

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        client = self.get_seed_vc_client()
        res = client.predict(
            source_audio_path=handle_file(original_vocals_path),
            target_audio_path=handle_file(user_voice_path),
            diffusion_steps=float(diffusion_steps),
            length_adjust=1.0,
            inference_cfg_rate=0.7,
            f0_condition=True,
            auto_f0_adjust=True,
            pitch_shift=float(pitch_shift),
            api_name="/predict_1"
        )

        stream_out, full_out = res[0], res[1]
        chosen_audio = full_out if os.path.exists(full_out) else stream_out

        shutil.copy(chosen_audio, output_path)
        print(f" -> Vocal cantado com sua voz concluído: {output_path}")
        return output_path

    def mix_vocals_and_instrumental(self, converted_vocals, instrumental, output_song="output/musica_cover_final.mp3", vocal_vol=1.0, inst_vol=1.0):
        print(f"\n[Passo 3/3] Mixando sua nova voz com o instrumental original via FFmpeg...")
        os.makedirs(os.path.dirname(output_song) or '.', exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-i", converted_vocals,
            "-i", instrumental,
            "-filter_complex",
            f"[0:a]volume={vocal_vol}[v];[1:a]volume={inst_vol}[i];[v][i]amix=inputs=2:duration=longest:dropout_transition=2",
            "-c:a", "libmp3lame",
            "-b:a", "320k",
            output_song
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print("[FFmpeg Erro]", result.stderr)
            raise RuntimeError(f"Erro ao mixar áudios: {result.stderr}")

        print(f"\n🎈 MÚSICA COVER CONCLuÍDA COM SUCESSO!")
        print(f" -> Arquivo final: {output_song}")
        return output_song

    def create_ai_song_cover(self, song_path, user_voice_path, output_song="output/musica_cover_final.mp3", pitch_shift=0, diffusion_steps=10):
        print("=" * 75)
        print("INICIANDO PIPELINE DE CRIACÃO DE AI COVER MUSICAL")
        print("=" * 75)

        vocals, instrumental = self.separate_vocals_and_instrumental(song_path)

        converted_vocals = self.convert_singing_voice(
            vocals,
            user_voice_path,
            output_path="output/stems/vocal_cantado_convertido.wav",
            pitch_shift=pitch_shift,
            diffusion_steps=diffusion_steps
        )

        final_song = self.mix_vocals_and_instrumental(
            converted_vocals,
            instrumental,
            output_song=output_song
        )

        return final_song

def main():
    parser = argparse.ArgumentParser(description="Motor de Substituição Vocal em Múlicas (AI Song Cover)")
    parser.add_argument("--song", type=str, required=True, help="Caminho da gravação da música original")
    parser.add_argument("--voice", type=str, required=True, help="Caminho da sua voz de referência")
    parser.add_argument("--out", type=str, default="output/musica_cover_final.mp3", help="Caminho do arquivo final")
    parser.add_argument("--pitch", type=int, default=0, help="Ajuste de semitons de afinação (ex: 0, 12, -12)")
    parser.add_argument("--steps", type=int, default=10, help="Passos de difusão neural")

    args = parser.parse_args()
    engine = AISongCoverEngine()
    engine.create_ai_song_cover(
        song_path=args.song,
        user_voice_path=args.voice,
        output_song=args.out,
        pitch_shift=args.pitch,
        diffusion_steps=args.steps
    )

if __name__ == '__main__':
    main()
