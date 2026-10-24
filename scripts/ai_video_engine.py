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


def _ltx_hf(prompt, out_path, first_frame, duration, aspect_ratio, log, negative_prompt=None):
    try:
        from gradio_client import Client, handle_file
        from scripts.magnific_canvas_engine import prompt_has_human_subject
        if not negative_prompt:
            if not prompt_has_human_subject(prompt):
                negative_prompt = "worst quality, blurry, jittery, distorted, static slide, human, person, woman, girl, man, face, portrait, lady, female, people, crowd, extra limbs"
            else:
                negative_prompt = "worst quality, blurry, jittery, distorted, static slide, deformed face, extra limbs"
        client = Client("Lightricks/ltx-video-distilled", token=os.getenv("HF_TOKEN") or None)
        portrait = aspect_ratio == "9:16"
        res = client.predict(
            prompt=prompt[:900],
            negative_prompt=negative_prompt,
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
                        aspect_ratio="9:16", timeout_s=900, is_paid=False, log=print, negative_prompt=None):
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
                         aspect_ratio=aspect_ratio, negative_prompt=negative_prompt, log=log)
        if v:
            return v

    # Tier Gratuito (50 tokens de boas-vindas) -> Open-source gratuito sem cobrança no RunPod
    log("[AIVideo] Tier Gratuito: Roteando para Motor Open-Source Gratuito (Zero Custo no RunPod)")
    v_hf = _ltx_hf(prompt, out_path, first_frame, duration, aspect_ratio, log, negative_prompt=negative_prompt)
    if v_hf:
        return v_hf

    if first_frame and os.path.exists(first_frame):
        return _local_cinematic_motion(first_frame, out_path, duration=duration, aspect_ratio=aspect_ratio, log=log)

    return None


