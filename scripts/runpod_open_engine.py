"""
Motor 100% OPEN-SOURCE rodando em GPU do RunPod.io (Public Endpoints serverless).

Modelos open-source usados:
  - Wan 2.2 (Alibaba, Apache-2.0)  image-to-video e text-to-video 720p
  - FLUX.1 schnell / dev / Kontext-dev (Black Forest Labs)  imagens e edicao com imagem de referencia
  - Whisper large-v3 (OpenAI, MIT)  transcricao
  - Chatterbox (Resemble AI, MIT)  TTS e clonagem de voz

A chave vem exclusivamente do .env (RUNPOD_API_KEY). Nada passa pelo OpenRouter.
"""
import base64
import os
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE = "https://api.runpod.ai/v2"

EP_WAN_I2V = "wan-2-2-i2v-720"
EP_WAN_T2V = "wan-2-2-t2v-720"
EP_FLUX_SCHNELL = "black-forest-labs-flux-1-schnell"
EP_FLUX_DEV = "black-forest-labs-flux-1-dev"
EP_FLUX_KONTEXT = "black-forest-labs-flux-1-kontext-dev"
EP_WHISPER = "whisper-v3-large"
EP_CHATTERBOX = "chatterbox-turbo"


def _headers():
    return {"Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY', '').strip()}", "Content-Type": "application/json"}


def available() -> bool:
    return bool(os.getenv("RUNPOD_API_KEY", "").strip())


def run_endpoint(slug: str, payload: dict, timeout_s: int = 900, log=print):
    """Envia job assincrono e aguarda. Retorna o dict 'output' ou None."""
    if not available():
        return None
    try:
        r = requests.post(f"{BASE}/{slug}/run", headers=_headers(), json={"input": payload}, timeout=60)
        if r.status_code not in (200, 201):
            log(f"[RunPod] {slug} /run {r.status_code}: {r.text[:300]}")
            return None
        job = r.json()
        jid = job.get("id")
        start = time.time()
        status = job.get("status")
        while time.time() - start < timeout_s:
            if status == "COMPLETED":
                return job.get("output") if job.get("output") is not None else {}
            if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
                log(f"[RunPod] {slug} {status}: {str(job)[:300]}")
                return None
            time.sleep(5)
            sr = requests.get(f"{BASE}/{slug}/status/{jid}", headers=_headers(), timeout=30)
            if sr.status_code == 200:
                job = sr.json()
                status = job.get("status")
        log(f"[RunPod] {slug} timeout")
    except Exception as e:
        log(f"[RunPod] {slug} excecao: {e}")
    return None


def _find_media(obj, exts=()):
    """Procura URL http(s) ou base64 dentro do output, qualquer formato."""
    if isinstance(obj, str):
        if obj.startswith("http"):
            return obj
        if obj.startswith("data:") and "base64," in obj:
            return obj
        if len(obj) > 2000:
            return "b64:" + obj
        return None
    if isinstance(obj, dict):
        for key in ("video_url", "video", "image_url", "image", "url", "audio_url", "audio", "result", "output"):
            if key in obj:
                f = _find_media(obj[key], exts)
                if f:
                    return f
        for v in obj.values():
            f = _find_media(v, exts)
            if f:
                return f
    if isinstance(obj, list):
        for v in obj:
            f = _find_media(v, exts)
            if f:
                return f
    return None


def _save_media(ref: str, out_path: str) -> bool:
    try:
        if ref.startswith("http"):
            d = requests.get(ref, timeout=240)
            if d.status_code != 200 or len(d.content) < 2000:
                return False
            data = d.content
        else:
            b64 = ref.split("base64,", 1)[1] if "base64," in ref else ref.replace("b64:", "", 1)
            data = base64.b64decode(b64)
        with open(out_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"[RunPod] falha ao salvar midia: {e}")
        return False


def wan_video(prompt, out_path, image_url=None, duration=5, aspect_ratio="9:16", log=print):
    """Wan 2.2 (open-source) no RunPod. image_url publica => image-to-video, senao text-to-video."""
    size = {"9:16": "720*1280", "1:1": "960*960"}.get(aspect_ratio, "1280*720")
    payload = {
        "prompt": prompt[:1500],
        "negative_prompt": "blurry, low quality, static image, slideshow, still frame, distortion, deformed, text, watermark, jitter",
        "size": size,
        "duration": 10 if duration > 7 else 5,
        "seed": -1,
        "num_inference_steps": 30,
        "guidance": 5,
        "flow_shift": 5,
        "enable_prompt_optimization": False,
        "enable_safety_checker": False,
    }
    slug = EP_WAN_T2V
    if image_url:
        payload["image"] = image_url
        slug = EP_WAN_I2V
    out = run_endpoint(slug, payload, timeout_s=900, log=log)
    if out is None:
        return None
    ref = _find_media(out)
    if ref and _save_media(ref, out_path):
        log(f"[RunPod] Wan 2.2 OK ({slug})")
        return out_path
    log(f"[RunPod] Wan sem midia no output: {str(out)[:300]}")
    return None


def flux_image(prompt, out_path, ref_image_url=None, aspect_ratio="9:16", quality="schnell", log=print):
    """FLUX.1 (open-source). Com imagem de referencia usa Kontext-dev (preserva o sujeito)."""
    size = {"9:16": (768, 1344), "1:1": (1024, 1024), "21:9": (1536, 640)}.get(aspect_ratio, (1344, 768))
    if ref_image_url:
        out = run_endpoint(EP_FLUX_KONTEXT, {
            "prompt": prompt[:1500], "image": ref_image_url, "size": f"{size[0]}*{size[1]}",
            "num_inference_steps": 28, "guidance": 2.5, "seed": -1, "enable_safety_checker": False,
        }, timeout_s=300, log=log)
    else:
        slug = EP_FLUX_DEV if quality == "dev" else EP_FLUX_SCHNELL
        out = run_endpoint(slug, {
            "prompt": prompt[:1500], "negative_prompt": "", "width": size[0], "height": size[1],
            "size": f"{size[0]}*{size[1]}", "num_inference_steps": 4 if slug == EP_FLUX_SCHNELL else 28,
            "guidance": 3.5, "seed": -1, "num_images": 1, "output_format": "jpeg", "enable_safety_checker": False,
        }, timeout_s=300, log=log)
    if out is None:
        return None
    ref = _find_media(out)
    if ref and _save_media(ref, out_path):
        try:
            import subprocess, shutil
            tmp_crop = out_path + ".tmp.jpg"
            cmd = [
                "ffmpeg", "-y", "-i", out_path,
                "-vf", f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=increase:flags=lanczos,crop={size[0]}:{size[1]}",
                "-q:v", "1", tmp_crop
            ]
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode == 0 and os.path.exists(tmp_crop):
                shutil.move(tmp_crop, out_path)
        except Exception as e_crop:
            log(f"[RunPod] Lanczos crop info: {e_crop}")
        return out_path
    log(f"[RunPod] FLUX sem imagem no output: {str(out)[:300]}")
    return None
