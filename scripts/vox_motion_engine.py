"""
========================================================================================
IABOX VOX MOTION ENGINE™ — MOTOR DE VÍDEO MULTI-CENA & COLAGEM EDITORIAL 2.5D
========================================================================================
Inspirado nas animações de alto engajamento (Estilo Vox / Explainer Editorial),
permite ao criador de conteúdo:
1. Enviar um roteiro geral e desmembrar em N cenas de 5 a 10 segundos com IA.
2. Cada cena recebe prompts, motion graphics dinâmicos e até 3 imagens de referência.
3. Transforma automaticamente as imagens no estilo visual selecionado (ex: Estilo Vox,
   Motion Graphics 2D, 3D Cinematográfico, Cyberpunk Neon, Comic Pop Art, Anime).
4. Renderiza clipes individuais de 5-10s ou concatena o vídeo master completo (1 minuto+).
5. Compatível com aceleração por cluster GPU na RunPod.io ou render rápido na VPS.
========================================================================================
"""

import os
import sys
import uuid
import json
import math
import time
import random
import base64
import shutil
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance
import numpy as np
from dotenv import dotenv_values

class VoxMotionEngine:
    def __init__(self, env_path=None):
        env = {}
        if env_path and os.path.exists(env_path):
            env = dotenv_values(env_path)
        if not env:
            if os.path.exists(".env"):
                env = dotenv_values(".env")
            elif os.path.exists("../.env"):
                env = dotenv_values("../.env")
            else:
                env = os.environ

        self.gemini_key = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
        self.openrouter_key = env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
        self.runpod_key = env.get("RUNPOD_API_KEY") or os.environ.get("RUNPOD_API_KEY", "")

        self.styles = {
            "vox": {
                "id": "vox",
                "name": "Estilo Vox (Colagem Editorial Vintage)",
                "desc": "Papel rasgado, texturas de jornal antigo, retícula halftone, halo amarelo vibrante, moedas caindo e tipografia serif retrô.",
                "bg_color": (24, 24, 27),
                "accent_color": (250, 204, 21), # Amarelo Vox
                "secondary_color": (25, 120, 175), # Azul Céu
                "has_torn_paper": True,
                "has_halo": True,
                "motion_types": ["moedas_caindo", "zoom_parallax", "engrenagens", "nuvens_deriva", "revelacao_papel"]
            },
            "motion_graphics": {
                "id": "motion_graphics",
                "name": "Motion Graphics 2D (Explainer Tech Minimalista)",
                "desc": "Visual corporativo limpo, formas geométricas vetorizadas, dados infográficos flutuantes e paleta ciano/ardósia moderna.",
                "bg_color": (15, 23, 42), # Slate 900
                "accent_color": (6, 182, 212), # Ciano 500
                "secondary_color": (59, 130, 246), # Azul 500
                "has_torn_paper": False,
                "has_halo": False,
                "motion_types": ["grafico_barras", "hud_tech", "zoom_isometrico", "vetores_flutuantes"]
            },
            "cinema_3d": {
                "id": "cinema_3d",
                "name": "3D Render Cinematográfico (Unreal / Octane)",
                "desc": "Iluminação volumétrica dramática, sombras suaves de estúdio, texturas foto-realistas e profundidade de campo rasa.",
                "bg_color": (10, 10, 15),
                "accent_color": (245, 158, 11), # Âmbar
                "secondary_color": (99, 102, 241), # Indigo
                "has_torn_paper": False,
                "has_halo": True,
                "motion_types": ["camera_dolly", "luz_volumetrica", "bokeh_flutuante", "profundidade_3d"]
            },
            "cyberpunk": {
                "id": "cyberpunk",
                "name": "Dark Cyberpunk Neon",
                "desc": "Contraste extremo, reflexos de asfalto molhado, neon laser ciano e magenta, interface HUD holográfica e fumaça volumétrica.",
                "bg_color": (10, 12, 20),
                "accent_color": (6, 182, 212), # Ciano Laser
                "secondary_color": (244, 63, 94), # Rose/Neon
                "has_torn_paper": False,
                "has_halo": True,
                "motion_types": ["glitch_suave", "neon_pulso", "grid_perspectiva", "scanline_hud"]
            },
            "comic_pop": {
                "id": "comic_pop",
                "name": "HQ & Pop Art (Graphic Novel Vintage)",
                "desc": "Pontos Ben-Day de impressão, contornos pretos expressivos, balões de diálogo, onomatopeias e cores chapadas vibrantes.",
                "bg_color": (255, 251, 235), # Off-white vintage
                "accent_color": (239, 68, 68), # Vermelho Comic
                "secondary_color": (234, 179, 8), # Amarelo Comic
                "has_torn_paper": True,
                "has_halo": False,
                "motion_types": ["linhas_acao", "zoom_impacto", "quadro_destaque"]
            },
            "anime": {
                "id": "anime",
                "name": "Ilustração Anime & Studio Ghibli",
                "desc": "Céus em aquarela com nuvens volumosas, luz natural suave, paleta nostálgica pintada à mão e atmosfera pacífica.",
                "bg_color": (20, 30, 45),
                "accent_color": (56, 189, 248), # Sky
                "secondary_color": (251, 191, 36), # Sunset
                "has_torn_paper": False,
                "has_halo": True,
                "motion_types": ["nuvens_ghibli", "particulas_luz", "pan_aquarela"]
            }
        }

    # ----------------------------------------------------------------------------------------
    # 1. INTELIGÊNCIA ARTIFICIAL: DESMEMBRAR ROTEIRO EM CENAS (BEATS)
    # ----------------------------------------------------------------------------------------
    def split_script_with_ai(
        self,
        script_text: str,
        num_scenes: int = 6,
        style: str = "vox",
        sec_per_scene: float = 10.0
    ) -> List[Dict]:
        """
        Usa o Gemini / OpenRouter para analisar o roteiro ou tema e transformá-lo em
        um plano de corte multi-cena rigorosamente estruturado dentro do estilo selecionado.
        """
        style_info = self.styles.get(style, self.styles["vox"])
        num_scenes = max(2, min(int(num_scenes), 16))
        sec_per_scene = max(5.0, min(float(sec_per_scene), 15.0))

        system_prompt = f"""Você é o Diretor Criativo Principal especializado em vídeos curtos virais de alto engajamento (Shorts, Reels, TikTok) no {style_info['name']}.
Sua missão é pegar o roteiro/ideia abaixo e transformá-lo EXATAMENTE em {num_scenes} cenas sequenciais de {sec_per_scene}s cada (compondo um vídeo de alto dinamismo).

Diretrizes Visuais para o {style_info['name']}:
- {style_info['desc']}
- Cada cena deve ter:
  1. "headline": Palavra de impacto curta em caixa alta (ex: "ESTILO", "PRONTO.", "FUTURO", "IMPACTO", "SEGREDO").
  2. "prompt": Descrição visual detalhada do elemento central e composição (em português ou inglês para o gerador de arte).
  3. "motion": Tipo de movimento sugerido (ex: 'moedas_caindo', 'zoom_parallax', 'revelacao_papel', 'engrenagens').
  4. "narration": Texto da narração falada / legenda desta cena (frase concisa de 1 a 2 linhas, direta e magnética).
  5. "duration": {sec_per_scene}.

Responda ESTRITAMENTE um JSON ARRAY com {num_scenes} objetos. Não inclua texto antes ou depois."""

        user_content = f"ROTEIRO OU TEMA DO VÍDEO:\n{script_text}\n\nDivida em exatamente {num_scenes} cenas."

        res = self._call_ai(system_prompt, user_content)
        if res:
            try:
                clean_json = res.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                
                scenes = json.loads(clean_json)
                if isinstance(scenes, list) and len(scenes) > 0:
                    formatted_scenes = []
                    for idx, s in enumerate(scenes[:num_scenes]):
                        formatted_scenes.append({
                            "scene_number": idx + 1,
                            "headline": s.get("headline", f"CENA {idx+1}")[:20].upper(),
                            "prompt": s.get("prompt", "Cena editorial estilizada")[:500],
                            "motion": s.get("motion", "zoom_parallax"),
                            "narration": s.get("narration", "")[:250],
                            "duration": sec_per_scene,
                            "reference_images": []
                        })
                    return formatted_scenes
            except Exception as e:
                print(f"[VoxMotionEngine] Falha ao decodificar JSON da IA: {e}")

        return self._generate_fallback_scenes(script_text, num_scenes, sec_per_scene, style)

    def _generate_fallback_scenes(self, script_text: str, num_scenes: int, sec_per_scene: float, style: str) -> List[Dict]:
        words = script_text.strip().split()
        chunk_size = max(1, len(words) // num_scenes)
        headlines = ["O IMPACTO", "O PROBLEMA", "A VIRADA", "COMO FUNCIONA", "O RESULTADO", "COMECE AGORA", "O FUTURO", "DESCUBRA"]
        motions = ["zoom_parallax", "moedas_caindo", "revelacao_papel", "engrenagens", "zoom_parallax", "revelacao_papel"]

        scenes = []
        for i in range(num_scenes):
            sub_words = words[i * chunk_size : (i + 1) * chunk_size] if words else []
            narration = " ".join(sub_words) if sub_words else f"Cena {i+1} do vídeo em alta definição."
            scenes.append({
                "scene_number": i + 1,
                "headline": headlines[i % len(headlines)],
                "prompt": f"Elemento central editorial estilo {style} ilustrando: {narration[:80]}",
                "motion": motions[i % len(motions)],
                "narration": narration[:250],
                "duration": sec_per_scene,
                "reference_images": []
            })
        return scenes

    def _call_ai(self, system_prompt: str, user_content: str) -> Optional[str]:
        if self.gemini_key:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_content}"}]}],
                    "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048}
                }
                r = requests.post(url, json=payload, timeout=20)
                if r.status_code == 200:
                    d = r.json()
                    candidates = d.get("candidates", [])
                    if candidates:
                        return candidates[0]["content"]["parts"][0]["text"]
            except Exception as e:
                print(f"[VoxMotionEngine] Gemini API error: {e}")

        if self.openrouter_key:
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.4
                }
                r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
                if r.status_code == 200:
                    d = r.json()
                    return d["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[VoxMotionEngine] OpenRouter API error: {e}")
        return None

    # ----------------------------------------------------------------------------------------
    # 2. TRATAMENTO VISUAL: ESTILIZAR FOTOS DE REFERÊNCIA (RECORTE, RASGO E EFEITO VOX)
    # ----------------------------------------------------------------------------------------
    def stylize_reference_image(self, input_path: str, style: str = "vox", output_path: str = None) -> str:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Imagem não encontrada: {input_path}")

        if not output_path:
            os.makedirs("output", exist_ok=True)
            output_path = os.path.join("output", f"styled_{uuid.uuid4().hex[:8]}.png")

        orig = Image.open(input_path).convert("RGBA")
        ow, oh = orig.size

        if style == "vox":
            gray = orig.convert("L")
            contrasted = ImageEnhance.Contrast(gray).enhance(1.4)
            styled_sub = ImageOps.colorize(contrasted, black=(25, 25, 30), white=(245, 240, 230)).convert("RGBA")

            mask = Image.new("L", (ow, oh), 0)
            m_draw = ImageDraw.Draw(mask)
            
            points = []
            step = max(10, ow // 40)
            for x in range(0, ow, step):
                points.append((x, int(random.uniform(8, 24))))
            for y in range(0, oh, step):
                points.append((ow - int(random.uniform(8, 24)), y))
            for x in range(ow, 0, -step):
                points.append((x, oh - int(random.uniform(8, 24))))
            for y in range(oh, 0, -step):
                points.append((int(random.uniform(8, 24)), y))

            m_draw.polygon(points, fill=255)
            styled_sub.putalpha(mask)

            border_layer = Image.new("RGBA", (ow, oh), (255, 255, 255, 0))
            b_draw = ImageDraw.Draw(border_layer)
            b_draw.polygon(points, outline=(255, 255, 250, 255), width=max(12, ow // 50))
            
            final = Image.alpha_composite(styled_sub, border_layer)
            final.save(output_path, "PNG")

        elif style == "cyberpunk":
            tinted = ImageOps.colorize(orig.convert("L"), black=(8, 12, 24), white=(0, 240, 255)).convert("RGBA")
            final = ImageEnhance.Brightness(tinted).enhance(1.2)
            final.save(output_path, "PNG")

        elif style == "comic_pop":
            enh = ImageEnhance.Color(orig).enhance(1.8)
            final = ImageEnhance.Contrast(enh).enhance(1.6).convert("RGBA")
            final.save(output_path, "PNG")

        else:
            orig.save(output_path, "PNG")

        return output_path

    # ----------------------------------------------------------------------------------------
    # 3. RENDERIZADOR DE CENA: GERA VÍDEO DE 5 A 10 SEGUNDOS COM MOTION GRAPHICS
    # ----------------------------------------------------------------------------------------
    def generate_scene_clip(
        self,
        scene_data: Dict,
        style: str = "vox",
        duration: float = 7.0,
        ref_images: List[str] = None,
        output_mp4: str = None,
        runpod_mode: bool = False
    ) -> str:
        duration = max(4.0, min(float(duration), 15.0))
        if not output_mp4:
            os.makedirs("output", exist_ok=True)
            output_mp4 = os.path.join("output", f"vox_scene_{uuid.uuid4().hex[:8]}.mp4")

        cw, ch = 1080, 1920
        fps = 30
        total_frames = int(duration * fps)

        styled_ref = None
        if ref_images and len(ref_images) > 0 and os.path.exists(ref_images[0]):
            styled_ref = self.stylize_reference_image(ref_images[0], style)

        headline = scene_data.get("headline", "ESTILO VOX")
        prompt = scene_data.get("prompt", "Cena editorial")
        motion_type = scene_data.get("motion", "moedas_caindo")
        narration = scene_data.get("narration", "")

        work_dir = os.path.join("output", f"frames_{uuid.uuid4().hex[:8]}")
        os.makedirs(work_dir, exist_ok=True)

        try:
            self._render_animated_frames(
                work_dir=work_dir,
                cw=cw, ch=ch,
                total_frames=total_frames,
                fps=fps,
                style=style,
                headline=headline,
                prompt=prompt,
                motion_type=motion_type,
                narration=narration,
                styled_ref_path=styled_ref
            )

            raw_video = os.path.join(work_dir, "raw_video.mp4")
            input_pattern = os.path.join(work_dir, "frame_%04d.jpg")
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", input_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "veryfast",
                "-crf", "20",
                raw_video
            ]
            subprocess.run(cmd, capture_output=True, timeout=120)

            # Anexa áudio de silêncio ou sfx da duração exata do clipe
            self._add_scene_sfx(raw_video, output_mp4, duration=duration)

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        return output_mp4

    def _render_animated_frames(
        self,
        work_dir: str,
        cw: int, ch: int,
        total_frames: int,
        fps: int,
        style: str,
        headline: str,
        prompt: str,
        motion_type: str,
        narration: str,
        styled_ref_path: Optional[str]
    ):
        try:
            font_title = ImageFont.truetype("times.ttf", 110)
            font_sub = ImageFont.truetype("arial.ttf", 34)
            font_narration = ImageFont.truetype("arial.ttf", 32)
        except Exception:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_narration = ImageFont.load_default()

        sub_img = None
        if styled_ref_path and os.path.exists(styled_ref_path):
            try:
                raw = Image.open(styled_ref_path).convert("RGBA")
                target_w = int(cw * 0.80)
                aspect = raw.height / max(1, raw.width)
                sub_img = raw.resize((target_w, int(target_w * aspect)), Image.Resampling.LANCZOS)
            except Exception:
                sub_img = None

        num_coins = 12
        coins = []
        for _ in range(num_coins):
            coins.append({
                "x": random.randint(100, cw - 100),
                "start_y": random.randint(-400, 200),
                "speed": random.uniform(250, 480),
                "rad": random.randint(24, 38)
            })

        for f_idx in range(total_frames):
            t = f_idx / float(fps)
            progress = f_idx / float(total_frames)

            canvas = Image.new("RGBA", (cw, ch), (24, 24, 27, 255))
            draw = ImageDraw.Draw(canvas)

            for ly in range(40, ch, 15):
                draw.line([(40, ly), (cw - 40, ly)], fill=(200, 200, 190, 20), width=2)

            sky_w, sky_h = int(cw * 0.90), int(ch * 0.52)
            sky = Image.new("RGBA", (sky_w, sky_h), (25, 120, 175, 255))
            sky_draw = ImageDraw.Draw(sky)
            for y in range(sky_h):
                r = int(18 + (38 - 18) * (y / sky_h))
                g = int(85 + (135 - 85) * (y / sky_h))
                b = int(140 + (195 - 140) * (y / sky_h))
                sky_draw.line([(0, y), (sky_w, y)], fill=(r, g, b, 255))

            cloud_drift = int(t * 30)
            for cx, cy, rad in [(180 + cloud_drift, 140, 75), (550 + cloud_drift, 110, 80), (880 + cloud_drift, 160, 65)]:
                wrap_cx = cx % (sky_w + 100) - 50
                sky_draw.ellipse([wrap_cx - rad, cy - rad//2, wrap_cx + rad, cy + rad//2], fill=(245, 248, 252, 110))

            mask = Image.new("L", (sky_w, sky_h), 255)
            m_draw = ImageDraw.Draw(mask)
            top_p = [(0, 0)]
            for x in range(0, sky_w, 14):
                top_p.append((x, int(22 + 6 * math.sin(x/30.0))))
            top_p.extend([(sky_w, 0), (0, 0)])
            m_draw.polygon(top_p, fill=0)

            bot_p = [(0, sky_h)]
            for x in range(0, sky_w, 14):
                bot_p.append((x, sky_h - int(24 + 6 * math.cos(x/30.0))))
            bot_p.extend([(sky_w, sky_h), (0, sky_h)])
            m_draw.polygon(bot_p, fill=0)
            sky.putalpha(mask)

            sky_x = (cw - sky_w) // 2
            sky_y = int(ch * 0.14)
            canvas.paste(sky, (sky_x, sky_y), sky)

            pulse = 1.0 + 0.04 * math.sin(t * 3.0)
            halo_size = int(cw * 0.60 * pulse)
            halo = Image.new("RGBA", (halo_size, halo_size), (0, 0, 0, 0))
            h_draw = ImageDraw.Draw(halo)
            h_draw.ellipse([0, 0, halo_size, halo_size], fill=(250, 204, 21, 235))
            canvas.paste(halo, (cw//2 - halo_size//2, sky_y + 35), halo)

            zoom_factor = 1.0 + 0.06 * progress
            if sub_img:
                zw = int(sub_img.width * zoom_factor)
                zh = int(sub_img.height * zoom_factor)
                zoomed_sub = sub_img.resize((zw, zh), Image.Resampling.LANCZOS)
                sub_x = (cw - zw) // 2
                sub_y = sky_y + int(sky_h * 0.20)
                canvas.paste(zoomed_sub, (sub_x, sub_y), zoomed_sub)

            if motion_type == "moedas_caindo" or style == "vox":
                draw_coin = ImageDraw.Draw(canvas)
                for c in coins:
                    current_y = int(c["start_y"] + c["speed"] * t) % (ch + 100) - 50
                    c_rad = c["rad"]
                    cx = c["x"]
                    draw_coin.ellipse([cx - c_rad, current_y - c_rad, cx + c_rad, current_y + c_rad],
                                      fill=(234, 179, 8, 245), outline=(254, 240, 138, 255), width=3)
                    draw_coin.ellipse([cx - c_rad//2, current_y - c_rad//2, cx + c_rad//2, current_y + c_rad//2],
                                      outline=(202, 138, 4, 200), width=2)

            title_text = headline.upper()
            title_y = int(ch * 0.05)
            bbox = draw.textbbox((0, 0), title_text, font=font_title)
            tw = bbox[2] - bbox[0]
            tx = (cw - tw) // 2
            draw.text((tx + 3, title_y + 3), title_text, font=font_title, fill=(10, 10, 12, 220))
            draw.text((tx, title_y), title_text, font=font_title, fill=(245, 242, 232, 255))

            box_w, box_h = int(cw * 0.84), 84
            box_x = (cw - box_w) // 2
            box_y = int(ch * 0.72)
            draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=24,
                                   fill=(255, 255, 255, 245), outline=(220, 220, 220, 255), width=2)
            btn_size = 56
            btn_x = box_x + box_w - btn_size - 14
            btn_y = box_y + (box_h - btn_size) // 2
            draw.rounded_rectangle([btn_x, btn_y, btn_x + btn_size, btn_y + btn_size], radius=16, fill=(225, 29, 72, 255))
            arrow_cx = btn_x + btn_size // 2
            arrow_cy = btn_y + btn_size // 2
            draw.line([(arrow_cx, arrow_cy + 10), (arrow_cx, arrow_cy - 10)], fill=(255, 255, 255, 255), width=4)
            draw.line([(arrow_cx - 8, arrow_cy - 2), (arrow_cx, arrow_cy - 10)], fill=(255, 255, 255, 255), width=4)
            draw.line([(arrow_cx + 8, arrow_cy - 2), (arrow_cx, arrow_cy - 10)], fill=(255, 255, 255, 255), width=4)
            clean_prompt = (prompt[:36] + "...") if len(prompt) > 36 else prompt
            draw.text((box_x + 28, box_y + 26), f"+ {clean_prompt}", font=font_sub, fill=(60, 60, 65, 255))

            if narration:
                cap_y = int(ch * 0.84)
                cap_w = int(cw * 0.84)
                cap_x = (cw - cap_w) // 2
                draw.rounded_rectangle([cap_x, cap_y, cap_x + cap_w, cap_y + 76], radius=16, fill=(18, 18, 22, 225))
                cap_text = narration[:42].upper()
                cbbox = draw.textbbox((0, 0), cap_text, font=font_narration)
                cx = (cw - (cbbox[2] - cbbox[0])) // 2
                draw.text((cx, cap_y + 22), cap_text, font=font_narration, fill=(255, 255, 255, 255))

            frame_path = os.path.join(work_dir, f"frame_{f_idx+1:04d}.jpg")
            canvas.convert("RGB").save(frame_path, "JPEG", quality=90)

    def _add_scene_sfx(self, input_video: str, output_video: str, duration: float = 7.0):
        """Gera áudio estéreo com silêncio da duração exata do clipe."""
        temp_audio = input_video.replace(".mp4", "_audio.wav")
        cmd_audio = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            temp_audio
        ]
        try:
            subprocess.run(cmd_audio, capture_output=True, timeout=20)
            cmd_merge = [
                "ffmpeg", "-y",
                "-i", input_video,
                "-i", temp_audio,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                output_video
            ]
            subprocess.run(cmd_merge, capture_output=True, timeout=30)
            if not os.path.exists(output_video) or os.path.getsize(output_video) < 1000:
                shutil.copyfile(input_video, output_video)
        except Exception:
            shutil.copyfile(input_video, output_video)
        finally:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)

    # ----------------------------------------------------------------------------------------
    # 4. COMPOSITOR MASTER: JUNTA TODAS AS CENAS EM VÍDEO COMPLETO (1 MINUTO+)
    # ----------------------------------------------------------------------------------------
    def assemble_master_video(
        self,
        scene_video_paths: List[str],
        output_mp4: str = None,
        style: str = "vox",
        bg_music_path: Optional[str] = None
    ) -> str:
        if not scene_video_paths:
            raise ValueError("Nenhum clipe de cena fornecido para junção.")

        if not output_mp4:
            os.makedirs("output", exist_ok=True)
            output_mp4 = os.path.join("output", f"vox_master_{uuid.uuid4().hex[:8]}.mp4")

        concat_txt = os.path.join("output", f"concat_{uuid.uuid4().hex[:8]}.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for p in scene_video_paths:
                clean_p = os.path.abspath(p).replace("\\", "/")
                f.write(f"file '{clean_p}'\n")

        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_txt,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "19",
                "-c:a", "aac",
                output_mp4
            ]
            subprocess.run(cmd, capture_output=True, timeout=180)
        finally:
            if os.path.exists(concat_txt):
                os.remove(concat_txt)

        return output_mp4
