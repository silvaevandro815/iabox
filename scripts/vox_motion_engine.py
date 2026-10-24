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
                "canvas_preset": "Estilo Vox (Colagem Editorial Vintage)",
                "desc": "Papel rasgado, texturas de jornal antigo, retícula halftone, realces amarelos vibrantes, colagem fotográfica recortada e tipografia editorial.",
                "prompt_prefix": "Vox documentary editorial collage art, vintage paper texture background, archival newspaper and cutout photo montage, subtle halftone dots, vibrant yellow highlighter accents, mixed-media photo montage, stop-motion archival explainer aesthetic, graphic design masterpiece",
                "video_motion": "editorial collage stop-motion parallax, archival cutouts animating, subtle paper texture drift, kinetic graphic elements, professional documentary motion",
                "bg_color": (24, 24, 27),
                "accent_color": (250, 204, 21), # Amarelo Vox #FACC15
                "accent_hex": "#FACC15",
                "font_head": "times.ttf"
            },
            "motion_graphics": {
                "id": "motion_graphics",
                "name": "Motion Graphics 2D (Explainer Tech Minimalista)",
                "canvas_preset": "Motion Graphics 2D (Explainer Tech Minimalista)",
                "desc": "Visual corporativo limpo, formas geométricas vetorizadas, dados infográficos flutuantes e paleta ciano/ardósia moderna.",
                "prompt_prefix": "clean 2D flat vector illustration, motion graphics explainer design, minimalist geometric vector art, slate grey and cyan high-contrast color palette, modern tech infographic elements, sharp clean edges, vector art masterpiece",
                "video_motion": "smooth 2D vector animation, kinetic infographic motion, minimalist geometric shapes shifting, modern motion design",
                "bg_color": (15, 23, 42),
                "accent_color": (6, 182, 212), # Ciano 500 #06B6D4
                "accent_hex": "#06B6D4",
                "font_head": "arial.ttf"
            },
            "cinema_3d": {
                "id": "cinema_3d",
                "name": "3D Render Cinematográfico (Unreal / Octane)",
                "canvas_preset": "3D Render Cinematográfico (Unreal / Octane)",
                "desc": "Iluminação volumétrica dramática, sombras suaves de estúdio, texturas foto-realistas e profundidade de campo rasa.",
                "prompt_prefix": "Unreal Engine 5 Octane 3D render, photorealistic 3D CGI masterwork, volumetric ray-traced lighting, subsurface scattering, ambient occlusion, 8k CGI cinema quality",
                "video_motion": "fluid 3D camera pan, 3D CGI volumetric motion, cinematic smooth camera movement",
                "bg_color": (10, 10, 15),
                "accent_color": (245, 158, 11), # Âmbar
                "accent_hex": "#F59E0B",
                "font_head": "arial.ttf"
            },
            "cyberpunk": {
                "id": "cyberpunk",
                "name": "Dark Cyberpunk Neon",
                "canvas_preset": "Dark Cyberpunk Neon",
                "desc": "Contraste extremo, reflexos de asfalto molhado, neon laser ciano e magenta, interface HUD holográfica e fumaça volumétrica.",
                "prompt_prefix": "dark cyberpunk sci-fi aesthetic, glowing vibrant cyan and magenta neon lights, futuristic cityscape, rain-slicked wet reflections, high contrast volumetric neon glow, dark synthwave vibe",
                "video_motion": "pulsing neon lights, glowing wet street reflections, volumetric smoke drifting, cyberpunk camera tracking",
                "bg_color": (10, 12, 20),
                "accent_color": (244, 63, 94), # Rose/Neon Magenta #F43F5E
                "accent_hex": "#F43F5E",
                "font_head": "arial.ttf"
            },
            "comic_pop": {
                "id": "comic_pop",
                "name": "HQ & Pop Art (Graphic Novel Vintage)",
                "canvas_preset": "HQ & Pop Art (Graphic Novel Vintage)",
                "desc": "Pontos Ben-Day de impressão, contornos pretos expressivos, balões de diálogo, onomatopeias e cores chapadas vibrantes.",
                "prompt_prefix": "vintage comic book pop art illustration, bold black ink outlines, Roy Lichtenstein style Ben-Day dots, vivid retro comic colors, dynamic graphic novel art, halftone print texture",
                "video_motion": "dynamic graphic novel animation, comic book pop art action lines, stylized illustrated movement",
                "bg_color": (255, 251, 235),
                "accent_color": (239, 68, 68), # Vermelho Comic #EF4444
                "accent_hex": "#EF4444",
                "font_head": "impact.ttf"
            },
            "anime": {
                "id": "anime",
                "name": "Ilustração Anime & Studio Ghibli",
                "canvas_preset": "Ilustração Anime & Studio Ghibli",
                "desc": "Céus em aquarela com nuvens volumosas, luz natural suave, paleta nostálgica pintada à mão e atmosfera pacífica.",
                "prompt_prefix": "Studio Ghibli anime masterwork illustration, Makoto Shinkai aesthetic, hand-painted watercolor background, beautiful lush painted clouds, soft natural anime lighting, expressive anime cel-shading",
                "video_motion": "cinematic anime animation, gentle wind blowing through hair, watercolor painted clouds drifting, soft natural character motion, Studio Ghibli cel motion",
                "bg_color": (20, 30, 45),
                "accent_color": (56, 189, 248), # Sky Blue #38BDF8
                "accent_hex": "#38BDF8",
                "font_head": "times.ttf"
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

        system_prompt = f"""Você é o Diretor Criativo Principal e Roteirista Chefe de documentários e vídeos virais estilo {style_info['name']} (Vox, Curio, Johnny Harris).
Sua missão é pegar o tema ou roteiro enviado pelo usuário e criar EXATAMENTE {num_scenes} cenas sequenciais de {sec_per_scene}s cada, com continuidade narrativa cinematográfica e rigorosa obediência ao estilo visual selecionado.

REGRA SUPREMA DE ESTILO VISUAL: {style_info['name'].upper()}
Cada cena DEVE incorporar com precisão milimétrica a estética deste estilo:
- Descrição estética obrigatória: {style_info['desc']}
- Todos os prompts do campo "prompt" DEVEM ser em INGLÊS e OBRIGATORIAMENTE conter a assinatura visual do estilo:
  "{style_info['prompt_prefix']}"
- NUNCA gere fotos de cinema genérico ou de câmera comum se o estilo for Colagem Editorial Vox, Anime, Comic Pop Art ou Motion Graphics! Obedeça 100% ao estilo {style_info['name']}.

DIRETRIZES FUNDAMENTAIS DE CONTINUIDADE E PERSONAGEM:
1. MANTENHA A COERÊNCIA DO PERSONAGEM/TEMA:
   - Se o usuário mencionar um personagem (ex: "menino negro", "cientista", "empreendedor"), mantenha ESSE MESMO PERSONAGEM em todas as cenas da narrativa com a mesma faixa etária, roupas e características físicas marcantes.
   - NUNCA invente personagens aleatórios sem relação com o pedido.
2. CADA CENA DEVE SER UM PONTO DINÂMICO DA HISTÓRIA (Jornada do Herói / Arco Dramático):
   - Cena 1: A Origem / O Chamado (apresentação do herói e do contraste inicial).
   - Cena 2: O Conflito / A Realidade do Mundo (o problema que ele enfrenta).
   - Cena 3: A Ação / A Ideia Inovadora (como ele começa a transformar ou tentar convencer).
   - Cena 4: A Resistência e Superação (o momento de desafio onde ele não desiste).
   - Cena 5: A Virada e Impacto Coletivo (a comunidade, as pessoas se unindo a ele).
   - Cena 6: A Vitória e Visão do Futuro (o desfecho triunfante, inspirador e sustentável).
3. ESTRUTURA DOS CAMPOS DE CADA CENA:
   - "headline": 1 ou 2 palavras em CAIXA ALTA de alto impacto (ex: "O CHAMADO", "A JORNADA", "A CRISE", "A VOZ", "A VIRADA", "O FUTURO").
   - "prompt": Descrição visual ultra-detalhada em INGLÊS (para o gerador de imagem 8K) contendo OBRIGATORIAMENTE "{style_info['prompt_prefix']}" seguido do sujeito e da ação.
   - "motion": Escolha o movimento que melhor casa com a cena: 'zoom_parallax', 'revelacao_papel', 'nuvens_deriva', 'engrenagens' ou 'moedas_caindo'.
   - "narration": Frase concisa, emocional e inspiradora em português (1 a 2 frases para a voz/legenda da cena).
   - "duration": {sec_per_scene}.

Responda ESTRITAMENTE um JSON ARRAY contendo exatamente {num_scenes} objetos JSON. Não inclua nenhum texto, explicação ou markdown fora do JSON."""

        user_content = f"TEMA OU ROTEIRO DO VÍDEO:\n{script_text}\n\nCrie a sequência completa de {num_scenes} cenas com continuidade visual perfeita no estilo {style_info['name']}."

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
                        p_raw = s.get("prompt", "Editorial scene")
                        # Garante que a assinatura visual do estilo esteja presente no prompt
                        if not any(k in p_raw.lower() for k in ["vox", "collage", "anime", "ghibli", "comic", "pop art", "vector", "cyberpunk", "octane", "unreal"]):
                            p_raw = f"{style_info['prompt_prefix']}, {p_raw}"

                        formatted_scenes.append({
                            "scene_number": idx + 1,
                            "headline": s.get("headline", f"CENA {idx+1}")[:25].upper(),
                            "prompt": p_raw[:850],
                            "motion": s.get("motion", "zoom_parallax"),
                            "narration": s.get("narration", "")[:300],
                            "duration": sec_per_scene,
                            "reference_images": []
                        })
                    return formatted_scenes
            except Exception as e:
                print(f"[VoxMotionEngine] Falha ao decodificar JSON da IA: {e}")

        return self._generate_fallback_scenes(script_text, num_scenes, sec_per_scene, style)

    def _generate_fallback_scenes(self, script_text: str, num_scenes: int, sec_per_scene: float, style: str) -> List[Dict]:
        style_info = self.styles.get(style, self.styles["vox"])
        prefix = style_info.get("prompt_prefix", "Vox documentary editorial collage art, vintage paper texture background")

        beats = [
            ("O CHAMADO", f"{prefix}, portrait of a determined 10-year-old Black boy with curly hair in a green hoodie looking over a city, dramatic contrast, high resolution.", "zoom_parallax", "Em um mundo tomado pela pressa e pelo desperdício, uma jovem voz decide não se calar."),
            ("A JORNADA", f"{prefix}, wide view, the young Black boy walking through a bustling urban avenue holding a handmade recycling bag, striking composition.", "revelacao_papel", "Ele caminha pelas ruas mostrando que cada pequena atitude tem o poder de transformar o planeta."),
            ("A VOZ", f"{prefix}, the young Black boy speaking passionately in a public square, demonstrating creative recycled inventions, inspiring expression.", "zoom_parallax", "Conscientizar não é impor regras, é despertar nas pessoas o amor pelo futuro comum."),
            ("O DESAFIO", f"{prefix}, community gathering listening to the young Black boy as he sorts recyclable bottles, rich graphic textures.", "engrenagens", "Quando o exemplo é sincero, a indiferença dá lugar à ação coletiva."),
            ("A VIRADA", f"{prefix}, thousands of people cleaning up city streets and parks, planting seedlings, vibrant global eco movement.", "nuvens_deriva", "O movimento ganha as ruas e o mundo: a reciclagem se torna uma corrente imparável de união."),
            ("O FUTURO", f"{prefix}, hopeful smiling portrait of the young Black boy looking over a lush green sustainable city with solar roofs, uplifting composition.", "zoom_parallax", "A mudança que o mundo precisa começou no coração de uma criança que acreditou no amanhã.")
        ]
        
        scenes = []
        for i in range(num_scenes):
            beat = beats[i % len(beats)]
            scenes.append({
                "scene_number": i + 1,
                "headline": beat[0],
                "prompt": beat[1],
                "motion": beat[2],
                "narration": beat[3],
                "duration": sec_per_scene,
                "reference_images": []
            })
        return scenes

    def _call_ai(self, system_prompt: str, user_content: str) -> Optional[str]:
        # 1. Tenta modelos Gemini ativos (3.5-flash-lite ou 3.8-flash)
        if self.gemini_key:
            for gemini_model in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-flash-latest"]:
                try:
                    import requests
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={self.gemini_key}"
                    payload = {
                        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_content}"}]}],
                        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2500}
                    }
                    r = requests.post(url, json=payload, timeout=18)
                    if r.status_code == 200:
                        d = r.json()
                        candidates = d.get("candidates", [])
                        if candidates:
                            return candidates[0]["content"]["parts"][0]["text"]
                except Exception as e:
                    print(f"[VoxMotionEngine] Gemini API error ({gemini_model}): {e}")

        # 2. Fallback para OpenRouter com modelos de alta disponibilidade
        if self.openrouter_key:
            for or_model in ["meta-llama/llama-3.3-70b-instruct", "google/gemini-2.5-flash-preview", "deepseek/deepseek-chat"]:
                try:
                    import requests
                    headers = {
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": or_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        "temperature": 0.4
                    }
                    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=18)
                    if r.status_code == 200:
                        d = r.json()
                        choices = d.get("choices", [])
                        if choices:
                            return choices[0]["message"]["content"]
                except Exception as e:
                    print(f"[VoxMotionEngine] OpenRouter API error ({or_model}): {e}")
        return None

    # ----------------------------------------------------------------------------------------
    # 2. TRATAMENTO VISUAL: PRESERVA 100% AS CORES E QUALIDADE DAS FOTOS
    # ----------------------------------------------------------------------------------------
    def stylize_reference_image(self, input_path: str, style: str = "vox", output_path: str = None) -> str:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Imagem não encontrada: {input_path}")

        if not output_path:
            os.makedirs("output", exist_ok=True)
            output_path = os.path.join("output", f"styled_{uuid.uuid4().hex[:8]}.png")

        # Preserva 100% as cores originais da imagem (sem degradar para preto e branco!)
        orig = Image.open(input_path).convert("RGBA")
        enh = ImageEnhance.Color(orig).enhance(1.05)
        contrasted = ImageEnhance.Contrast(enh).enhance(1.06)
        contrasted.save(output_path, "PNG")
        return output_path

    # ----------------------------------------------------------------------------------------
    # 3. RENDERIZADOR DE CENA: GERA VÍDEO DE VERDADE COM MOVIMENTO DE IA (SEM SLIDES, SEM SOL FAKE)
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

        headline = scene_data.get("headline", "CENA").strip().upper()
        prompt = scene_data.get("prompt", "Cena editorial cinematografica").strip()
        narration = scene_data.get("narration", "").strip()
        scene_num = scene_data.get("scene_number", 1)

        work_dir = os.path.join("output", f"vox_work_{uuid.uuid4().hex[:8]}")
        os.makedirs(work_dir, exist_ok=True)

        try:
            # 1. Obter o frame chave da cena em cores reais 8K ultra-realista
            keyframe_path = None
            for r_p in (ref_images or []):
                if r_p and os.path.exists(r_p):
                    keyframe_path = r_p
                    break

            # Se nenhuma foto foi enviada, a IA sintetiza o frame chave 8K rigorosamente no estilo selecionado
            style_info = self.styles.get(style, self.styles["vox"])
            if not keyframe_path:
                try:
                    from scripts.magnific_canvas_engine import MagnificCanvasEngine
                    canvas_eng = MagnificCanvasEngine()
                    synth_path = os.path.join(work_dir, f"keyframe_{scene_num}.jpg")
                    is_paid = runpod_mode or bool(self.runpod_key)
                    m_style = style_info.get("canvas_preset", "Estilo Vox (Colagem Editorial Vintage)")

                    # Assegura a assinatura visual artística do estilo no prompt
                    full_img_prompt = prompt
                    prefix = style_info.get("prompt_prefix", "")
                    if prefix and not any(k in prompt.lower() for k in ["vox", "collage", "anime", "ghibli", "comic", "pop art", "vector", "cyberpunk", "octane", "unreal"]):
                        full_img_prompt = f"{prefix}, {prompt}"

                    canvas_eng.generate_connected_node(
                        prompt=full_img_prompt,
                        reference_images=[],
                        model_style=m_style,
                        aspect_ratio="9:16",
                        is_paid=is_paid,
                        output_path=synth_path
                    )
                    if os.path.exists(synth_path) and os.path.getsize(synth_path) > 3000:
                        keyframe_path = synth_path
                except Exception as e_synth:
                    print(f"[VoxMotionEngine] Erro ao sintetizar frame da cena: {e_synth}")

            # 2. Gerar o vídeo com movimento cinematográfico real de IA respeitando o estilo
            raw_ai_video = os.path.join(work_dir, "raw_ai_video.mp4")
            try:
                from scripts.ai_video_engine import generate_video_clip
                motion_tag = style_info.get("video_motion", "editorial documentary motion")
                video_prompt = f"{prompt}, {motion_tag}"

                gen_res = generate_video_clip(
                    prompt=video_prompt,
                    out_path=raw_ai_video,
                    first_frame=keyframe_path,
                    duration=int(duration),
                    aspect_ratio="9:16",
                    is_paid=runpod_mode or bool(self.runpod_key)
                )
            except Exception as e_gen:
                print(f"[VoxMotionEngine] Falha ao chamar ai_video_engine: {e_gen}")
                gen_res = None

            if not gen_res or not os.path.exists(raw_ai_video) or os.path.getsize(raw_ai_video) < 5000:
                if keyframe_path and os.path.exists(keyframe_path):
                    from scripts.ai_video_engine import _local_cinematic_motion
                    _local_cinematic_motion(keyframe_path, raw_ai_video, duration=int(duration), aspect_ratio="9:16")

            # 3. Aplicar Overlay Editorial Profissional respeitando as cores e tipografia do estilo
            self._apply_broadcast_overlay(
                input_video=raw_ai_video,
                output_video=output_mp4,
                headline=headline,
                narration=narration,
                duration=duration,
                style=style
            )

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        return output_mp4

    def _apply_broadcast_overlay(self, input_video: str, output_video: str, headline: str, narration: str, duration: float, style: str = "vox"):
        if not os.path.exists(input_video) or os.path.getsize(input_video) < 1000:
            return

        cw, ch = 720, 1280
        overlay = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        style_info = self.styles.get(style, self.styles["vox"])
        accent_color = style_info.get("accent_color", (250, 204, 21))
        font_file = style_info.get("font_head", "times.ttf")

        try:
            font_head = ImageFont.truetype(font_file, 58)
        except Exception:
            try:
                font_head = ImageFont.truetype("arial.ttf", 58)
            except Exception:
                font_head = ImageFont.load_default()

        try:
            font_sub = ImageFont.truetype("arial.ttf", 26)
        except Exception:
            font_sub = ImageFont.load_default()

        # Vinheta cinematográfica suave no topo e na base (garante 100% de legibilidade dos textos)
        for y in range(160):
            alpha = int(140 * (1.0 - y / 160.0))
            draw.line([(0, y), (cw, y)], fill=(0, 0, 0, alpha))

        for y in range(ch - 220, ch):
            factor = (y - (ch - 220)) / 220.0
            alpha = int(180 * factor)
            draw.line([(0, y), (cw, y)], fill=(0, 0, 0, alpha))

        # Headline no topo
        if headline:
            bbox = draw.textbbox((0, 0), headline, font=font_head)
            tw = bbox[2] - bbox[0]
            tx = (cw - tw) // 2
            draw.text((tx + 2, 42), headline, font=font_head, fill=(0, 0, 0, 220))
            draw.text((tx, 40), headline, font=font_head, fill=(255, 255, 255, 255))

        # Legenda com efeito glassmorphism na base
        if narration:
            cap_w = int(cw * 0.90)
            cap_h = 84
            cap_x = (cw - cap_w) // 2
            cap_y = ch - cap_h - 40

            outline_rgba = (accent_color[0], accent_color[1], accent_color[2], 160)
            accent_rgba = (accent_color[0], accent_color[1], accent_color[2], 255)

            draw.rounded_rectangle([cap_x, cap_y, cap_x + cap_w, cap_y + cap_h], radius=16, fill=(15, 15, 20, 210), outline=outline_rgba, width=2)
            draw.rounded_rectangle([cap_x, cap_y, cap_x + 6, cap_y + cap_h], radius=3, fill=accent_rgba)

            words = narration.split()
            l1, l2 = "", ""
            for w in words:
                if len(l1 + " " + w) < 32 and not l2:
                    l1 = (l1 + " " + w).strip()
                else:
                    l2 = (l2 + " " + w).strip()

            draw.text((cap_x + 20, cap_y + 14), l1, font=font_sub, fill=(255, 255, 255, 255))
            if l2:
                draw.text((cap_x + 20, cap_y + 46), l2, font=font_sub, fill=accent_rgba)

        temp_overlay = input_video.replace(".mp4", "_overlay.png")
        overlay.save(temp_overlay, "PNG")
        overlay.save(temp_overlay, "PNG")

        # Anexa overlay e áudio via FFmpeg
        temp_audio = input_video.replace(".mp4", "_audio.wav")
        cmd_audio = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            temp_audio
        ]
        subprocess.run(cmd_audio, capture_output=True, timeout=15)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-i", temp_overlay,
            "-i", temp_audio,
            "-filter_complex", "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280[scaled];[scaled][1:v]overlay=0:0:format=auto[outv]",
            "-map", "[outv]",
            "-map", "2:a",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "19",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            output_video
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
            if not os.path.exists(output_video) or os.path.getsize(output_video) < 2000:
                shutil.copyfile(input_video, output_video)
        except Exception:
            shutil.copyfile(input_video, output_video)
        finally:
            if os.path.exists(temp_overlay):
                os.remove(temp_overlay)
            if os.path.exists(temp_audio):
                os.remove(temp_audio)

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