def render_start_end_movie(
    job_id: str,
    user_id: str,
    start_img_path: str,
    end_img_path: str,
    prompt: str,
    duration: int = 10,
    aspect_ratio: str = "9:16",
    out_path: str = None,
    out_filename: str = None,
    req_ip: str = None,
    is_paid: bool = False,
    log=print
):
    """
    Motor de Metamorfose Cinematográfica (Estilo Kling.ai e Higgsfield):
    Conecta o Frame Inicial (Estado A) e o Frame Final (Estado B) em um filme contínuo de 10s ou 15s.
    """
    import subprocess
    from scripts.magnific_canvas_engine import MagnificCanvasEngine, prompt_has_human_subject, sanitize_prompt_subject

    duration = 15 if int(duration or 10) >= 14 else 10
    num_takes = 3 if duration == 15 else 2
    take_dur = 5

    target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    has_human = prompt_has_human_subject(prompt)
    clean_p = sanitize_prompt_subject(prompt, "") if not has_human else prompt

    work_dir = os.path.join(os.getenv("UPLOAD_DIR", "uploads"), f"startend_{job_id[:8]}")
    os.makedirs(work_dir, exist_ok=True)
    engine = MagnificCanvasEngine()

    neg_prompt = (
        "human, person, woman, girl, female, lady, man, face, portrait, people, crowd, extra limbs, worst quality, blurry, jittery, distorted, static slide"
        if not has_human else
        "worst quality, blurry, jittery, distorted, static slide, deformed face, bad anatomy, extra limbs"
    )

    # 1. TENTATIVA DIRETA RUNPOD WAN FLF2V SE FOR TIER PAGO / VIP
    if is_paid and rp.available():
        log("[StartEnd] Tier VIP/Pago: Tentando render direto no Wan 2.1 FLF2V / Wan 2.2 (RunPod GPU)...")
        start_url = public_url_for(start_img_path)
        end_url = public_url_for(end_img_path)
        rp_direct = rp.wan_video(
            clean_p, out_path, image_url=start_url, end_image_url=end_url,
            duration=duration, aspect_ratio=aspect_ratio, negative_prompt=neg_prompt, log=log
        )
        if rp_direct and os.path.exists(rp_direct) and os.path.getsize(rp_direct) > 60000:
            log("[StartEnd] Wan FLF2V concluído com sucesso!")
            shutil.rmtree(work_dir, ignore_errors=True)
            return out_path

    # 2. METAMORFOSE NEURAL MULTI-TAKE DE CONTINUIDADE CINEMATOGRÁFICA (10s ou 15s)
    log(f"[StartEnd] Iniciando pipeline de metamorfose neural ({duration}s, {num_takes} tomadas)...")
    take_clips = []

    if duration == 10:
        # Tomada 0 (0 a 5s): Início exato no Frame A e evolução cinética
        clip_0 = os.path.join(work_dir, "take_0.mp4")
        p0 = f"{clean_p}. Beginning act: establishing the initial state, continuous physical action commences, subtle camera push-in, volumetric lighting."
        log("[StartEnd] Gerando Tomada 0 (0.0s - 5.0s)...")
        generate_video_clip(
            prompt=p0, out_path=clip_0, first_frame=start_img_path,
            duration=take_dur, aspect_ratio=aspect_ratio, is_paid=is_paid,
            negative_prompt=neg_prompt, log=log
        )
        if os.path.exists(clip_0):
            take_clips.append(clip_0)

        # Síntese do Frame Intermediário (5.0s): Fusing A & B
        mid_kf = os.path.join(work_dir, "mid_kf.jpg")
        log("[StartEnd] Sintetizando Frame Intermediário (5.0s)...")
        try:
            engine.generate_connected_node(
                prompt=f"Intermediate visual state halfway between starting scene and ending scene: {clean_p}",
                reference_images=[start_img_path, end_img_path],
                model_style="Seedream 5 Pro", aspect_ratio=aspect_ratio,
                camera_angle="macro_detail" if not has_human else "close_up_85mm",
                output_path=mid_kf, is_paid=is_paid
            )
        except Exception as e_mid:
            log(f"[StartEnd] Info síntese mid frame: {e_mid}")

        src_take1 = mid_kf if (os.path.exists(mid_kf) and os.path.getsize(mid_kf) > 5000) else end_img_path

        # Tomada 1 (5s a 10s): Clímax da transformação e ancoragem no Frame B
        clip_1 = os.path.join(work_dir, "take_1.mp4")
        p1 = f"{clean_p}. Climax act: metamorphic action completes and stabilizes seamlessly into the final destination state, razor-sharp focus."
        log("[StartEnd] Gerando Tomada 1 (5.0s - 10.0s)...")
        generate_video_clip(
            prompt=p1, out_path=clip_1, first_frame=src_take1,
            duration=take_dur, aspect_ratio=aspect_ratio, is_paid=is_paid,
            negative_prompt=neg_prompt, log=log
        )
        if os.path.exists(clip_1):
            take_clips.append(clip_1)

    else:
        # 15s (3 Tomadas de 5s cada): Início -> Metamorfose -> Resolução
        # Tomada 0 (0 a 5s)
        clip_0 = os.path.join(work_dir, "take_0.mp4")
        p0 = f"{clean_p}. Act 1 (Beginning): starting faithfully from the start state, continuous physical motion begins."
        generate_video_clip(
            prompt=p0, out_path=clip_0, first_frame=start_img_path,
            duration=take_dur, aspect_ratio=aspect_ratio, is_paid=is_paid,
            negative_prompt=neg_prompt, log=log
        )
        if os.path.exists(clip_0):
            take_clips.append(clip_0)

        # Mid Frame 1 (35% transição)
        mid_kf1 = os.path.join(work_dir, "mid_kf1.jpg")
        try:
            engine.generate_connected_node(
                prompt=f"Early stage of continuous transformation: {clean_p}",
                reference_images=[start_img_path, end_img_path],
                model_style="Seedream 5 Pro", aspect_ratio=aspect_ratio,
                camera_angle="wide_anamorphic", output_path=mid_kf1, is_paid=is_paid
            )
        except Exception:
            pass
        src_take1 = mid_kf1 if (os.path.exists(mid_kf1) and os.path.getsize(mid_kf1) > 5000) else start_img_path

        # Tomada 1 (5 a 10s)
        clip_1 = os.path.join(work_dir, "take_1.mp4")
        p1 = f"{clean_p}. Act 2 (Action): physical metamorphosis peaks with dynamic particles, camera movement and evolving textures."
        generate_video_clip(
            prompt=p1, out_path=clip_1, first_frame=src_take1,
            duration=take_dur, aspect_ratio=aspect_ratio, is_paid=is_paid,
            negative_prompt=neg_prompt, log=log
        )
        if os.path.exists(clip_1):
            take_clips.append(clip_1)

        # Mid Frame 2 (75% transição)
        mid_kf2 = os.path.join(work_dir, "mid_kf2.jpg")
        try:
            engine.generate_connected_node(
                prompt=f"Advanced stage of transformation resolving into final target: {clean_p}",
                reference_images=[end_img_path, start_img_path],
                model_style="Seedream 5 Pro", aspect_ratio=aspect_ratio,
                camera_angle="macro_detail" if not has_human else "close_up_85mm",
                output_path=mid_kf2, is_paid=is_paid
            )
        except Exception:
            pass
        src_take2 = mid_kf2 if (os.path.exists(mid_kf2) and os.path.getsize(mid_kf2) > 5000) else end_img_path

        # Tomada 2 (10 a 15s)
        clip_2 = os.path.join(work_dir, "take_2.mp4")
        p2 = f"{clean_p}. Act 3 (Ending): flawless resolution into the final end frame, stabilizing into crisp 8k composition."
        generate_video_clip(
            prompt=p2, out_path=clip_2, first_frame=src_take2,
            duration=take_dur, aspect_ratio=aspect_ratio, is_paid=is_paid,
            negative_prompt=neg_prompt, log=log
        )
        if os.path.exists(clip_2):
            take_clips.append(clip_2)

    if not take_clips:
        raise RuntimeError("Não foi possível renderizar a transição cinematográfica entre os dois frames.")

    # 3. NORMALIZAÇÃO DE RESOLUÇÃO E FPS
    norm_clips = []
    for idx, c_path in enumerate(take_clips):
        c_norm = os.path.join(work_dir, f"norm_{idx}.mp4")
        cmd_scale = [
            "ffmpeg", "-y", "-i", c_path,
            "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase:flags=lanczos,crop={target_w}:{target_h},fps=30,"
                   f"unsharp=5:5:0.6:5:5:0.0,format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "17", c_norm
        ]
        res_norm = subprocess.run(cmd_scale, capture_output=True)
        if os.path.exists(c_norm) and os.path.getsize(c_norm) > 10000:
            norm_clips.append(c_norm)

    if not norm_clips:
        norm_clips = take_clips

    # 4. MASTERIZAÇÃO COM TRANSIÇÃO CINEMATOGRÁFICA FLUIDA (XFADE / DISSOLVE SUAVE)
    merged_raw = os.path.join(work_dir, "merged_raw.mp4")
    if len(norm_clips) == 1:
        shutil.copy(norm_clips[0], merged_raw)
    elif len(norm_clips) == 2:
        # Crossfade de 0.6s entre clipe 0 e clipe 1 no ponto 4.4s
        cmd_xfade = [
            "ffmpeg", "-y",
            "-i", norm_clips[0], "-i", norm_clips[1],
            "-filter_complex", "[0:v][1:v]xfade=transition=fade:duration=0.6:offset=4.4,format=yuv420p[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", merged_raw
        ]
        subprocess.run(cmd_xfade, capture_output=True)
    elif len(norm_clips) >= 3:
        # Encadeamento suave para 3 tomadas (15 segundos)
        cmd_xfade3 = [
            "ffmpeg", "-y",
            "-i", norm_clips[0], "-i", norm_clips[1], "-i", norm_clips[2],
            "-filter_complex",
            "[0:v][1:v]xfade=transition=fade:duration=0.6:offset=4.4[v01];"
            "[v01][2:v]xfade=transition=fade:duration=0.6:offset=8.4,format=yuv420p[v]",
            "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", merged_raw
        ]
        subprocess.run(cmd_xfade3, capture_output=True)

    final_src = merged_raw if (os.path.exists(merged_raw) and os.path.getsize(merged_raw) > 20000) else norm_clips[0]

    # 5. SOUND DESIGN CINEMATOGRÁFICO AMBIENTE
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", final_src],
                           capture_output=True, text=True)
    try:
        final_dur = float(probe.stdout.strip())
    except Exception:
        final_dur = float(duration)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    cmd_audio = [
        "ffmpeg", "-y", "-i", final_src,
        "-f", "lavfi", "-i", f"anoisesrc=d={final_dur}:c=pink:r=44100:a=0.012",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path
    ]
    subprocess.run(cmd_audio, capture_output=True)
    if not os.path.exists(out_path) or os.path.getsize(out_path) < 10000:
        shutil.copy(final_src, out_path)

    shutil.rmtree(work_dir, ignore_errors=True)
    log(f"[StartEnd] Metamorfose concluída com sucesso: {out_path} ({round(final_dur, 1)}s)")
    return out_path
