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
    # 1. INTELIGÊNCIA ARTIFICIAL: DESMEMBRAR ROTEIRO EM CENAS (BEATS CINEMATOGRÁFICOS)
    # ----------------------------------------------------------------------------------------
    def split_script_with_ai(
        self,
        script_text: str,
        num_scenes: int = 6,
        style: str = "vox",
        sec_per_scene: float = 10.0
    ) -> List[Dict]:
        """
        Usa LLM avançado para analisar o roteiro ou tema e transformá-lo em
        um plano de corte multi-cena com rigorosa continuidade narrativa,
        design consistente de personagens/sujeitos (VISUAL_DNA) e planos de câmera variados.
        """
        style_info = self.styles.get(style, self.styles["vox"])
        num_scenes = max(2, min(int(num_scenes), 16))
        sec_per_scene = max(5.0, min(float(sec_per_scene), 15.0))

        system_prompt = f"""Você é o Diretor Criativo Principal e Roteirista Chefe de documentários e vídeos virais estilo {style_info['name']} (Vox, Johnny Harris, Kurzgesagt, Netflix Explained).
Sua missão é pegar o tema ou roteiro enviado pelo usuário e criar EXATAMENTE {num_scenes} cenas sequenciais de {sec_per_scene}s cada, com continuidade narrativa impecável (Começo, Meio e Fim) e obediência absoluta ao estilo visual selecionado.

REGRA SUPREMA DE ESTILO: {style_info['name'].upper()}
- Estética obrigatória: {style_info['desc']}
- Assinatura visual obrigatória em TODOS os prompts:
  "{style_info['prompt_prefix']}"

ETAPA 1 — IDENTIFICAR E FIXAR O DNA VISUAL DO SUJEITO (VISUAL_DNA):
1. Identifique o sujeito central da história (ex: um planeta artesanal, um personagem específico, um objeto em transformação).
2. Formule uma descrição visual densa e invariável (materiais, textura, paleta de cores, estilo de colagem ou traço do estilo ativo).
3. Esse bloco "VISUAL_DNA: [descrição]" DEVE SER REPETIDO LITERALMENTE em TODAS as {num_scenes} cenas para garantir consistência visual absoluta nos modelos generativos!
4. FIDELIDADE AO TEMA: Se a história trata de um planeta, espaço, objeto inanimado ou animal, É TERMINANTEMENTE PROIBIDO inventar ou inserir seres humanos, mulheres ou pessoas aleatórias! Mantenha o foco 100% no elemento central pedido.

ETAPA 2 — PROGRESSÃO CINEMATOGRÁFICA RIGOROSA (6 ATOS COM PLANOS E ÂNGULOS TÉCNICOS DISTINTOS):
- Cena 1: Extreme Wide Establishing Shot (Plano Geral Aberto 24mm) + slow pan/drift. Estabelece o mundo, escala e atmosfera inicial.
- Cena 2: Medium Portrait / Focus Shot (Plano Médio 50mm) + slow dolly-in. Apresenta o sujeito/personagem central em destaque.
- Cena 3: Macro Detail Shot (Plano Detalhe / Close-up 85mm) + dynamic tilt/tracking. Mostra o mecanismo interno, textura tátil ou ponto de tensão.
- Cena 4: Dynamic Low-Angle Action Shot (Contra-Plongée 35mm) + kinetic push/orbit. Ação dramática, metamorfose ou clímax do conflito.
- Cena 5: High-Angle Wide Impact Shot (Plano Plongée Aberto 28mm) + sweeping crane. O impacto amplo, irradiação no cenário ou reverberação coletiva.
- Cena 6: Hero Medium Resolution Shot (Plano Master de Fechamento) + parallax pull-out. Conclusão triunfante, inspiradora e memorável.

ESTRUTURA DOS CAMPOS DE CADA CENA NO JSON:
- "scene_number": número inteiro da cena (1 a {num_scenes}).
- "headline": 1 ou 2 palavras em CAIXA ALTA de alto impacto (ex: "A ORIGEM", "O CHAMADO", "O NÚCLEO", "A VIRADA", "A EXPANSÃO", "O FUTURO").
- "prompt": Descrição visual técnica em INGLÊS. Comece com "{style_info['prompt_prefix']}", seguido do Plano e Lente (ex: "Extreme Wide Establishing Shot, 24mm lens"), depois "VISUAL_DNA: [descrição fixa do sujeito]", depois a ação da cena e iluminação, finalizando com o movimento de câmera cinematográfico.
- "motion": 'zoom_parallax', 'revelacao_papel', 'nuvens_deriva', 'engrenagens' ou 'moedas_caindo'.
- "narration": Frase concisa, cinematográfica e conectada em português (construindo uma narrativa fluida com começo, meio e fim).
- "duration": {sec_per_scene}.

Responda ESTRITAMENTE um JSON ARRAY contendo exatamente {num_scenes} objetos JSON. Não inclua texto explicativo fora do array."""

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
                if isinstance(scenes, dict):
                    scenes = scenes.get("scenes", list(scenes.values())[0])

                if isinstance(scenes, list) and len(scenes) > 0:
                    formatted_scenes = []
                    for idx, s in enumerate(scenes[:num_scenes]):
                        p_raw = s.get("prompt", "Editorial scene")
                        # Garante que a assinatura visual do estilo esteja presente no prompt
                        if not any(k in p_raw.lower() for k in ["vox", "collage", "anime", "ghibli", "comic", "pop art", "vector", "cyberpunk", "octane", "unreal"]):
                            p_raw = f"{style_info['prompt_prefix']}, {p_raw}"

                        formatted_scenes.append({
                            "scene_number": idx + 1,
                            "headline": s.get("headline", f"CENA {idx+1}")[:30].upper(),
                            "prompt": p_raw[:1200],
                            "motion": s.get("motion", "zoom_parallax"),
                            "narration": s.get("narration", "")[:350],
                            "duration": sec_per_scene,
                            "reference_images": []
                        })
                    return formatted_scenes
            except Exception as e:
                print(f"[VoxMotionEngine] Falha ao decodificar JSON da IA: {e}")

        return self._generate_fallback_scenes(script_text, num_scenes, sec_per_scene, style)

    def _generate_fallback_scenes(self, script_text: str, num_scenes: int, sec_per_scene: float, style: str) -> List[Dict]:
        """
        Gera 6 cenas cinematográficas adaptativas quando o LLM estiver indisponível,
        extraindo dinamicamente o tema do texto do usuário (Planeta, Metamorfose de Objeto,
        Personagem ou Tecnologia) ao invés de fixar uma única história.
        """
        style_info = self.styles.get(style, self.styles["vox"])
        prefix = style_info.get("prompt_prefix", "Vox documentary editorial collage art, vintage paper texture background")
        text_lower = (script_text or "").lower()

        # Tema 1: Planeta / Espaço / Cosmos
        if any(w in text_lower for w in ["planeta", "planet", "espaço", "espaco", "space", "galaxia", "universo", "estrela", "cosmos"]):
            dna = "A stylized vintage papercraft planet crafted from aged cartography maps, torn parchment continents, deep blueprint teal oceans, and golden foil rings"
            beats = [
                ("A ORIGEM", f"{prefix}, Extreme Wide Establishing Shot, 24mm lens, VISUAL_DNA: {dna}, drifting serenely in a cosmic void of aged celestial atlas pages, slow panoramic drift.", "nuvens_deriva", "Nos confins inexplorados do cosmos, um mundo esculpido pelo tempo aguarda em silêncio."),
                ("O NÚCLEO", f"{prefix}, Medium Focus Shot, 50mm lens, VISUAL_DNA: {dna}, rotating gently revealing paper tectonic folds and golden contour lines, dramatic rim light, slow dolly-in.", "zoom_parallax", "Sua atmosfera guarda segredos de uma civilização antiga gravados em mapas e papiros."),
                ("O MECANISMO", f"{prefix}, Macro Detail Shot, 85mm lens, VISUAL_DNA: {dna}, extreme close-up of intricate paper clockwork gears and luminous canary-yellow energy veins, tilt focus tracking.", "engrenagens", "No coração deste planeta, engrenagens douradas mantêm o ritmo perfeito da existência."),
                ("A TRANSFORMAÇÃO", f"{prefix}, Dynamic Low-Angle Action Shot, 35mm lens, VISUAL_DNA: {dna}, golden energy bursts through paper tectonic plates, shifting mountain ranges, kinetic orbit push.", "revelacao_papel", "Um impulso de luz rompe a crosta, despertando forças adormecidas há milênios."),
                ("A IRRADIAÇÃO", f"{prefix}, High-Angle Wide Impact Shot, 28mm lens, VISUAL_DNA: {dna}, radiant yellow light pulses across the entire planetary surface illuminating orbiting star charts, sweeping crane.", "moedas_caindo", "O brilho se expande pelo espaço, transformando a escuridão em um espetáculo de harmonia."),
                ("O FUTURO", f"{prefix}, Hero Medium Resolution Shot, 50mm lens, VISUAL_DNA: {dna}, the majestic planet flourishing with luminescent golden paper auroras, cinematic parallax pull-out.", "zoom_parallax", "Assim nasce uma nova era cósmica: onde história, arte e vida eterna se encontram.")
            ]
        # Tema 2: Metamorfose / Objeto (Ex: Lápis vira Flor)
        elif any(w in text_lower for w in ["lápis", "lapis", "flor", "flower", "metamorfose", "semente", "planta", "árvore", "arvore"]):
            dna = "A handcrafted vintage pencil crafted from dark cedar wood and golden brass ferrule, transforming into an intricate origami blooming flower"
            beats = [
                ("O COMEÇO", f"{prefix}, Extreme Wide Establishing Shot, 24mm lens, VISUAL_DNA: {dna}, resting on an architect drafting table covered in blueprints and paper scraps, slow pan.", "revelacao_papel", "Toda grande criação começa na simplicidade de um único traço no papel."),
                ("O DESPERTAR", f"{prefix}, Medium Focus Shot, 50mm lens, VISUAL_DNA: {dna}, graphite tip glowing with delicate yellow highlights as wood grain subtly fractures into petal folds, slow dolly-in.", "zoom_parallax", "Onde antes havia apenas madeira e grafite, uma centelha de vida começa a pulsar."),
                ("A ECLOSÃO", f"{prefix}, Macro Detail Shot, 85mm lens, VISUAL_DNA: {dna}, extreme macro of paper petals delicately peeling away from the wooden pencil core, dynamic tilt tracking.", "engrenagens", "Camada por camada, a matéria rígida se curva diante da força da imaginação."),
                ("A METAMORFOSE", f"{prefix}, Dynamic Low-Angle Action Shot, 35mm lens, VISUAL_DNA: {dna}, rapid burst of colorful origami petals unfurling in dynamic motion, kinetic low-angle push.", "moedas_caindo", "O lápis se desfaz e floresce: o instrumento se transforma na própria obra de arte."),
                ("O IMPACTO", f"{prefix}, High-Angle Wide Impact Shot, 28mm lens, VISUAL_DNA: {dna}, vibrant yellow paper pollen particles showering the workspace bringing illustrations to life, sweeping crane.", "nuvens_deriva", "O pólen dourado da criatividade se espalha, colorindo tudo ao seu redor."),
                ("O TRIUNFO", f"{prefix}, Hero Medium Resolution Shot, 50mm lens, VISUAL_DNA: {dna}, fully bloomed glowing origami lotus standing proud amidst architectural sketches, parallax pull-out.", "zoom_parallax", "A verdadeira arte não apenas desenha a beleza: ela a faz florescer no mundo real.")
            ]
        # Tema 3: Tecnologia / Inteligência Artificial / Negócios
        elif any(w in text_lower for w in ["ia", "ai", "inteligência", "inteligencia", "robô", "robo", "futuro", "negócio", "negocio", "mercado", "empresa"]):
            dna = "A futuristic archival collage of cybernetic gears, glowing circuits, vintage newspaper headlines, and bright canary-yellow infographic markers"
            beats = [
                ("A REVOLUÇÃO", f"{prefix}, Extreme Wide Establishing Shot, 24mm lens, VISUAL_DNA: {dna}, massive editorial wall of financial graphs, algorithms and paper cutouts, slow pan.", "engrenagens", "Uma revolução invisível está redesenhando as fronteiras de toda a economia global."),
                ("O DESAFIO", f"{prefix}, Medium Focus Shot, 50mm lens, VISUAL_DNA: {dna}, central vintage human silhouette confronting complex geometric AI neural pathways, slow dolly-in.", "zoom_parallax", "Modelos tradicionais desmoronam diante da velocidade implacável da automação inteligente."),
                ("O NÚCLEO", f"{prefix}, Macro Detail Shot, 85mm lens, VISUAL_DNA: {dna}, extreme close-up of mechanical clockwork merging with glowing fiber optic threads, dynamic tracking.", "engrenagens", "Aqueles que dominam a nova engrenagem transformam horas de esforço em segundos de impacto."),
                ("A DISRUPÇÃO", f"{prefix}, Dynamic Low-Angle Action Shot, 35mm lens, VISUAL_DNA: {dna}, towering kinetic charts and paper graphs rocketing upward with bold yellow accents, kinetic push.", "moedas_caindo", "A barreira de entrada caiu: pequenas ideias agora movem impérios gigantescos."),
                ("A ESCALA", f"{prefix}, High-Angle Wide Impact Shot, 28mm lens, VISUAL_DNA: {dna}, global interconnected network of digital cutouts and financial data nodes glowing bright, sweeping crane.", "revelacao_papel", "O mundo nunca mais será o mesmo para quem decide liderar a vanguarda."),
                ("O FUTURO", f"{prefix}, Hero Medium Resolution Shot, 50mm lens, VISUAL_DNA: {dna}, triumphant visionary icon looking over a gleaming horizon of innovation, parallax pull-out.", "zoom_parallax", "O futuro pertence àqueles que não apenas assistem à mudança, mas a constroem hoje.")
            ]
        # Tema 4: Padrão Inspirador Adaptado
        else:
            subj = script_text.split('.')[0][:40] if script_text else "A compelling visual concept"
            dna = f"A stylized archival cutout of {subj} rendered in vintage papercraft collage with Canary Yellow #FACC15 accents and aged newsprint texture"
            beats = [
                ("O CHAMADO", f"{prefix}, Extreme Wide Establishing Shot, 24mm lens, VISUAL_DNA: {dna}, dramatic wide environment with layered vintage parchment, slow pan.", "revelacao_papel", "Toda grande história começa no momento exato em que decidimos desafiar o comum."),
                ("O FOCO", f"{prefix}, Medium Focus Shot, 50mm lens, VISUAL_DNA: {dna}, crisp cutout silhouette with yellow highlighter halo, slow dolly-in.", "zoom_parallax", "O olhar atento descobre oportunidades onde os outros enxergavam apenas rotina."),
                ("O DETALHE", f"{prefix}, Macro Detail Shot, 85mm lens, VISUAL_DNA: {dna}, extreme macro of intricate paper textures and handcrafted edges, dynamic tilt.", "engrenagens", "São os detalhes minuciosos e a perseverança silenciosa que constroem a grandeza."),
                ("O CLÍMAX", f"{prefix}, Dynamic Low-Angle Action Shot, 35mm lens, VISUAL_DNA: {dna}, kinetic dynamic movement with dramatic shadows and high contrast, low-angle push.", "moedas_caindo", "No instante da virada, cada peça do mosaico se encaixa com precisão absoluta."),
                ("A EXPANSÃO", f"{prefix}, High-Angle Wide Impact Shot, 28mm lens, VISUAL_DNA: {dna}, sweeping panoramic view of the entire scene reacting in harmony, sweeping crane.", "nuvens_deriva", "O resultado reverbera além das expectativas, inspirando todos ao redor."),
                ("O TRIUNFO", f"{prefix}, Hero Medium Resolution Shot, 50mm lens, VISUAL_DNA: {dna}, final iconic composition with golden parchment radiance, parallax pull-out.", "zoom_parallax", "A visão inicial se consolida como um legado inquestionável para o amanhã.")
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
        """
        Orquestra a chamada de LLM com prioridade para modelos rápidos e confiáveis:
        1. OpenRouter (deepseek/deepseek-chat e meta-llama/llama-3.3-70b-instruct) -> altíssima velocidade e coerência.
        2. Gemini Google API (gemini-3.6-flash e gemini-3.5-flash).
        """
        # 1. Prioridade OpenRouter (DeepSeek / Llama 70B respondem com precisão de JSON em ~3s)
        if self.openrouter_key:
            for or_model in ["deepseek/deepseek-chat", "meta-llama/llama-3.3-70b-instruct"]:
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
                        "temperature": 0.35
                    }
                    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=22)
                    if r.status_code == 200:
                        d = r.json()
                        choices = d.get("choices", [])
                        if choices:
                            txt = choices[0]["message"]["content"]
                            if txt and len(txt.strip()) > 30:
                                return txt
                except Exception as e:
                    print(f"[VoxMotionEngine] OpenRouter API ({or_model}) aviso: {e}")

        # 2. Alternativa direta Gemini com modelos ativos e timeout curto (8s)
        if self.gemini_key:
            for gemini_model in ["gemini-3.6-flash", "gemini-3.5-flash"]:
                try:
                    import requests
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={self.gemini_key}"
                    payload = {
                        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_content}"}]}],
                        "generationConfig": {"temperature": 0.35, "maxOutputTokens": 3000}
                    }
                    r = requests.post(url, json=payload, timeout=10)
                    if r.status_code == 200:
                        d = r.json()
                        candidates = d.get("candidates", [])
                        if candidates:
                            c_parts = candidates[0].get("content", {}).get("parts", [])
                            for cp in c_parts:
                                if "text" in cp:
                                    return cp["text"]
                except Exception as e:
                    print(f"[VoxMotionEngine] Gemini API ({gemini_model}) aviso: {e}")

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
