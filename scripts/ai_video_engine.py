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


def _local_cinematic_motion(first_frame, out_path, duration=5, aspect_ratio="9:16", log=print):
    """Gera movimento cinematográfico óptico nativo via FFmpeg sem custos de GPU na nuvem."""
    import subprocess
    try:
        tw, th = (720, 1280) if aspect_ratio == "9:16" else (1280, 720)
        frames = int(float(duration) * 30)
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", first_frame,
            "-filter_complex",
            f"[0:v]scale=-1:10*ih,zoompan=z='min(zoom+0.0018,1.25)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={tw}x{th}:fps=30,"
            f"unsharp=5:5:0.8:5:5:0.0,format=yuv420p[v]",
            "-map", "[v]", "-t", str(duration), "-c:v", "libx264", "-preset", "fast", "-crf", "18", out_path
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=60)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            log("[AIVideo] OK Movimento Cinematográfico Nativo Open-Source (Custo R$ 0,00 no RunPod)")
            return out_path
    except Exception as e:
        log(f"[AIVideo] Erro motion local: {e}")
    return None


def generate_video_clip(prompt, out_path, first_frame=None, reference_images=None, duration=5,
                        aspect_ratio="9:16", timeout_s=900, is_paid=False, log=print):
    """
    Gera clipe com movimento real.
    - Se is_paid=True (VIP ou créditos pagos): utiliza GPU Dedicada Wan 2.2 no RunPod.io.
    - Se is_paid=False (bônus gratuito de 50 tokens): utiliza modelos open-source gratuitos (HuggingFace / FFmpeg),
      preservando 100% o saldo em dólares do servidor RunPod.io do fundador.
    """
    img_url = public_url_for(first_frame) if first_frame else None
    if not img_url and reference_images:
        for p in reference_images:
            img_url = public_url_for(p)
            if img_url:
                break

    # Tier Pago / Fundador VIP -> RunPod.io GPU dedicada
    if is_paid and rp.available():
        log("[AIVideo] Tier VIP/Pago: Roteando para GPU Dedicada RunPod.io (Wan 2.2 720p)")
        v = rp.wan_video(prompt, out_path, image_url=img_url, duration=duration,
                         aspect_ratio=aspect_ratio, log=log)
        if v:
            return v

    # Tier Gratuito (50 tokens de boas-vindas) -> Open-source gratuito sem cobrança no RunPod
    log("[AIVideo] Tier Gratuito: Roteando para Motor Open-Source Gratuito (Zero Custo no RunPod)")
    v_hf = _ltx_hf(prompt, out_path, first_frame, duration, aspect_ratio, log)
    if v_hf:
        return v_hf

    if first_frame and os.path.exists(first_frame):
        return _local_cinematic_motion(first_frame, out_path, duration=duration, aspect_ratio=aspect_ratio, log=log)

    return None
