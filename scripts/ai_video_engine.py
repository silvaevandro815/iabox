"""
Motor de VIDEO REAL 100% open-source (Wan 2.2 no RunPod GPU, com LTX-Video no HuggingFace como reserva).
Nao usa OpenRouter. Mantem a mesma assinatura usada pelo restante da plataforma.
"""
import os
import shutil
import uuid

from scripts import runpod_open_engine as rp

PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "https://iabox.evandrosilvagallina.cloud").rstrip("/")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")


def public_url_for(local_path: str):
    """Garante que o arquivo esteja em /output (servido publicamente) e devolve a URL https."""
    if not local_path or not os.path.exists(local_path):
        return None
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    name = os.path.basename(local_path)
    dest = os.path.join(OUTPUT_DIR, name)
    if os.path.abspath(dest) != os.path.abspath(local_path):
        name = f"pub_{uuid.uuid4().hex[:8]}_{name}"
        dest = os.path.join(OUTPUT_DIR, name)
        shutil.copy(local_path, dest)
    return f"{PUBLIC_BASE}/output/{name}"


def _ltx_hf(prompt, out_path, first_frame, duration, aspect_ratio, log):
    try:
        from gradio_client import Client, handle_file
        client = Client("Lightricks/ltx-video-distilled", token=os.getenv("HF_TOKEN") or None)
        portrait = aspect_ratio == "9:16"
        res = client.predict(
            prompt=prompt[:900],
            negative_prompt="worst quality, blurry, jittery, distorted, static slide",
            input_image_filepath=handle_file(first_frame) if first_frame else None,
            input_video_filepath=None,
            height_ui=768 if portrait else 512,
            width_ui=512 if portrait else 768,
            mode="image-to-video" if first_frame else "text-to-video",
            duration_ui=min(float(duration), 5.0),
            ui_frames_to_use=9,
            seed_ui=42,
            randomize_seed=True,
            ui_guidance_scale=1.0,
            improve_texture_flag=True,
            api_name="/image_to_video" if first_frame else "/text_to_video",
        )
        v = res[0]["video"] if isinstance(res[0], dict) else res[0]
        if v and os.path.exists(v):
            shutil.copy(v, out_path)
            log("[AIVideo] OK LTX-Video (HuggingFace)")
            return out_path
    except Exception as e:
        log(f"[AIVideo] LTX indisponivel: {e}")
    return None


def generate_video_clip(prompt, out_path, first_frame=None, reference_images=None, duration=5,
                        aspect_ratio="9:16", timeout_s=900, log=print):
    """Gera clipe com movimento real. Retorna caminho do MP4 ou None."""
    img_url = public_url_for(first_frame) if first_frame else None
    if not img_url and reference_images:
        for p in reference_images:
            img_url = public_url_for(p)
            if img_url:
                break

    if rp.available():
        v = rp.wan_video(prompt, out_path, image_url=img_url, duration=duration,
                         aspect_ratio=aspect_ratio, log=log)
        if v:
            return v
    return _ltx_hf(prompt, out_path, first_frame, duration, aspect_ratio, log)
