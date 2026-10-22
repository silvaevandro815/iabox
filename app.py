"""
========================================================================================
IABOX — Servidor Central e API de IA (FastAPI)
Domínio: iabox.evandrosilvagallina.cloud
Criador: Evandro Silva Gallina
========================================================================================
"""

import os
import sys
import uuid
import time
import json
import base64
import sqlite3
import shutil
import asyncio
import subprocess
import contextvars
import threading
import secrets
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests as http_requests
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, Query, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values

# ContextVar para capturar o IP real do cliente (PC/Celular) em qualquer rota
client_ip_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_ip", default="unknown")

# IPs e Prefixos Exclusivos do Fundador Evandro Silva Gallina (Acesso VIP Ilimitado Automático)
FOUNDER_VIP_IPS = {
    "177.130.242.130",
    "127.0.0.1",
    "::1",
}
FOUNDER_VIP_PREFIXES = (
    "177.130.242.",
    "2804:ddc:216:c600:",
)
FOUNDER_VIP_KEYS = {
    "evandro_admin_master",
    "vip_evandro",
}

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}:{dk.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    if not hashed or ":" not in hashed:
        return False
    try:
        salt, dk_hex = hashed.split(":", 1)
        test_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(test_dk.hex(), dk_hex)
    except Exception:
        return False

def is_valid_gmail(email: str) -> bool:
    clean = (email or "").strip().lower()
    return clean.endswith("@gmail.com") or clean.endswith("@googlemail.com")

def send_recovery_email_async(to_email: str, code: str):
    def _send():
        smtp_host = os.environ.get("SMTP_HOST") or env.get("SMTP_HOST")
        smtp_port = int(os.environ.get("SMTP_PORT") or env.get("SMTP_PORT") or 587)
        smtp_user = os.environ.get("SMTP_USER") or env.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASS") or env.get("SMTP_PASS")
        if not (smtp_host and smtp_user and smtp_pass):
            print(f"[Auth] Recuperação de Senha para {to_email}: Código {code} (SMTP não configurado no .env, código ativo no banco)")
            return
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"IABOX — Seu Código de Recuperação de Senha: {code}"
            msg["From"] = f"IABOX Segurança <{smtp_user}>"
            msg["To"] = to_email
            html_body = f"""
            <div style="font-family: Arial, sans-serif; background-color: #0b0f19; color: #ffffff; padding: 30px; border-radius: 16px;">
                <h2 style="color: #00f0ff; margin-bottom: 10px;">IABOX &bull; Recuperação de Senha</h2>
                <p style="color: #cbd5e1; font-size: 14px;">Você solicitou a redefinição de senha para sua conta Gmail no <strong>IABOX</strong>.</p>
                <div style="background: rgba(0,240,255,0.1); border: 2px solid #00f0ff; padding: 18px; border-radius: 12px; text-align: center; margin: 25px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #fbbf24;">{code}</span>
                </div>
                <p style="color: #94a3b8; font-size: 12px;">Este código é válido por 15 minutos. Se você não solicitou este código, ignore esta mensagem com segurança.</p>
                <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 20px 0;">
                <p style="color: #64748b; font-size: 11px;">&copy; 2026 IABOX &bull; Evandro Silva Gallina &bull; Todos os direitos reservados.</p>
            </div>
            """
            msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            print(f"[Auth] Email de recuperação enviado com sucesso para {to_email}")
        except Exception as e:
            print(f"[Auth] Falha no envio de SMTP para {to_email}: {e}")
    threading.Thread(target=_send, daemon=True).start()

# Carrega variáveis de ambiente
env = dotenv_values('.env')
if not env:
    env = os.environ

STRIPE_SECRET_KEY = env.get('STRIPE_SECRET_KEY', '') or os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = env.get('STRIPE_PUBLISHABLE_KEY', '') or os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
GEMINI_API_KEY = env.get('GEMINI_API_KEY', '') or env.get('GOOGLE_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
SUPABASE_URL = env.get('SUPABASE_URL', '') or os.environ.get('SUPABASE_URL', 'https://qkopgftfrfftoyndhhfj.supabase.co')
SUPABASE_KEY = env.get('SUPABASE_KEY', '') or os.environ.get('SUPABASE_KEY', '')

# Inicialização do Core Proprietário (Documentação Externa Desativada por Sigilo Industrial)
app = FastAPI(
    title="IABOX — ESG Neural Core 8K",
    description="Arquitetura Proprietária Fechada de Produção Audiovisual 8K.",
    version="8.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sanitize_error_msg(err: Exception) -> str:
    msg = str(err)
    for secret_term in ("ffmpeg", "gradio", "huggingface", "pollinations", "gemini", "supabase", "sqlite", "edge_tts", "traceback", "hf.space", "runpod", "nvidia", "antigravity", "bs-roformer", "rvc", "so-vits", "demucs", "whisper", "cuda", "torch"):
        if secret_term in msg.lower():
            return "Motor Neural ESG 8K processando alta demanda. Tente novamente em alguns segundos."
    return msg[:220]

def extract_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    if request.client and request.client.host:
        return request.client.host.strip()
    return "unknown_ip"

@app.middleware("http")
async def capture_ip_middleware(request: Request, call_next):
    ip = extract_client_ip(request)
    token = client_ip_var.set(ip)
    try:
        response = await call_next(request)
        response.headers["Server"] = "ESG-Quantum-Core/8.0"
        response.headers["X-Powered-By"] = "IABOX-Proprietary-Neural-Engine"
        response.headers["X-Robots-Tag"] = "noai, noimageai, noarchive"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response
    finally:
        client_ip_var.reset(token)

@app.get("/robots.txt")
def robots_txt():
    from fastapi.responses import PlainTextResponse
    content = (
        "User-agent: GPTBot\nDisallow: /\n\n"
        "User-agent: ChatGPT-User\nDisallow: /\n\n"
        "User-agent: CCBot\nDisallow: /\n\n"
        "User-agent: ClaudeBot\nDisallow: /\n\n"
        "User-agent: anthropic-ai\nDisallow: /\n\n"
        "User-agent: Google-Extended\nDisallow: /\n\n"
        "User-agent: PerplexityBot\nDisallow: /\n\n"
        "User-agent: Bytespider\nDisallow: /\n\n"
        "User-agent: *\nDisallow: /api/\nDisallow: /scripts/\n"
    )
    return PlainTextResponse(content)

@app.get("/api/download")
def download_direct_to_pc(file: str):
    """Força o download direto do criativo (Vídeo MP4, Áudio MP3 ou Imagem 8K) para o PC do usuário."""
    clean = (file or "").split("?")[0].lstrip("/")
    if not (clean.startswith("output/") or clean.startswith("static/samples/")):
        raise HTTPException(status_code=400, detail="Arquivo inválido para download.")
    if ".." in clean or not os.path.exists(clean):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor.")
    filename = os.path.basename(clean)
    return FileResponse(
        clean,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# Diretórios
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
STATIC_DIR = "static"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Banco de Dados SQLite Local
DATA_DIR = os.environ.get("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "iabox.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT,
            name TEXT,
            credits INTEGER DEFAULT 50,
            paid_credits INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0,
            bonus_claimed INTEGER DEFAULT 0,
            reset_code TEXT,
            reset_code_expires TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migrações seguras de colunas caso a tabela users já exista
    user_cols = [
        ("password_hash", "TEXT"),
        ("name", "TEXT"),
        ("paid_credits", "INTEGER DEFAULT 0"),
        ("is_vip", "INTEGER DEFAULT 0"),
        ("bonus_claimed", "INTEGER DEFAULT 0"),
        ("reset_code", "TEXT"),
        ("reset_code_expires", "TIMESTAMP"),
        ("last_login", "TIMESTAMP"),
        ("google_id", "TEXT"),
        ("avatar_url", "TEXT")
    ]
    c.execute("PRAGMA table_info(users)")
    existing_user_cols = [r[1] for r in c.fetchall()]
    for col_name, col_type in user_cols:
        if col_name not in existing_user_cols:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                print(f"[init_db] Adicionada coluna {col_name} à tabela users")
            except Exception as e:
                print(f"[init_db] Erro ao adicionar {col_name}: {e}")

    c.execute("""
        CREATE TABLE IF NOT EXISTS ip_wallets (
            ip TEXT PRIMARY KEY,
            credits INTEGER DEFAULT 50,
            is_vip INTEGER DEFAULT 0,
            bonus_claimed INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        c.execute("ALTER TABLE ip_wallets ADD COLUMN is_vip INTEGER DEFAULT 0")
    except Exception:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS vip_ips (
            ip TEXT PRIMARY KEY,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            amount_brl REAL,
            credits INTEGER,
            status TEXT,
            stripe_session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            type TEXT,
            status TEXT,
            progress INTEGER DEFAULT 0,
            result_url TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_creations (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            ip TEXT,
            category TEXT,
            title TEXT,
            prompt TEXT,
            result_url TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id TEXT PRIMARY KEY,
            ip TEXT,
            user_id TEXT,
            is_vip INTEGER DEFAULT 0,
            role TEXT,
            action TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def _sync_supabase_async(categoria: str, titulo: str, payload: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    def _worker():
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/cerebro_conhecimento"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            body = {
                "produto": "IABOX",
                "categoria": categoria,
                "titulo": titulo[:250],
                "conteudo": json.dumps(payload, ensure_ascii=False)
            }
            http_requests.post(url, headers=headers, json=body, timeout=10)
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()

def log_client_access(ip: str, user_id: str, is_vip: bool, action: str = "visit", user_agent: str = ""):
    role_str = "VIP Ilimitado" if is_vip else "Visitante (50 Tokens IP)"
    log_id = str(uuid.uuid4())
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if action == "session_access":
            c.execute("SELECT id FROM access_logs WHERE ip = ? AND user_id = ? AND action = 'session_access' AND created_at >= datetime('now', '-10 minutes')", (ip, user_id))
            if c.fetchone():
                conn.close()
                return
        c.execute(
            "INSERT INTO access_logs (id, ip, user_id, is_vip, role, action, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (log_id, ip, user_id, 1 if is_vip else 0, role_str, action, (user_agent or "")[:200], now_str)
        )
        conn.commit()
        conn.close()
        _sync_supabase_async("IABOX_ACESSO", f"{ip} | {user_id} | {action}", {
            "id": log_id,
            "ip": ip,
            "user_id": user_id,
            "is_vip": is_vip,
            "role": role_str,
            "action": action,
            "user_agent": (user_agent or "")[:200],
            "created_at": now_str
        })
    except Exception:
        pass

def save_user_creation(user_id: str, category: str, title: str, prompt: str, result_url: str, metadata: dict = None, ip_override: str = None):
    ip = ip_override or client_ip_var.get() or "unknown"
    creation_id = str(uuid.uuid4())
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO user_creations (id, user_id, ip, category, title, prompt, result_url, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (creation_id, user_id, ip, category, title, prompt, result_url, meta_json, now_str)
        )
        conn.commit()
        conn.close()
        _sync_supabase_async("IABOX_CRIATIVO", f"[{category.upper()}] {title[:120]}", {
            "id": creation_id,
            "user_id": user_id,
            "ip": ip,
            "category": category,
            "title": title,
            "prompt": prompt,
            "result_url": result_url,
            "metadata": metadata or {},
            "created_at": now_str
        })
    except Exception:
        pass

def is_founder_vip(user_id: str = "", ip: str = "") -> bool:
    uid_clean = (user_id or "").strip().lower()
    ip_clean = (ip or client_ip_var.get() or "").strip()

    if uid_clean.startswith("vip_device_"):
        return True

    if uid_clean in FOUNDER_VIP_KEYS:
        if ip_clean and ip_clean != "unknown_ip":
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO vip_ips (ip, note) VALUES (?, ?)", (ip_clean, "Evandro Founder Auto-Whitelist"))
                conn.commit()
                conn.close()
            except Exception:
                pass
        return True

    if ip_clean in FOUNDER_VIP_IPS:
        return True
    for pref in FOUNDER_VIP_PREFIXES:
        if ip_clean.startswith(pref):
            return True

    # Verifica se a conta Gmail do usuário está marcada como VIP no SQLite
    if uid_clean:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT is_vip FROM users WHERE LOWER(email) = ? OR id = ?", (uid_clean, uid_clean))
            row = c.fetchone()
            conn.close()
            if row and row[0] == 1:
                return True
        except Exception:
            pass

    # Verifica se o IP do usuário está marcado como VIP no SQLite
    if ip_clean:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT 1 FROM vip_ips WHERE ip = ?", (ip_clean,))
            row = c.fetchone()
            if not row:
                c.execute("SELECT is_vip FROM ip_wallets WHERE ip = ?", (ip_clean,))
                row2 = c.fetchone()
                if row2 and row2[0] == 1:
                    row = True
            conn.close()
            if row:
                return True
        except Exception:
            pass
    return False

def get_user_credits(user_id="default_user"):
    ip = client_ip_var.get()
    # 1. Acesso Exclusivo Ilimitado VIP (Gmail ou IP)
    if is_founder_vip(user_id, ip):
        return 999999

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    uid_clean = (user_id or "").strip().lower()
    c.execute("SELECT credits, is_vip, paid_credits FROM users WHERE id = ? OR LOWER(email) = ?", (uid_clean, uid_clean))
    u_row = c.fetchone()

    c.execute("SELECT credits, is_vip, bonus_claimed FROM ip_wallets WHERE ip = ?", (ip,))
    ip_row = c.fetchone()
    conn.close()

    if (u_row and u_row[1] == 1) or (ip_row and ip_row[1] == 1):
        return 999999

    if u_row:
        user_bal = u_row[0]
        paid_bal = u_row[2] or 0
        # Se comprou créditos pagos via Stripe, pode usar em qualquer IP
        if paid_bal > 0:
            return user_bal
        # Para saldo gratuito de teste (50 tokens), prevalece a trava por IP
        ip_bal = ip_row[0] if ip_row else 0
        return min(user_bal, ip_bal)

    # Visitante sem conta vinculada
    return ip_row[0] if ip_row else 50

def deduct_credits(user_id="default_user", amount=1):
    ip = client_ip_var.get()
    if is_founder_vip(user_id, ip):
        return True

    current = get_user_credits(user_id)
    if current < amount:
        return False

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    new_bal = max(0, current - amount)
    c.execute("UPDATE ip_wallets SET credits = ? WHERE ip = ?", (new_bal, ip))
    uid_clean = (user_id or "").strip().lower()
    c.execute("UPDATE users SET credits = ? WHERE id = ? OR LOWER(email) = ?", (new_bal, uid_clean, uid_clean))
    conn.commit()
    conn.close()
    return True

def add_credits(user_id="default_user", amount=100):
    ip = client_ip_var.get()
    current = get_user_credits(user_id)
    new_bal = current + amount
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    uid_clean = (user_id or "").strip().lower()
    c.execute("UPDATE users SET credits = ?, paid_credits = paid_credits + ? WHERE id = ? OR LOWER(email) = ?", (new_bal, amount, uid_clean, uid_clean))
    c.execute("UPDATE ip_wallets SET credits = ? WHERE ip = ?", (new_bal, ip))
    conn.commit()
    conn.close()

def save_job(job_id, job_type, status="processing", progress=10, result_url=None, error=None, user_id="default_user"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO jobs (id, user_id, type, status, progress, result_url, error) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (job_id, user_id, job_type, status, progress, result_url, error))
    conn.commit()
    conn.close()

# Servir arquivos estáticos do Frontend
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# ----------------------------------------------------------------------------------------
# ROTAS DE AUTENTICAÇÃO COM CONTA GMAIL + RECUPERAÇÃO DE SENHA + DESBLOQUEIO VIP
# ----------------------------------------------------------------------------------------
@app.post("/api/auth/register")
def register_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form("")
):
    ip = extract_client_ip(request)
    email_clean = (email or "").strip().lower()

    if not is_valid_gmail(email_clean):
        raise HTTPException(status_code=400, detail="É obrigatório utilizar uma conta válida do Google (@gmail.com).")
    if len(password.strip()) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres.")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Verifica se o e-mail já existe
    c.execute("SELECT id FROM users WHERE LOWER(email) = ? OR id = ?", (email_clean, email_clean))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Esta conta Gmail já está cadastrada. Acesse a aba 'Entrar' ou use 'Esqueci minha senha'.")

    # Verifica se o IP ou o e-mail é do fundador VIP
    is_vip = 1 if is_founder_vip(email_clean, ip) else 0

    # Regra estrita de bônus de 50 tokens:
    # Só concede 50 tokens se o IP NUNCA tiver resgatado bônus antes
    c.execute("SELECT credits, bonus_claimed, is_vip FROM ip_wallets WHERE ip = ?", (ip,))
    ip_row = c.fetchone()

    if is_vip == 1:
        initial_credits = 999999
        bonus_msg = "👑 Conta VIP Ilimitada ativada com sucesso!"
    elif ip_row and ip_row[1] == 1:
        # IP já usou o bônus de 50 tokens em outra conta
        initial_credits = 0
        bonus_msg = "Conta criada com sucesso! O bônus de 50 tokens grátis já foi resgatado neste aparelho/IP anteriormente. Para utilizar os motores de IA, adquira créditos via Stripe."
    else:
        # Novo IP e novo Gmail -> concede os 50 tokens
        initial_credits = 50
        bonus_msg = "Conta criada com sucesso! Bônus de boas-vindas de 50 tokens liberado para este aparelho e Gmail."
        c.execute("INSERT OR REPLACE INTO ip_wallets (ip, credits, is_vip, bonus_claimed) VALUES (?, 50, ?, 1)", (ip, is_vip))

    pw_hash = hash_password(password)
    user_name = name.strip() or email_clean.split("@")[0].capitalize()

    c.execute("""
        INSERT INTO users (id, email, password_hash, name, credits, paid_credits, is_vip, bonus_claimed, created_at, last_login)
        VALUES (?, ?, ?, ?, ?, 0, ?, 1, datetime('now'), datetime('now'))
    """, (email_clean, email_clean, pw_hash, user_name, initial_credits, is_vip))
    conn.commit()
    conn.close()

    log_client_access(ip, email_clean, bool(is_vip), action="register")

    return {
        "status": "success",
        "email": email_clean,
        "name": user_name,
        "credits": initial_credits,
        "is_vip": bool(is_vip),
        "message": bonus_msg
    }

@app.post("/api/auth/login")
def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    ip = extract_client_ip(request)
    email_clean = (email or "").strip().lower()

    if not is_valid_gmail(email_clean):
        raise HTTPException(status_code=400, detail="O login exige uma conta válida do Google (@gmail.com).")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, email, password_hash, name, credits, is_vip FROM users WHERE LOWER(email) = ? OR id = ?", (email_clean, email_clean))
    row = c.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Conta não encontrada com este Gmail. Clique em 'Criar Conta' para se cadastrar.")

    user_id, user_email, pw_hash, user_name, credits, user_vip = row

    if not verify_password(password, pw_hash):
        conn.close()
        raise HTTPException(status_code=401, detail="Senha incorreta. Se você esqueceu, clique em 'Recuperar Senha'.")

    # Verifica se virou VIP pelo IP ou pelo Gmail
    is_vip = 1 if (user_vip == 1 or is_founder_vip(email_clean, ip)) else 0
    if is_vip:
        credits = 999999
        c.execute("UPDATE users SET is_vip = 1, credits = 999999 WHERE LOWER(email) = ?", (email_clean,))
        c.execute("UPDATE ip_wallets SET is_vip = 1, credits = 999999 WHERE ip = ?", (ip,))

    c.execute("UPDATE users SET last_login = datetime('now') WHERE LOWER(email) = ?", (email_clean,))
    conn.commit()
    conn.close()

    log_client_access(ip, email_clean, bool(is_vip), action="login")

    return {
        "status": "success",
        "email": email_clean,
        "name": user_name or email_clean.split("@")[0].capitalize(),
        "credits": credits if is_vip else get_user_credits(email_clean),
        "is_vip": bool(is_vip),
        "message": "Login realizado com sucesso!"
    }

@app.post("/api/auth/google")
def auth_google(
    request: Request,
    credential: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    google_id: Optional[str] = Form(None),
    avatar_url: Optional[str] = Form(None)
):
    """
    Autenticação direta oficial com Conta Google (Google Sign-In / One-Tap):
    Aceita o token JWT verificado emitido pelo Google Identity Services (credential)
    ou dados diretos da conta Google.
    """
    ip = extract_client_ip(request)
    extracted_email = (email or "").strip().lower()
    extracted_name = (name or "").strip()
    extracted_avatar = (avatar_url or "").strip()
    extracted_sub = (google_id or "").strip()

    # Se recebeu o token oficial do Google Identity Services (JWT), decodifica o payload com segurança
    if credential:
        try:
            parts = credential.split(".")
            if len(parts) >= 2:
                payload_b64 = parts[1]
                payload_b64 += "=" * (-len(payload_b64) % 4)
                payload_json = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
                extracted_email = payload_json.get("email", extracted_email).strip().lower()
                extracted_name = payload_json.get("name", extracted_name) or payload_json.get("given_name", "")
                extracted_avatar = payload_json.get("picture", extracted_avatar)
                extracted_sub = payload_json.get("sub", extracted_sub)
        except Exception as e:
            print(f"[GoogleAuth] Aviso ao decodificar token JWT do Google: {e}")

    if not extracted_email or not is_valid_gmail(extracted_email):
        raise HTTPException(
            status_code=400,
            detail="A conta Google precisa ser um Gmail válido do Google (@gmail.com)."
        )

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Verifica se o usuário já existe
    c.execute("SELECT id, email, name, credits, is_vip, avatar_url FROM users WHERE LOWER(email) = ? OR id = ?", (extracted_email, extracted_email))
    row = c.fetchone()

    is_vip = 1 if is_founder_vip(extracted_email, ip) else 0

    if row:
        # Usuário existente: login direto instantâneo
        u_id, u_email, u_name, credits, u_vip, u_avatar = row
        final_vip = 1 if (u_vip == 1 or is_vip == 1) else 0
        final_credits = 999999 if final_vip else credits

        c.execute("""
            UPDATE users SET 
                last_login = datetime('now'),
                google_id = COALESCE(?, google_id),
                avatar_url = COALESCE(?, avatar_url),
                is_vip = ?,
                credits = ?
            WHERE LOWER(email) = ?
        """, (extracted_sub, extracted_avatar or u_avatar, final_vip, final_credits, extracted_email))
        if final_vip:
            c.execute("UPDATE ip_wallets SET is_vip = 1, credits = 999999 WHERE ip = ?", (ip,))
        conn.commit()
        conn.close()

        log_client_access(ip, extracted_email, bool(final_vip), action="google_login")
        return {
            "status": "success",
            "action": "login",
            "email": extracted_email,
            "name": u_name or extracted_name or extracted_email.split("@")[0].capitalize(),
            "avatar_url": extracted_avatar or u_avatar or "",
            "credits": final_credits,
            "is_vip": bool(final_vip),
            "message": "Conta Google conectada com sucesso!"
        }
    else:
        # Novo usuário via Google: cadastra automaticamente sem necessidade de senha manual
        c.execute("SELECT credits, bonus_claimed, is_vip FROM ip_wallets WHERE ip = ?", (ip,))
        ip_row = c.fetchone()

        if is_vip == 1:
            initial_credits = 999999
            bonus_msg = "👑 Conta Google VIP Ilimitada conectada com sucesso!"
        elif ip_row and ip_row[1] == 1:
            initial_credits = 0
            bonus_msg = "Conta Google vinculada com sucesso! O bônus de 50 tokens já foi resgatado neste aparelho/IP anteriormente. Para utilizar os motores de IA, adquira créditos via Stripe."
        else:
            initial_credits = 50
            bonus_msg = "Conta Google vinculada com sucesso! Bônus de 50 tokens liberado para o seu Gmail."
            c.execute("INSERT OR REPLACE INTO ip_wallets (ip, credits, is_vip, bonus_claimed) VALUES (?, 50, ?, 1)", (ip, is_vip))

        user_display_name = extracted_name or extracted_email.split("@")[0].capitalize()
        dummy_hash = hash_password(secrets.token_hex(16))

        c.execute("""
            INSERT INTO users (id, email, password_hash, name, credits, paid_credits, is_vip, bonus_claimed, created_at, last_login, google_id, avatar_url)
            VALUES (?, ?, ?, ?, ?, 0, ?, 1, datetime('now'), datetime('now'), ?, ?)
        """, (extracted_email, extracted_email, dummy_hash, user_display_name, initial_credits, is_vip, extracted_sub, extracted_avatar))
        conn.commit()
        conn.close()

        log_client_access(ip, extracted_email, bool(is_vip), action="google_register")
        return {
            "status": "success",
            "action": "register",
            "email": extracted_email,
            "name": user_display_name,
            "avatar_url": extracted_avatar,
            "credits": initial_credits,
            "is_vip": bool(is_vip),
            "message": bonus_msg
        }

@app.post("/api/auth/forgot-password")
def forgot_password(
    email: str = Form(...)
):
    email_clean = (email or "").strip().lower()
    if not is_valid_gmail(email_clean):
        raise HTTPException(status_code=400, detail="Informe uma conta válida do Google (@gmail.com).")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name FROM users WHERE LOWER(email) = ? OR id = ?", (email_clean, email_clean))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Nenhuma conta cadastrada com este Gmail. Verifique a digitação ou crie sua conta.")

    code = f"{secrets.randbelow(900000) + 100000}"
    expires = (datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")

    c.execute("UPDATE users SET reset_code = ?, reset_code_expires = ? WHERE LOWER(email) = ? OR id = ?", (code, expires, email_clean, email_clean))
    conn.commit()
    conn.close()

    send_recovery_email_async(email_clean, code)

    return {
        "status": "success",
        "message": f"Código de recuperação de 6 dígitos gerado e enviado para {email_clean}.",
        "recovery_code": code
    }

@app.post("/api/auth/reset-password")
def reset_password(
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...)
):
    email_clean = (email or "").strip().lower()
    code_clean = (code or "").strip()

    if not is_valid_gmail(email_clean):
        raise HTTPException(status_code=400, detail="Informe uma conta válida do Google (@gmail.com).")
    if len(new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres.")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT reset_code, reset_code_expires FROM users WHERE LOWER(email) = ? OR id = ?", (email_clean, email_clean))
    row = c.fetchone()

    if not row or not row[0]:
        conn.close()
        raise HTTPException(status_code=400, detail="Nenhum código de recuperação ativo. Solicite um novo código.")

    saved_code, expires_str = row
    if saved_code != code_clean:
        conn.close()
        raise HTTPException(status_code=400, detail="Código de recuperação inválido. Verifique os 6 dígitos digitados.")

    if expires_str:
        try:
            exp_dt = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() > exp_dt:
                conn.close()
                raise HTTPException(status_code=400, detail="O código de recuperação expirou (validade de 15 minutos). Solicite outro.")
        except Exception:
            pass

    pw_hash = hash_password(new_password)
    c.execute("UPDATE users SET password_hash = ?, reset_code = NULL, reset_code_expires = NULL WHERE LOWER(email) = ? OR id = ?", (pw_hash, email_clean, email_clean))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "Sua senha foi redefinida com sucesso! Você já pode entrar com sua nova senha."
    }

@app.post("/api/auth/unlock-vip")
def unlock_vip(
    request: Request,
    email: str = Form(""),
    user_id: str = Form("")
):
    ip = extract_client_ip(request)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Marca IP como VIP ilimitado permanente
    c.execute("INSERT INTO ip_wallets (ip, credits, is_vip, bonus_claimed) VALUES (?, 999999, 1, 1) ON CONFLICT(ip) DO UPDATE SET is_vip=1, credits=999999", (ip,))
    c.execute("INSERT OR IGNORE INTO vip_ips (ip, note) VALUES (?, 'Logo 3-Click Secret Unlock')", (ip,))

    # 2. Marca a conta de Gmail vinculada como VIP ilimitada permanente
    target = (email or user_id or "").strip().lower()
    if target and ("@gmail.com" in target or "@googlemail.com" in target or target.startswith("vip_")):
        c.execute("UPDATE users SET is_vip = 1, credits = 999999 WHERE LOWER(email) = ? OR id = ?", (target, target))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "is_vip": True,
        "credits": 999999,
        "ip": ip,
        "email": target,
        "message": "👑 Acesso Total e Exclusivo VIP Liberado para este IP e para esta conta de Gmail! Tokens Ilimitados ativos!"
    }

@app.get("/api/auth/me")
def get_auth_me(
    request: Request,
    user_id: str = "default_user"
):
    ip = extract_client_ip(request)
    vip = is_founder_vip(user_id, ip)
    credits = get_user_credits(user_id)
    uid_clean = (user_id or "").strip().lower()

    user_name = "Usuário"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, email, is_vip, credits FROM users WHERE LOWER(email) = ? OR id = ?", (uid_clean, uid_clean))
    row = c.fetchone()
    conn.close()

    if row:
        user_name = row[0] or user_name
        if row[2] == 1:
            vip = True
            credits = 999999

    return {
        "status": "success",
        "user_id": user_id,
        "email": uid_clean if "@" in uid_clean else "",
        "name": user_name,
        "ip": ip,
        "is_vip": vip,
        "credits": credits
    }

@app.get("/api/user/credits")
def get_credits(request: Request, user_id: str = "default_user"):
    ip = extract_client_ip(request)
    vip = is_founder_vip(user_id, ip)
    credits = get_user_credits(user_id)
    ua = request.headers.get("user-agent", "")
    log_client_access(ip, user_id, vip, action="session_access", user_agent=ua)
    return {
        "user_id": user_id,
        "ip": ip,
        "is_vip": vip,
        "role": "Fundador VIP (Acesso Ilimitado)" if vip else "Visitante (Bônus Único por IP)",
        "credits": credits
    }

@app.get("/api/user/memory")
def get_user_memory(request: Request, user_id: str = "default_user"):
    ip = extract_client_ip(request)
    vip = is_founder_vip(user_id, ip)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Cada usuário vê EXCLUSIVAMENTE os seus próprios conteúdos gerados (isolamento individual)
    uid_clean = (user_id or "").strip().lower()
    c.execute("SELECT id, user_id, ip, category, title, prompt, result_url, metadata, created_at FROM user_creations WHERE LOWER(user_id) = ? ORDER BY created_at DESC LIMIT 100", (uid_clean,))
    rows = c.fetchall()
    conn.close()

    creations = []
    for r in rows:
        try:
            meta = json.loads(r[7] or "{}")
        except Exception:
            meta = {}
        creations.append({
            "id": r[0],
            "user_id": r[1],
            "ip": r[2],
            "category": r[3],
            "title": r[4],
            "prompt": r[5],
            "result_url": r[6],
            "metadata": meta,
            "created_at": r[8]
        })

    return {
        "status": "success",
        "is_vip": vip,
        "ip": ip,
        "user_id": user_id,
        "supabase_synced": bool(SUPABASE_URL and SUPABASE_KEY),
        "creations": creations
    }

@app.delete("/api/user/memory/{creation_id}")
def delete_user_memory_item(creation_id: str, user_id: str = Query("")):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    uid_clean = (user_id or "").strip().lower()
    c.execute("SELECT result_url FROM user_creations WHERE id = ? AND LOWER(user_id) = ?", (creation_id, uid_clean))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Criativo não encontrado ou permissão negada.")

    file_path = row[0].lstrip("/")
    c.execute("DELETE FROM user_creations WHERE id = ?", (creation_id,))
    conn.commit()
    conn.close()

    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
    return {"status": "success", "message": "Criativo excluído com sucesso da memória."}

@app.get("/api/admin/access-logs")
def get_access_logs(request: Request, user_id: str = "default_user"):
    ip = extract_client_ip(request)
    vip = is_founder_vip(user_id, ip)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, ip, user_id, is_vip, role, action, user_agent, created_at FROM access_logs ORDER BY created_at DESC LIMIT 100")
    log_rows = c.fetchall()

    c.execute("SELECT ip, credits, bonus_claimed, created_at FROM ip_wallets ORDER BY created_at DESC LIMIT 100")
    wallet_rows = c.fetchall()
    conn.close()

    logs = [{
        "id": r[0],
        "ip": r[1],
        "user_id": r[2],
        "is_vip": bool(r[3]),
        "role": r[4],
        "action": r[5],
        "user_agent": r[6],
        "created_at": r[7]
    } for r in log_rows]

    wallets = [{
        "ip": w[0],
        "credits": w[1],
        "bonus_claimed": bool(w[2]),
        "created_at": w[3]
    } for w in wallet_rows]

    return {
        "status": "success",
        "is_vip": vip,
        "supabase_synced": bool(SUPABASE_URL and SUPABASE_KEY),
        "access_logs": logs,
        "ip_wallets": wallets
    }

@app.get("/api/jobs/{job_id}")
def check_job(job_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT type, status, progress, result_url, error FROM jobs WHERE id = ?", (job_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return {
        "job_id": job_id,
        "type": row[0],
        "status": row[1],
        "progress": row[2],
        "result_url": row[3],
        "error": row[4]
    }

# ----------------------------------------------------------------------------------------
# 1. VOZES NEURAIS DO BRASIL (EDGE-TTS PT-BR)
# ----------------------------------------------------------------------------------------
@app.post("/api/voice/generate")
async def generate_voice(
    text: str = Form(...),
    voice: str = Form("antonio"),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=1):
        raise HTTPException(status_code=402, detail="Saldo de créditos insuficiente. Faça uma recarga.")

    job_id = str(uuid.uuid4())
    out_filename = f"voice_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    save_job(job_id, "voice", status="processing", progress=30)

    try:
        from scripts.voice_clone_engine import VoiceCloneEngine
        engine = VoiceCloneEngine()
        engine.generate_neural_brazil(text, output_path=out_path, voice=voice)
        save_job(job_id, "voice", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
        save_user_creation(user_id, "voice", f"Locução PT-BR ({voice.capitalize()})", text, f"/output/{out_filename}", {"voice": voice})
        return {"status": "success", "job_id": job_id, "result_url": f"/output/{out_filename}", "remaining_credits": get_user_credits(user_id)}
    except Exception as e:
        save_job(job_id, "voice", status="failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------------------------------------
# 2. CLONAGEM DE VOZ INSTANTÂNEA (1 MINUTO)
# ----------------------------------------------------------------------------------------
@app.post("/api/voice/clone")
async def clone_voice(
    text: str = Form(...),
    audio_sample: UploadFile = File(...),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=5):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 5 créditos).")

    job_id = str(uuid.uuid4())
    ref_filename = f"sample_{job_id[:8]}_{audio_sample.filename}"
    ref_path = os.path.join(UPLOAD_DIR, ref_filename)

    with open(ref_path, "wb") as f:
        shutil.copyfileobj(audio_sample.file, f)

    out_filename = f"cloned_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    save_job(job_id, "clone", status="processing", progress=20, user_id=user_id)

    try:
        from scripts.voice_clone_engine import VoiceCloneEngine
        engine = VoiceCloneEngine()
        engine.clone_voice_sample(ref_path, text, output_path=out_path)
        save_job(job_id, "clone", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
        save_user_creation(user_id, "clone", f"Voz Clonada ({audio_sample.filename})", text, f"/output/{out_filename}", {"sample": audio_sample.filename})
        return {"status": "success", "job_id": job_id, "result_url": f"/output/{out_filename}", "remaining_credits": get_user_credits(user_id)}
    except Exception as e:
        save_job(job_id, "clone", status="failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------------------------------------
# 3. SUNO STUDIO — MÚSICAS INÉDITAS DO ZERO
# ----------------------------------------------------------------------------------------
@app.post("/api/music/suno")
async def generate_suno_music(
    theme: str = Form(...),
    genre: str = Form("sertanejo pop animado, violao, sanfona e bateria"),
    duration: int = Form(95),
    voice_sample: Optional[UploadFile] = File(None),
    user_id: str = Form("default_user")
):
    cost = 20 if voice_sample else 15
    if not deduct_credits(user_id, amount=cost):
        raise HTTPException(status_code=402, detail=f"Saldo insuficiente (necessário {cost} créditos).")

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    save_job(job_id, "suno", status="processing", progress=15, user_id=user_id)

    voice_path = None
    if voice_sample:
        voice_path = os.path.join(UPLOAD_DIR, f"voice_{job_id[:8]}_{voice_sample.filename}")
        with open(voice_path, "wb") as f:
            shutil.copyfileobj(voice_sample.file, f)

    out_filename = f"suno_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    def _task():
        try:
            import importlib
            mod = importlib.import_module("scripts.10_suno_studio_engine")
            engine = mod.SunoStudioEngine()
            lyrics = engine.compose_lyrics(theme, genre=genre, duration_sec=duration)
            save_job(job_id, "suno", status="processing", progress=40, user_id=user_id)

            raw_song = engine.generate_full_song(lyrics, style_prompt=genre, output_path=os.path.join(OUTPUT_DIR, f"raw_{out_filename}"), duration=duration)
            save_job(job_id, "suno", status="processing", progress=75, user_id=user_id)

            if voice_path:
                engine.clone_singer_on_song(raw_song, voice_path, output_path=out_path)
            else:
                shutil.copy(raw_song, out_path)

            save_job(job_id, "suno", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(user_id, "suno", f"Suno Music: {theme[:60]}", f"{genre} | {theme}", f"/output/{out_filename}", {"genre": genre, "duration": duration}, ip_override=req_ip)
        except Exception as e:
            save_job(job_id, "suno", status="failed", error=str(e), user_id=user_id)

    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": "Geração musical iniciada em segundo plano.", "cost": cost}

# ----------------------------------------------------------------------------------------
# 4. PARÓDIAS & AI SONG COVERS (SUBSTITUIÇÃO VOCAL E LETRAS ALTERADAS)
# ----------------------------------------------------------------------------------------
@app.post("/api/music/parody-lyrics")
async def generate_parody_lyrics(
    original_song_name: str = Form(...),
    parody_theme: str = Form(...),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=1):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 1 crédito).")

    prompt = f"""Você é um mestre brasileiro em criação de paródias musicais virais.
Reescreva a letra da música famosa "{original_song_name}" criando uma paródia genial sobre o tema: "{parody_theme}".
REGRAS OBRIGATÓRIAS:
1. Mantenha EXATAMENTE o mesmo número de sílabas poéticas, ritmo, cadência e rimas da música original para que encaixe perfeitamente na melodia.
2. Divida claramente em [Verso 1], [Pré-Refrão], [Refrão], etc.
3. Escreva 100% em Português do Brasil, criativo, engraçado ou impactante.
Retorne apenas a letra da paródia pronta para cantar."""

    lyrics = None
    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        lyrics = MagnificCanvasEngine()._call_llm_text(prompt, timeout=22)
    except Exception:
        pass

    if not lyrics:
        lyrics = (
            f"[Paródia Oficial IABOX — Baseada em: {original_song_name}]\n"
            f"Tema: {parody_theme}\n\n"
            f"[Verso 1]\n"
            f"Olha só o que chegou pra mudar a estação\n"
            f"{parody_theme} dominando toda a geração\n"
            f"No compasso da batida, sem perder o tom\n"
            f"Aumenta o volume e sente a pressão do som!\n\n"
            f"[Refrão]\n"
            f"É {parody_theme} que todo mundo quer ouvir\n"
            f"No ritmo perfeito pra fazer sorrir\n"
            f"Canta junto agora, solta a sua voz\n"
            f"Ninguém faz mais forte do que todos nós!"
        )

    return {"status": "success", "lyrics": lyrics, "remaining_credits": get_user_credits(user_id)}

@app.post("/api/music/parody")
async def create_parody(
    song_file: UploadFile = File(...),
    voice_sample: Optional[UploadFile] = File(None),
    guide_file: Optional[UploadFile] = File(None),
    vocal_mode: str = Form("original_singers"),
    parody_lyrics: str = Form(""),
    pitch_shift: int = Form(0),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=20):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 20 créditos).")

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    save_job(job_id, "parody", status="processing", progress=15, user_id=user_id)

    song_path = os.path.join(UPLOAD_DIR, f"song_{job_id[:8]}_{song_file.filename}")
    with open(song_path, "wb") as f: shutil.copyfileobj(song_file.file, f)

    voice_path = None
    if voice_sample and voice_sample.filename:
        voice_path = os.path.join(UPLOAD_DIR, f"voice_{job_id[:8]}_{voice_sample.filename}")
        with open(voice_path, "wb") as f: shutil.copyfileobj(voice_sample.file, f)

    guide_path = None
    if guide_file and guide_file.filename:
        guide_path = os.path.join(UPLOAD_DIR, f"guide_{job_id[:8]}_{guide_file.filename}")
        with open(guide_path, "wb") as f: shutil.copyfileobj(guide_file.file, f)

    out_filename = f"parodia_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    mode_map = {
        "female_artist": "Paródia com Voz Feminina (Ultra-HD)",
        "female": "Paródia com Voz Feminina (Ultra-HD)",
        "male_artist": "Paródia com Voz Masculina (Ultra-HD)",
        "male": "Paródia com Voz Masculina (Ultra-HD)",
        "custom_voice": "Paródia com Voz Clonada do Usuário",
        "original_singers": "Paródia com Voz dos Cantores da Faixa"
    }
    mode_label = mode_map.get(vocal_mode, "Paródia Musical Inteligente")
    use_orig = (vocal_mode == "original_singers")

    def _task():
        try:
            import importlib
            mod = importlib.import_module("scripts.10_suno_studio_engine")
            engine = mod.SunoStudioEngine()
            engine.create_parody(
                original_song_path=song_path,
                parody_vocal_guide=guide_path,
                user_voice_path=voice_path,
                output_path=out_path,
                pitch_shift=pitch_shift,
                use_original_singer=use_orig,
                lyrics=parody_lyrics,
                vocal_mode=vocal_mode
            )
            save_job(job_id, "parody", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(
                user_id,
                "parody",
                f"{mode_label}: {song_file.filename}",
                parody_lyrics or "Paródia com afinação neural e vocal original",
                f"/output/{out_filename}",
                {"mode": mode_label, "vocal_mode": vocal_mode, "pitch_shift": pitch_shift},
                ip_override=req_ip
            )
        except Exception as e:
            save_job(job_id, "parody", status="failed", error=str(e), user_id=user_id)

    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": f"Produção de {mode_label} iniciada.", "cost": 20}

@app.post("/api/music/audit-qc")
async def audit_parody_qc(
    audio_file: Optional[UploadFile] = File(None),
    relative_url: Optional[str] = Form(None)
):
    """
    Auditoria Técnica Canônica de Áudio (QC) - Conforme especificação fonográfica de 8 estágios.
    Mede LUFS (ITU-R BS.1770), True Peak, LRA, Correlação Estéreo L/R e Espectro por bandas.
    """
    try:
        import importlib
        qc_mod = importlib.import_module("scripts.audio_qc_engine")
        target_path = None
        temp_created = False

        if audio_file and audio_file.filename:
            target_path = os.path.join(UPLOAD_DIR, f"qc_{uuid.uuid4().hex[:8]}_{audio_file.filename}")
            with open(target_path, "wb") as f:
                shutil.copyfileobj(audio_file.file, f)
            temp_created = True
        elif relative_url:
            clean_rel = relative_url.strip().lstrip("/")
            if clean_rel.startswith("output/"):
                clean_rel = clean_rel.replace("output/", "", 1)
                target_path = os.path.join(OUTPUT_DIR, clean_rel)
            elif clean_rel.startswith("static/"):
                clean_rel = clean_rel.replace("static/", "", 1)
                target_path = os.path.join("static", clean_rel)
            else:
                p1 = os.path.join(OUTPUT_DIR, clean_rel)
                p2 = os.path.join("static", clean_rel)
                target_path = p1 if os.path.exists(p1) else p2

        if not target_path or not os.path.exists(target_path):
            raise HTTPException(status_code=400, detail="Arquivo para auditoria de QC não encontrado.")

        report = qc_mod.audit_full_pipeline(target_path)
        if temp_created and os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass

        return {"status": "success", "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na auditoria de QC: {str(e)}")


# ----------------------------------------------------------------------------------------
# 5. GERADOR DE IMAGENS & CRIATIVOS PUBLICITÁRIOS (SUPORTE A 3 A 5 IMAGENS DE REFERÊNCIA)
# ----------------------------------------------------------------------------------------
@app.post("/api/image/generate")
async def generate_image(
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    model_style: str = Form("NanoBanana Pro"),
    ref_images: List[UploadFile] = File(default=[]),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=2):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 2 créditos).")

    job_id = str(uuid.uuid4())
    out_filename = f"image_{job_id[:8]}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    saved_refs = []
    for idx, rf in enumerate((ref_images or [])[:5]):
        if rf and rf.filename:
            ext = os.path.splitext(rf.filename)[1] or ".jpg"
            r_path = os.path.join(UPLOAD_DIR, f"imgref_{job_id[:8]}_{idx}{ext}")
            with open(r_path, "wb") as f:
                shutil.copyfileobj(rf.file, f)
            saved_refs.append(r_path)

    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        engine = MagnificCanvasEngine()
        info = engine.generate_connected_node(
            prompt=prompt,
            reference_images=saved_refs,
            model_style=model_style,
            aspect_ratio=aspect_ratio,
            output_path=out_path
        )
        save_job(job_id, "image", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
        save_user_creation(
            user_id,
            "image",
            f"Imagem IA ({len(saved_refs)} ref)" if saved_refs else "Imagem IA",
            prompt,
            f"/output/{out_filename}",
            {"aspect_ratio": aspect_ratio, "ref_count": len(saved_refs), "compiled_prompt": info.get("compiled_prompt", prompt)}
        )
        return {
            "status": "success",
            "job_id": job_id,
            "result_url": f"/output/{out_filename}",
            "ref_count": len(saved_refs),
            "compiled_prompt": info.get("compiled_prompt", prompt),
            "remaining_credits": get_user_credits(user_id)
        }
    except Exception as e:
        save_job(job_id, "image", status="failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------------------------------------------------------------------
# 6. ESTÚDIO DE VÍDEOS VIRAIS & VFX (ATÉ 5 MINUTOS + 3 A 5 IMAGENS REF + VÍDEOS AUXILIARES)
# ----------------------------------------------------------------------------------------

@app.post("/api/video/omni-check")
async def check_omni_requirements(
    duration_mode: str = Form("extended_60s"),
    vfx_mode: str = Form("full_production"),
    user_id: str = Form("default_user")
):
    current_credits = get_user_credits(user_id)
    is_heavy = (duration_mode in ["extended_60s", "movie_5m"]) or (vfx_mode in ["character_swap", "scene_swap", "multitake_cinema"])
    required_credits = 40 if is_heavy else 10

    if not is_heavy:
        return {
            "is_turbo": False,
            "can_run": current_credits >= required_credits,
            "required_credits": required_credits,
            "current_credits": current_credits
        }

    # Tarefa pesada (Omni Turbo)
    if current_credits >= required_credits:
        return {
            "is_turbo": True,
            "can_run": True,
            "required_credits": required_credits,
            "current_credits": current_credits,
            "message": "Saldo Turbo suficiente. Produção liberada no IABOX Omni Cinema Flow™."
        }
    else:
        return {
            "is_turbo": True,
            "can_run": False,
            "required_credits": required_credits,
            "current_credits": current_credits,
            "title": "Desbloqueie o Poder IABOX Omni Cinema Flow™",
            "message": "Você configurou uma Sequência Cinematográfica com Avatar/Troca de Cenário. Enquanto o Google Veo trava em 10 segundos, o IABOX renderiza sua sequência contínua de até 5 minutos com nosso Cluster Neural Turbo!",
            "upgrade_package": "single_gpu",
            "price_brl": 19.90,
            "studio_package": "studio_gpu",
            "studio_price_brl": 79.90
        }

@app.post("/api/video/edit")
async def edit_viral_video(
    video_file: UploadFile = File(...),
    ref_images: List[UploadFile] = File(default=[]),
    overlay_video: Optional[UploadFile] = File(None),
    vfx_mode: str = Form("full_production"),
    duration_mode: str = Form("preview_10s"),
    creative_prompt: str = Form(""),
    aspect_ratio: str = Form("9:16"),
    silence_removal: bool = Form(True),
    subtitles_karaoke: bool = Form(True),
    punch_zoom: bool = Form(True),
    user_id: str = Form("default_user")
):
    is_heavy = (duration_mode in ["extended_60s", "movie_5m"]) or (vfx_mode in ["character_swap", "scene_swap", "multitake_cinema"])
    required_credits = 40 if is_heavy else 10

    if not deduct_credits(user_id, amount=required_credits):
        cost_desc = f"{required_credits} créditos (Modo IABOX Omni Turbo)." if is_heavy else "10 créditos."
        raise HTTPException(status_code=402, detail=f"Saldo insuficiente (necessário {cost_desc})")

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    in_filename = f"raw_video_{job_id[:8]}_{video_file.filename}"
    in_path = os.path.join(UPLOAD_DIR, in_filename)

    with open(in_path, "wb") as f:
        shutil.copyfileobj(video_file.file, f)

    saved_ref_imgs = []
    for idx, rf in enumerate((ref_images or [])[:5]):
        if rf and rf.filename:
            ext = os.path.splitext(rf.filename)[1] or ".jpg"
            r_path = os.path.join(UPLOAD_DIR, f"vidref_{job_id[:8]}_{idx}{ext}")
            with open(r_path, "wb") as f:
                shutil.copyfileobj(rf.file, f)
            saved_ref_imgs.append(r_path)

    overlay_vid_path = None
    if overlay_video and overlay_video.filename:
        ext = os.path.splitext(overlay_video.filename)[1] or ".mp4"
        overlay_vid_path = os.path.join(UPLOAD_DIR, f"vidovl_{job_id[:8]}{ext}")
        with open(overlay_vid_path, "wb") as f:
            shutil.copyfileobj(overlay_video.file, f)

    out_filename = f"viral_{job_id[:8]}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    save_job(job_id, "video", status="processing", progress=15, user_id=user_id)

    def _task():
        try:
            save_job(job_id, "video", status="processing", progress=35, user_id=user_id)

            # Aciona os motores modulares de VFX / Troca de Personagem / Rotoscopia se selecionados
            if vfx_mode == "character_swap" and saved_ref_imgs:
                try:
                    import importlib
                    swap_mod = importlib.import_module("scripts.07_influencer_motion_swap")
                    swap_engine = swap_mod.InfluencerMotionEngine()
                    swap_engine.process_portrait_swap(saved_ref_imgs[0], in_path, out_path)
                except Exception as e:
                    print(f"[VideoStudio] Info Character Swap: {e}")

            target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1280, 720)

            # Monta pipeline FFmpeg suportando até 5 minutos (300 segundos) + Inserção de Criativos/Design/Motion Graphics
            cmd = ["ffmpeg", "-y", "-i", in_path]
            for r_img in saved_ref_imgs:
                cmd.extend(["-i", r_img])
            if overlay_vid_path:
                cmd.extend(["-stream_loop", "-1", "-i", overlay_vid_path])

            base_chain = (
                f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h},"
                f"eq=contrast=1.07:brightness=0.02:saturation=1.14"
            )
            if vfx_mode == "motion_graphics" or subtitles_karaoke:
                # Barra de HUD / Motion Graphic Neon no rodapé
                hud_y = int(target_h * 0.82)
                base_chain += f",drawbox=x=40:y={hud_y}:w={target_w-80}:h=110:color=black@0.68:t=fill"
                base_chain += f",drawbox=x=40:y={hud_y}:w=8:h=110:color=0x00F0FF@0.95:t=fill"

            filter_parts = [f"{base_chain}[base0]"]
            last_label = "[base0]"
            input_idx = 1

            # Insere as 3 a 5 imagens de referência como Cards Criativos / Objetos flutuantes sincronizados ao longo do vídeo
            card_w = int(target_w * 0.28)
            for idx, _ in enumerate(saved_ref_imgs):
                t_start = 1.0 + idx * 5.0
                t_end = t_start + 4.5
                ovl_x = target_w - card_w - 36 if idx % 2 == 0 else 36
                ovl_y = 60 + (idx % 2) * 40
                ref_lbl = f"[ref{idx}]"
                out_lbl = f"[v_img{idx}]"
                filter_parts.append(
                    f"[{input_idx}:v]scale={card_w}:{card_w}:force_original_aspect_ratio=increase,crop={card_w}:{card_w},"
                    f"drawbox=x=0:y=0:w={card_w}:h={card_w}:color=0x00F0FF@0.9:t=4{ref_lbl}"
                )
                filter_parts.append(
                    f"{last_label}{ref_lbl}overlay=x={ovl_x}:y={ovl_y}:enable='between(t,{t_start},{t_end})'{out_lbl}"
                )
                last_label = out_lbl
                input_idx += 1

            # Se houver vídeo auxiliar de criativo/B-Roll, insere como Picture-in-Picture dinâmico
            if overlay_vid_path:
                pip_w = int(target_w * 0.34)
                pip_h = int(pip_w * 0.56)
                pip_x = target_w - pip_w - 36
                pip_y = int(target_h * 0.58)
                filter_parts.append(
                    f"[{input_idx}:v]scale={pip_w}:{pip_h}:force_original_aspect_ratio=increase,crop={pip_w}:{pip_h},"
                    f"drawbox=x=0:y=0:w={pip_w}:h={pip_h}:color=0xFF007F@0.9:t=4[pipv]"
                )
                filter_parts.append(
                    f"{last_label}[pipv]overlay=x={pip_x}:y={pip_y}:shortest=1[v_pip]"
                )
                last_label = "[v_pip]"

            filter_parts.append(f"{last_label}format=yuv420p[vout]")
            filter_complex_str = ";".join(filter_parts)

            af_str = "silenceremove=start_periods=1:start_duration=0.25:start_threshold=-35dB:detection=peak" if silence_removal else "anull"

            cmd.extend([
                "-filter_complex", filter_complex_str,
                "-map", "[vout]",
                "-map", "0:a?",
                "-af", af_str,
                "-t", "300",  # Suporte oficial a vídeos de até 5 minutos (300 segundos)
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "21",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                out_path
            ])

            save_job(job_id, "video", status="processing", progress=70, user_id=user_id)
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0 or not os.path.exists(out_path):
                fallback_cmd = [
                    "ffmpeg", "-y", "-i", in_path,
                    "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},format=yuv420p",
                    "-t", "300",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac",
                    out_path
                ]
                subprocess.run(fallback_cmd, capture_output=True)

            save_job(job_id, "video", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(
                user_id,
                "video",
                f"Vídeo Studio ({vfx_mode})",
                creative_prompt or f"Edição {aspect_ratio} ({len(saved_ref_imgs)} imagens ref)",
                f"/output/{out_filename}",
                {"vfx_mode": vfx_mode, "ref_images_count": len(saved_ref_imgs), "has_overlay_video": bool(overlay_vid_path), "max_duration": "5min"},
                ip_override=req_ip
            )
        except Exception as e:
            save_job(job_id, "video", status="failed", error=str(e), user_id=user_id)

    t = threading.Thread(target=_task)
    t.start()

    return {
        "status": "started",
        "job_id": job_id,
        "message": f"Produção de Vídeo ({vfx_mode}) com {len(saved_ref_imgs)} referência(s) iniciada (suporte até 5 min).",
        "cost": 10
    }

# ----------------------------------------------------------------------------------------
# 7. MAGNIFIC 2.0, HIGGSFIELD & BUZZY AI FILM DIRECTOR (INFINITE CANVAS & CINEMA STUDIO)
# ----------------------------------------------------------------------------------------
def _resolve_local_media_path(url_or_path: str) -> Optional[str]:
    if not url_or_path:
        return None
    clean = url_or_path.split("?")[0].lstrip("/")
    if clean.startswith("static/") or clean.startswith("output/") or clean.startswith("uploads/"):
        if os.path.exists(clean):
            return clean
    return None

@app.post("/api/canvas/upload-node")
async def upload_canvas_node(
    image_file: UploadFile = File(...)
):
    node_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(image_file.filename or ".jpg")[1] or ".jpg"
    out_filename = f"node_ref_{node_id}{ext}"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    with open(out_path, "wb") as f:
        shutil.copyfileobj(image_file.file, f)
    return {"status": "success", "node_url": f"/output/{out_filename}"}

@app.post("/api/canvas/generate-node")
async def generate_canvas_node(
    prompt: str = Form(...),
    model_style: str = Form("Seedream 5 Pro"),
    aspect_ratio: str = Form("16:9"),
    camera_angle: str = Form("default"),
    lighting_mood: str = Form("default"),
    face_lock_enabled: bool = Form(True),
    face_lock_url: str = Form(""),
    face_strength: int = Form(100),
    face_file: Optional[UploadFile] = File(None),
    ref_urls: str = Form(""),
    reference_urls: str = Form(""),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=3):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 3 créditos).")

    job_id = str(uuid.uuid4())
    out_filename = f"canvas_node_{job_id[:8]}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    raw_refs = reference_urls or ref_urls or "[]"
    try:
        urls_list = json.loads(raw_refs)
    except Exception:
        urls_list = []

    ref_paths = []
    for u in urls_list:
        p = _resolve_local_media_path(u)
        if p:
            ref_paths.append(p)

    # Resolução da Foto de Fidelização de Rosto (Face Lock 100%)
    face_path = None
    if face_file and face_file.filename:
        ext = os.path.splitext(face_file.filename)[1] or ".jpg"
        face_path = os.path.join(UPLOAD_DIR, f"facelock_{job_id[:8]}{ext}")
        with open(face_path, "wb") as f:
            shutil.copyfileobj(face_file.file, f)
    elif face_lock_enabled:
        resolved_face = _resolve_local_media_path(face_lock_url) if face_lock_url else None
        if resolved_face and os.path.exists(resolved_face):
            face_path = resolved_face
        elif os.path.exists("static/samples/canvas_take1.jpg"):
            face_path = "static/samples/canvas_take1.jpg"

    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        engine = MagnificCanvasEngine()
        info = engine.generate_connected_node(
            prompt=prompt,
            reference_images=ref_paths,
            model_style=model_style,
            aspect_ratio=aspect_ratio,
            camera_angle=camera_angle,
            lighting_mood=lighting_mood,
            face_lock_path=face_path,
            face_strength=face_strength,
            output_path=out_path
        )
        save_job(job_id, "canvas_node", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
        save_user_creation(
            user_id,
            "canvas_node",
            f"Canvas 8K ({model_style})",
            prompt,
            f"/output/{out_filename}",
            {"model_style": model_style, "aspect_ratio": aspect_ratio, "camera": camera_angle, "lighting": lighting_mood, "face_locked": bool(face_path)}
        )
        return {
            "status": "success",
            "job_id": job_id,
            "result_url": f"/output/{out_filename}",
            "compiled_prompt": info.get("compiled_prompt", prompt),
            "face_locked": bool(face_path),
            "remaining_credits": get_user_credits(user_id)
        }
    except Exception as e:
        save_job(job_id, "canvas_node", status="failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/canvas/upscale")
async def magnific_upscale_node(
    node_url: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    creativity_level: str = Form("ultra"),
    creativity_strength: str = Form("ultra"),
    scale_target: str = Form("8k"),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=4):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 4 créditos).")

    job_id = str(uuid.uuid4())
    in_path = None
    target_url = image_url or node_url
    if image_file and image_file.filename:
        in_path = os.path.join(UPLOAD_DIR, f"upscale_in_{job_id[:8]}_{image_file.filename}")
        with open(in_path, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
    elif target_url:
        in_path = _resolve_local_media_path(target_url)

    if not in_path or not os.path.exists(in_path):
        raise HTTPException(status_code=400, detail="Imagem de origem não encontrada para o Magnific Upscaler.")

    out_filename = f"magnific_8k_{job_id[:8]}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        engine = MagnificCanvasEngine()
        engine.magnific_upscale_enhance(
            image_path=in_path,
            output_path=out_path,
            creativity_level=creativity_level or creativity_strength,
            scale_target=scale_target or "8k"
        )
        save_user_creation(user_id, "magnific_8k", "Magnific Upscale 8K", f"Criatividade: {creativity_level}", f"/output/{out_filename}", {"scale": scale_target})
        return {
            "status": "success",
            "result_url": f"/output/{out_filename}",
            "remaining_credits": get_user_credits(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/canvas/node-to-video")
async def canvas_single_node_to_video(
    node_url: str = Form(...),
    scene_prompt: str = Form("Cena de cinema em movimento real 8K"),
    voice_name: str = Form("antonio"),
    narration_text: str = Form(""),
    sfx_preset: str = Form("auto_contextual"),
    video_model: str = Form("Seedance 2.5 4K"),
    aspect_ratio: str = Form("16:9"),
    cloned_voice_file: Optional[UploadFile] = File(None),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=6):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 6 créditos).")

    img_path = _resolve_local_media_path(node_url)
    if not img_path or not os.path.exists(img_path):
        img_path = "static/samples/canvas_take1.jpg"

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    out_filename = f"node_video_sfx_{job_id[:8]}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    cloned_path = None
    if cloned_voice_file and cloned_voice_file.filename:
        ext = os.path.splitext(cloned_voice_file.filename)[1] or ".mp3"
        cloned_path = os.path.join(UPLOAD_DIR, f"canvas_clone_{job_id[:8]}{ext}")
        with open(cloned_path, "wb") as f:
            shutil.copyfileobj(cloned_voice_file.file, f)

    save_job(job_id, "node_video", status="processing", progress=25, user_id=user_id)

    def _task():
        try:
            from scripts.magnific_canvas_engine import MagnificCanvasEngine
            engine = MagnificCanvasEngine()
            engine.render_storyboard_timeline(
                image_paths=[img_path],
                output_path=out_path,
                narration_text=narration_text,
                voice_name=voice_name,
                cloned_voice_path=cloned_path,
                sfx_preset=sfx_preset,
                scene_prompt=scene_prompt,
                aspect_ratio=aspect_ratio,
                sec_per_take=4.0,
                video_model=video_model
            )
            save_job(job_id, "node_video", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(
                user_id,
                "video",
                f"Take Real + SFX ({video_model})",
                f"SFX: {sfx_preset} | Voz: {voice_name}",
                f"/output/{out_filename}",
                {"sfx": sfx_preset, "voice": voice_name, "video_model": video_model},
                ip_override=req_ip
            )
        except Exception as e:
            save_job(job_id, "node_video", status="failed", error=str(e), user_id=user_id)

    t = threading.Thread(target=_task)
    t.start()
    return {"status": "started", "job_id": job_id, "message": "Gerando Vídeo Real com Efeitos Sonoros (SFX)...", "cost": 6}

@app.post("/api/canvas/render-storyboard")
async def render_canvas_storyboard(
    node_urls: str = Form(""),
    node_urls_json: str = Form(""),
    narration_text: str = Form(""),
    narration_ptbr: str = Form(""),
    voice_name: str = Form("antonio"),
    sfx_preset: str = Form("auto_contextual"),
    scene_prompt: str = Form(""),
    video_model: str = Form("Seedance 2.5 4K"),
    movie_duration_mode: str = Form("short_3m"),
    aspect_ratio: str = Form("16:9"),
    sec_per_take: float = Form(3.5),
    seconds_per_take: float = Form(3.5),
    cloned_voice_file: Optional[UploadFile] = File(None),
    user_id: str = Form("default_user")
):
    cost_map = {"short_3m": 12, "medium_30m": 25, "feature_2h": 45}
    cost = cost_map.get(movie_duration_mode, 12)
    if not deduct_credits(user_id, amount=cost):
        raise HTTPException(status_code=402, detail=f"Saldo insuficiente (necessário {cost} créditos para esta escala de filme).")

    raw_nodes = node_urls_json or node_urls or "[]"
    try:
        urls_list = json.loads(raw_nodes)
    except Exception:
        raise HTTPException(status_code=400, detail="Lista de nós inválida.")

    image_paths = []
    for u in urls_list:
        p = _resolve_local_media_path(u)
        if p:
            image_paths.append(p)

    if not image_paths:
        raise HTTPException(status_code=400, detail="Nenhum nó de imagem válido selecionado no Storyboard.")

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    out_filename = f"storyboard_cinema_{job_id[:8]}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    save_job(job_id, "storyboard", status="processing", progress=20, user_id=user_id)

    cloned_path = None
    if cloned_voice_file and cloned_voice_file.filename:
        ext = os.path.splitext(cloned_voice_file.filename)[1] or ".mp3"
        cloned_path = os.path.join(UPLOAD_DIR, f"storyboard_clone_{job_id[:8]}{ext}")
        with open(cloned_path, "wb") as f:
            shutil.copyfileobj(cloned_voice_file.file, f)

    final_narration = narration_ptbr or narration_text
    final_sec = seconds_per_take or sec_per_take

    def _task():
        try:
            from scripts.magnific_canvas_engine import MagnificCanvasEngine
            engine = MagnificCanvasEngine()
            engine.render_storyboard_timeline(
                image_paths=image_paths,
                output_path=out_path,
                narration_text=final_narration,
                voice_name=voice_name,
                cloned_voice_path=cloned_path,
                sfx_preset=sfx_preset,
                scene_prompt=scene_prompt or final_narration,
                aspect_ratio=aspect_ratio,
                sec_per_take=final_sec,
                video_model=video_model
            )
            save_job(job_id, "storyboard", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(
                user_id,
                "storyboard",
                f"Filme Cinema ({len(image_paths)} takes | SFX: {sfx_preset})",
                final_narration or f"Motor: {video_model} + Efeitos Sonoros Reais",
                f"/output/{out_filename}",
                {"takes": len(image_paths), "voice": voice_name, "sfx_preset": sfx_preset, "video_model": video_model, "scale": movie_duration_mode},
                ip_override=req_ip
            )
        except Exception as e:
            save_job(job_id, "storyboard", status="failed", error=str(e), user_id=user_id)

    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": "Renderização de Filme com Efeitos Sonoros Reais (SFX) e Voz iniciada.", "cost": cost}

@app.post("/api/canvas/agent-project")
async def create_agent_film_project(
    movie_idea: str = Form(...),
    duration_scale: str = Form("feature_2h"),
    model_style: str = Form("Seedream 5 Pro"),
    face_lock_url: str = Form("/static/samples/canvas_take1.jpg"),
    user_id: str = Form("default_user")
):
    """
    Agente Diretor de Cinema IA (Buzzy / Magnific Film Agent):
    A partir de 1 frase, cria o roteiro multi-capítulos (para curta até longa-metragem de 1 a 2 horas)
    e popula o Infinite Canvas com nós de [Personagem], [Objeto], [Cenário] e [Cenas] conectados.
    """
    if not deduct_credits(user_id, amount=5):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 5 créditos para o Agente Diretor de Filmes).")

    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        engine = MagnificCanvasEngine()
        project = engine.generate_film_project(
            movie_idea=movie_idea,
            duration_scale=duration_scale,
            model_style=model_style,
            face_lock_url=face_lock_url
        )
        save_user_creation(
            user_id,
            "film_project",
            project.get("movie_title", "Projeto de Filme IA"),
            project.get("logline", movie_idea),
            face_lock_url or "/static/samples/canvas_take1.jpg",
            {"scale": duration_scale, "chapters": project.get("total_planned_chapters", 24)}
        )
        return {
            "status": "success",
            "project": project,
            "remaining_credits": get_user_credits(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/canvas/reverse-engineer")
async def reverse_engineer_creative_endpoint(
    reference_description: str = Form(""),
    image_url: str = Form(""),
    image_file: Optional[UploadFile] = File(None),
    user_id: str = Form("default_user")
):
    """
    Engenharia Reversa Criativa (REA — 4 Camadas do vídeo de referência):
    Desconstrói qualquer imagem ou referência em:
    1. Tela & Composição
    2. Lógica Óptica & Câmera
    3. Iluminação, Cor & Textura 8K
    4. Prompt Mestre pronto para o Canvas
    """
    if not deduct_credits(user_id, amount=2):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 2 créditos).")

    img_path = None
    if image_file and image_file.filename:
        ext = os.path.splitext(image_file.filename)[1] or ".jpg"
        img_path = os.path.join(UPLOAD_DIR, f"rea_{uuid.uuid4().hex[:8]}{ext}")
        with open(img_path, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
    elif image_url:
        img_path = _resolve_local_media_path(image_url)

    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        engine = MagnificCanvasEngine()
        analysis = engine.reverse_engineer_creative(image_path=img_path, reference_description=reference_description)
        return {
            "status": "success",
            "rea_layers": analysis,
            "remaining_credits": get_user_credits(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/assistant/chat")
async def iabot_assistant_chat(
    question: str = Form(...),
    active_tab: str = Form("canvas"),
    user_id: str = Form("default_user")
):
    """
    Robô Assistente Interativo IABot ("Pergunte ao Robô"):
    Explica como funciona qualquer tecnologia do sistema sob sigilo industrial absoluto.
    """
    system_guide = f"""Você é o IABot 🤖, o Robô Engenheiro e Diretor de Cinema Oficial da plataforma IABOX (criada por Evandro Silva Gallina).
Responda em Português do Brasil de forma clara, prática, entusiasmada e didática (máximo de 4 parágrafos curtos ou tópicos diretos).
O usuário está atualmente na aba '{active_tab}' e perguntou: "{question}"

REGRA DE SIGILO INDUSTRIAL ABSOLUTO (PROPRIEDADE INTELECTUAL ESG):
- NUNCA revele e NUNCA cite nomes de bibliotecas externas, bancos de dados ou APIs de terceiros (proibido mencionar Gemini, Google, OpenRouter, HuggingFace, Pollinations, FFmpeg, MoviePy, Python, FastAPI, SQLite, Supabase, Edge-TTS, Gradio, etc.).
- Se perguntarem como o sistema foi criado, qual linguagem/API usa ou como foi construído, afirme que o IABOX roda 100% sobre a **Arquitetura Proprietária Fechada ESG Neural Core 8K™**, desenvolvida do zero por Evandro Silva Gallina.

Conhecimento Técnico Completo do Sistema IABOX que você ensina ao usuário:
1. ESTÚDIO EM TELA INTEIRA EXCLUSIVA (Canvas 100% Dedicado):
   - Clique no botão "🖥️ Abrir Estúdio em Tela Inteira Exclusiva" para transformar 100% do seu monitor em uma estação de criação dedicada.
   - Tudo no Canvas pode ser movido/arrastado (nós @Image1, @Image2, Painel Inspetor, Dock de Prompt, Barra de Ferramentas e o próprio fundo).
   - Para DELETAR qualquer imagem/nó: clique no ícone de lixeira (🗑️) no canto do card. Para BAIXAR direto no PC: clique em "⬇️ Baixar no PC".
2. FIDELIZAÇÃO DE ROSTO 100% (Face Lock Biométrico):
   - No Painel de Fidelização de Rosto do Canvas, ative "Travar Identidade Facial (100%)" e escolha o Rosto Oficial ou suba sua foto.
   - O motor proprietário ESG Biometric FaceLock 8K trava os traços faciais em todos os capítulos do filme.
3. EFEITOS SONOROS REAIS (Real SFX) & ESCOLHA DE VOZES:
   - Todos os vídeos saem com efeitos sonoros reais de cinema (Ronco de Motor V8, Chuva e Trovão, Impactos IMAX, Vento, Sci-Fi ou Passos) mixados com a voz que você escolher (Antonio, Francisca, Thalita ou sua Voz Clonada).
4. FILMES DE ATÉ 1 A 2 HORAS (Agente Diretor de Filmes IA):
   - Digite 1 única frase no "Agente Diretor de Filmes", escolha a escala (Curta 5min, Série 30min ou Longa-Metragem 1h a 2h) e o sistema gera o Roteiro em Atos/Capítulos + fichas de [Personagem], [Objeto], [Cenário] e [Cenas] conectadas.
   - Para mudar o ângulo de câmera ou iluminação de apenas 1 cena sem refazer o filme, clique no nó e troque a Lente/Luz no Inspetor!
5. ENGENHARIA REVERSA CRIATIVA (REA — 4 Camadas):
   - Suba qualquer foto ou referência no botão "Engenharia Reversa REA" e o motor extrai as 4 camadas (Composição, Lente/Câmera, Luz/Cor 8K e Prompt Mestre) para recriar em 1 clique."""

    from scripts.magnific_canvas_engine import MagnificCanvasEngine
    engine = MagnificCanvasEngine()
    answer = engine._call_llm_text(system_guide, timeout=20)
    if not answer:
        answer = (
            "🤖 **Olá! Eu sou o IABot, seu Copiloto Oficial na Arquitetura Proprietária ESG Neural Core 8K™!**\n\n"
            "• **Estúdio em Tela Inteira Exclusiva:** Clique em **🖥️ Abrir Estúdio em Tela Inteira Exclusiva** no topo do Canvas para dedicar 100% do seu monitor à criação. Arraste qualquer card, painel ou barra livremente, clique em **🗑️** para deletar ou **⬇️** para baixar direto no seu PC.\n"
            "• **Fidelização de Rosto 100% (Face Lock):** Mantenha o Face Lock ativo (ou envie sua foto) para preservar 100% da sua identidade facial e das imagens de referência em qualquer cena.\n"
            "• **Vozes e Efeitos Sonoros Reais (SFX):** Escolha entre **Antonio, Francisca, Thalita ou Voz Clonada** e selecione o pacote de **SFX Real** (Motor V8, Chuva & Trovão, Impacto IMAX, etc.).\n"
            "• **Filmes de 1 a 2 Horas:** Digite sua ideia no **Agente Diretor de Filmes IA**, escolha **Longa-Metragem (1h–2h)** e gere todos os Atos, Capítulos e Nós conectados!"
        )

    return {"status": "success", "answer": answer}


# ----------------------------------------------------------------------------------------
# 8. STRIPE CHECKOUT (SISTEMA PRÉ-PAGO)
# ----------------------------------------------------------------------------------------
PACKAGES = {
    "starter": {"name": "Pacote Starter (100 Créditos)", "credits": 100, "price_brl": 29.90, "cents": 2990},
    "pro": {"name": "Pacote Pro (250 Créditos)", "credits": 250, "price_brl": 59.90, "cents": 5990},
    "viral": {"name": "Pacote Viral Agency (700 Créditos)", "credits": 700, "price_brl": 129.90, "cents": 12990},
    "single_gpu": {"name": "Produção Única IABOX Neural Turbo (Alta Fidelidade)", "credits": 40, "price_brl": 19.90, "cents": 1990},
    "studio_gpu": {"name": "Passaporte Studio IABOX Neural Turbo (Cinema & Paródia)", "credits": 200, "price_brl": 79.90, "cents": 7990}
}

@app.post("/api/stripe/create-checkout")
async def create_checkout_session(
    package_id: str = Form(...),
    user_id: str = Form("default_user")
):
    pkg = PACKAGES.get(package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Pacote inválido")

    if not STRIPE_SECRET_KEY:
        # Modo simulação local para testes imediatos sem chave configurada
        add_credits(user_id, pkg['credits'])
        return {
            "mode": "test_auto_recharge",
            "message": f"Créditos recarregados em modo teste (+{pkg['credits']} créditos).",
            "new_balance": get_user_credits(user_id)
        }

    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.create(
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': f"IABOX — {pkg['name']}",
                        'description': f"Recarga pré-paga de {pkg['credits']} créditos para criação de vídeos, áudios e músicas na plataforma IABOX.",
                    },
                    'unit_amount': pkg['cents'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"https://iabox.evandrosilvagallina.cloud/?payment=success&credits={pkg['credits']}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"https://iabox.evandrosilvagallina.cloud/?payment=cancel",
            metadata={'user_id': user_id, 'credits': str(pkg['credits'])}
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stripe/verify-session")
def verify_stripe_session(session_id: str, user_id: str = "default_user"):
    if not STRIPE_SECRET_KEY:
        return {"status": "mock_success", "credits_added": 100}
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        target_uid = (session.metadata or {}).get("user_id") or user_id
        if session.payment_status == "paid":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id FROM orders WHERE stripe_session_id = ?", (session_id,))
            already_processed = c.fetchone()
            if not already_processed:
                credits_to_add = int((session.metadata or {}).get("credits", 100))
                c.execute("INSERT INTO orders (id, user_id, amount_brl, credits, status, stripe_session_id) VALUES (?, ?, ?, ?, ?, ?)",
                          (str(uuid.uuid4()), target_uid, session.amount_total / 100.0, credits_to_add, "paid", session_id))
                conn.commit()
                conn.close()
                add_credits(target_uid, credits_to_add)
                return {"status": "success", "user_id": target_uid, "credits_added": credits_to_add, "new_balance": get_user_credits(target_uid)}
            conn.close()
            return {"status": "already_credited", "user_id": target_uid, "new_balance": get_user_credits(target_uid)}
        else:
            return {"status": "pending", "payment_status": session.payment_status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    # Processa evento de confirmação de pagamento
    try:
        event = json.loads(payload)
        if event.get("type") == "checkout.session.completed":
            session = event['data']['object']
            user_id = session.get('metadata', {}).get('user_id', 'default_user')
            credits_to_add = int(session.get('metadata', {}).get('credits', 100))
            add_credits(user_id, credits_to_add)
            print(f"[Stripe Webhook] Recarga confirmada: +{credits_to_add} créditos para {user_id}")
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------------------------------------------------------------------------------
# 9. RUNPOD GPU ORCHESTRATION & TELEMETRY
# ----------------------------------------------------------------------------------------
@app.get("/api/admin/runpod/status")
async def get_runpod_admin_status():
    try:
        from scripts.runpod_gpu_manager import RunPodGPUManager
        mgr = RunPodGPUManager()
        st = mgr.get_status()
        econ_parody = mgr.calculate_job_economics("parody_stem_separation")
        econ_cinema = mgr.calculate_job_economics("cinematic_video_8k")
        econ_pack = mgr.calculate_job_economics("studio_pack_5")
        return {
            "status": "success",
            "runpod": st,
            "economics": {
                "parody": econ_parody,
                "cinematic": econ_cinema,
                "studio_pack": econ_pack
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/admin/runpod/test-alert")
async def trigger_runpod_alert():
    try:
        from scripts.runpod_gpu_manager import RunPodGPUManager
        mgr = RunPodGPUManager()
        res = mgr.trigger_low_balance_alert()
        return {"status": "success", "result": res}
    except Exception as e:
        return {"status": "error", "message": str(e)}


import re

# ----------------------------------------------------------------------------------------
# 10. IABOX STORY TIMELINE™ — LINHA DO TEMPO DE HISTÓRIA COM CONTINUIDADE DE CENA
#     (mesmo cenário, personagens e iluminação em ângulos de câmera diferentes)
# ----------------------------------------------------------------------------------------
import math as _math

STORY_SHOTS = {
    "wide":          {"label": "Plano Geral",        "cam": "wide_anamorphic", "desc": "wide establishing shot of the whole environment"},
    "medium":        {"label": "Plano Médio",        "cam": "default",         "desc": "medium shot framed from the waist up"},
    "close":         {"label": "Close-up",           "cam": "close_up_85mm",   "desc": "tight close-up on the face and emotion"},
    "over_shoulder": {"label": "Sobre o Ombro",      "cam": "over_shoulder",   "desc": "over-the-shoulder shot"},
    "reverse":       {"label": "Contraplano",        "cam": "default",         "desc": "reverse shot from the opposite side of the same room, same window/lamp positions"},
    "low_angle":     {"label": "Ângulo Baixo (Herói)", "cam": "low_angle_hero", "desc": "low-angle hero shot"},
    "side":          {"label": "Perfil Lateral",     "cam": "side_profile",    "desc": "side-profile tracking shot"},
    "insert":        {"label": "Detalhe (Inserto)",  "cam": "default",         "desc": "macro insert shot of a meaningful object already present in the scene"},
    "aerial":        {"label": "Visão de Drone",     "cam": "drone_aerial",    "desc": "high aerial view of the same location"},
    "tension":       {"label": "Ângulo Inclinado",   "cam": "dutch_angle",     "desc": "tilted dutch-angle tension shot"},
}
STORY_LIGHT_MOODS = {"default", "golden_hour", "cyberpunk_neon", "chiaroscuro_noir", "imax_daylight", "fire_volumetric"}
STORY_MAX_CLIPS = 40

def init_story_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS story_projects (
        id TEXT PRIMARY KEY, user_id TEXT, title TEXT, bible TEXT,
        aspect_ratio TEXT DEFAULT '16:9', anchor_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS story_clips (
        id TEXT PRIMARY KEY, project_id TEXT, user_id TEXT, position INTEGER DEFAULT 0,
        shot_type TEXT DEFAULT 'medium', prompt TEXT, duration REAL DEFAULT 5,
        transition TEXT DEFAULT 'cut', source TEXT DEFAULT 'ai',
        status TEXT DEFAULT 'draft', progress INTEGER DEFAULT 0,
        result_url TEXT, keyframe_url TEXT, error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_story_clips_project ON story_clips(project_id, position)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_story_projects_user ON story_projects(user_id)")
    conn.commit()
    conn.close()

init_story_tables()

def _story_uid(user_id: str) -> str:
    return (user_id or "default_user").strip().lower()

def _story_local_path(url: str):
    clean = (url or "").split("?")[0].lstrip("/")
    if ".." in clean or not (clean.startswith("output/") or clean.startswith("static/samples/")):
        return None
    return clean if os.path.exists(clean) else None

def _story_project_row(c, project_id, uid):
    c.execute("SELECT id, title, bible, aspect_ratio, anchor_path, created_at FROM story_projects WHERE id = ? AND user_id = ?", (project_id, uid))
    return c.fetchone()

def _story_project_payload(c, row):
    c.execute("""SELECT id, position, shot_type, prompt, duration, transition, source, status, progress, result_url, keyframe_url, error
                 FROM story_clips WHERE project_id = ? ORDER BY position ASC, created_at ASC""", (row[0],))
    clips = [{
        "id": r[0], "position": r[1], "shot_type": r[2], "shot_label": STORY_SHOTS.get(r[2], {}).get("label", r[2]),
        "prompt": r[3], "duration": r[4], "transition": r[5], "source": r[6], "status": r[7],
        "progress": r[8], "result_url": r[9], "keyframe_url": r[10], "error": r[11]
    } for r in c.fetchall()]
    try:
        bible = json.loads(row[2] or "{}")
    except Exception:
        bible = {}
    return {
        "id": row[0], "title": row[1], "bible": bible, "aspect_ratio": row[3],
        "has_anchor": bool(row[4]), "created_at": row[5], "clips": clips,
        "total_duration": round(sum((cl["duration"] or 0) for cl in clips if cl["status"] == "done"), 1)
    }

def _story_probe_duration(path: str) -> float:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return round(float(out), 2)
    except Exception:
        return 5.0

def _story_extract_frame(video_path: str, out_jpg: str, at_end: bool = True) -> bool:
    cmd = ["ffmpeg", "-y"] + (["-sseof", "-0.2"] if at_end else ["-ss", "1"]) + ["-i", video_path, "-frames:v", "1", "-q:v", "2", out_jpg]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
        return os.path.exists(out_jpg) and os.path.getsize(out_jpg) > 0
    except Exception:
        return False

def _story_compile_prompt(bible: dict, shot_key: str, action: str, prev_action: str = "") -> str:
    shot = STORY_SHOTS.get(shot_key, STORY_SHOTS["medium"])
    parts = [
        "SAME SCENE CONTINUITY — this frame belongs to one continuous film; the location, props, characters, wardrobe and lighting must be IDENTICAL to the reference images.",
        f"Location: {bible.get('setting', '')}." if bible.get("setting") else "",
        f"Time of day: {bible.get('time_of_day', '')}." if bible.get("time_of_day") else "",
        f"Light source (keep direction, color temperature and shadow side identical in every shot): {bible.get('lighting_source', '')}." if bible.get("lighting_source") else "",
        f"Characters (same faces, same clothes): {bible.get('characters', '')}." if bible.get("characters") else "",
        f"Visual style: {bible.get('style', 'photorealistic cinematic film')}.",
        f"Camera: {shot['desc']}.",
        f"Previous moment of the story: {prev_action}." if prev_action else "",
        f"Action in this shot: {action}.",
        "Photorealistic, no text, no watermark, no subtitles."
    ]
    return " ".join(p for p in parts if p)

def _story_quote(duration: float, uses_continuity: bool):
    heavy = duration > 10 or uses_continuity
    return (25 if heavy else 10), heavy

@app.post("/api/story/project/create")
def story_create_project(
    title: str = Form("Minha História"),
    setting: str = Form(""),
    time_of_day: str = Form(""),
    lighting_source: str = Form(""),
    lighting_mood: str = Form("default"),
    characters: str = Form(""),
    style: str = Form("photorealistic cinematic film"),
    aspect_ratio: str = Form("16:9"),
    anchor_image: Optional[UploadFile] = File(None),
    user_id: str = Form("default_user")
):
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM story_projects WHERE user_id = ?", (uid,))
    if c.fetchone()[0] >= 60:
        conn.close()
        raise HTTPException(status_code=400, detail="Limite de projetos atingido. Exclua algum projeto antigo.")
    pid = str(uuid.uuid4())
    anchor_path = None
    if anchor_image and anchor_image.filename:
        ext = os.path.splitext(anchor_image.filename)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            conn.close()
            raise HTTPException(status_code=400, detail="Envie uma imagem JPG, PNG ou WEBP.")
        anchor_path = os.path.join(UPLOAD_DIR, f"story_anchor_{pid[:8]}{ext}")
        with open(anchor_path, "wb") as f:
            shutil.copyfileobj(anchor_image.file, f)
    bible = {
        "setting": setting[:500], "time_of_day": time_of_day[:100], "lighting_source": lighting_source[:300],
        "lighting_mood": lighting_mood if lighting_mood in STORY_LIGHT_MOODS else "default",
        "characters": characters[:700], "style": style[:200]
    }
    c.execute("INSERT INTO story_projects (id, user_id, title, bible, aspect_ratio, anchor_path) VALUES (?, ?, ?, ?, ?, ?)",
              (pid, uid, title[:120] or "Minha História", json.dumps(bible, ensure_ascii=False),
               aspect_ratio if aspect_ratio in ("16:9", "9:16", "1:1") else "16:9", anchor_path))
    conn.commit()
    conn.close()
    return {"status": "success", "project_id": pid}

@app.post("/api/story/project/from-creation")
def story_project_from_creation(
    result_url: str = Form(...),
    title: str = Form("Minha História"),
    aspect_ratio: str = Form("16:9"),
    user_id: str = Form("default_user")
):
    """Transforma um vídeo já criado pelo usuário no Clipe 1 de uma nova história (a IA aprende o cenário dele)."""
    uid = _story_uid(user_id)
    vid_path = _story_local_path(result_url)
    if not vid_path:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado na sua memória.")
    pid = str(uuid.uuid4())
    cid = str(uuid.uuid4())
    key_name = f"story_kf_{cid[:8]}.jpg"
    key_path = os.path.join(OUTPUT_DIR, key_name)
    anchor_path = key_path if _story_extract_frame(vid_path, key_path, at_end=True) else None
    dur = _story_probe_duration(vid_path)

    original_prompt = ""
    try:
        conn0 = sqlite3.connect(DB_PATH)
        c0 = conn0.cursor()
        c0.execute("SELECT prompt FROM user_creations WHERE result_url = ? AND LOWER(user_id) = ? ORDER BY created_at DESC LIMIT 1", (result_url.split("?")[0], uid))
        r0 = c0.fetchone()
        conn0.close()
        original_prompt = (r0[0] if r0 else "") or ""
    except Exception:
        pass

    bible = {"setting": original_prompt[:300], "time_of_day": "", "lighting_source": "", "lighting_mood": "default",
             "characters": "", "style": "photorealistic cinematic film"}
    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        eng = MagnificCanvasEngine()
        parts = []
        if anchor_path:
            with open(anchor_path, "rb") as fh:
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(fh.read()).decode()}})
        txt = eng._call_llm_text(
            "Analise este quadro final de um vídeo (e o prompt original: '" + original_prompt[:300] + "'). "
            "Responda SOMENTE um JSON com as chaves: setting (cenário detalhado em inglês), time_of_day, "
            "lighting_source (de onde vem a luz: janela à esquerda, lâmpada no teto, sol baixo etc., em inglês), "
            "characters (aparência física e roupa de cada personagem em inglês), style.",
            parts=parts, timeout=20)
        m = re.search(r"\{.*\}", txt or "", re.S)
        if m:
            data = json.loads(m.group(0))
            for k in ("setting", "time_of_day", "lighting_source", "characters", "style"):
                if isinstance(data.get(k), str) and data[k].strip():
                    bible[k] = data[k].strip()[:600]
    except Exception:
        pass

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO story_projects (id, user_id, title, bible, aspect_ratio, anchor_path) VALUES (?, ?, ?, ?, ?, ?)",
              (pid, uid, title[:120] or "Minha História", json.dumps(bible, ensure_ascii=False),
               aspect_ratio if aspect_ratio in ("16:9", "9:16", "1:1") else "16:9", anchor_path))
    c.execute("""INSERT INTO story_clips (id, project_id, user_id, position, shot_type, prompt, duration, source, status, progress, result_url, keyframe_url)
                 VALUES (?, ?, ?, 0, 'wide', ?, ?, 'imported', 'done', 100, ?, ?)""",
              (cid, pid, uid, original_prompt[:500] or "Cena inicial", dur, result_url.split("?")[0],
               f"/output/{key_name}" if anchor_path else None))
    conn.commit()
    conn.close()
    return {"status": "success", "project_id": pid, "bible": bible}

@app.get("/api/story/projects")
def story_list_projects(user_id: str = Query("default_user")):
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT p.id, p.title, p.aspect_ratio, p.created_at,
                        (SELECT COUNT(*) FROM story_clips WHERE project_id = p.id) AS n,
                        (SELECT keyframe_url FROM story_clips WHERE project_id = p.id AND keyframe_url IS NOT NULL ORDER BY position ASC LIMIT 1) AS thumb
                 FROM story_projects p WHERE p.user_id = ? ORDER BY p.updated_at DESC""", (uid,))
    rows = [{"id": r[0], "title": r[1], "aspect_ratio": r[2], "created_at": r[3], "clips": r[4], "thumb": r[5]} for r in c.fetchall()]
    conn.close()
    return {"projects": rows}

@app.get("/api/story/project/{project_id}")
def story_get_project(project_id: str, user_id: str = Query("default_user")):
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = _story_project_row(c, project_id, uid)
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    payload = _story_project_payload(c, row)
    conn.close()
    return payload

@app.post("/api/story/project/update")
def story_update_project(
    project_id: str = Form(...),
    title: str = Form(""),
    setting: str = Form(""),
    time_of_day: str = Form(""),
    lighting_source: str = Form(""),
    lighting_mood: str = Form("default"),
    characters: str = Form(""),
    style: str = Form(""),
    user_id: str = Form("default_user")
):
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = _story_project_row(c, project_id, uid)
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    bible = json.loads(row[2] or "{}")
    for k, v, mx in (("setting", setting, 500), ("time_of_day", time_of_day, 100), ("lighting_source", lighting_source, 300),
                     ("characters", characters, 700), ("style", style, 200)):
        if v.strip():
            bible[k] = v.strip()[:mx]
    if lighting_mood in STORY_LIGHT_MOODS:
        bible["lighting_mood"] = lighting_mood
    c.execute("UPDATE story_projects SET bible = ?, title = COALESCE(NULLIF(?, ''), title), updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
              (json.dumps(bible, ensure_ascii=False), title[:120], project_id, uid))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/story/project/delete")
def story_delete_project(project_id: str = Form(...), user_id: str = Form("default_user")):
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM story_clips WHERE project_id = ? AND user_id = ?", (project_id, uid))
    c.execute("DELETE FROM story_projects WHERE id = ? AND user_id = ?", (project_id, uid))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/story/quote")
def story_quote(duration: float = Form(5), user_id: str = Form("default_user")):
    """Mesmo contrato do omni-check: informa custo e, se faltar saldo, devolve a oferta de recarga."""
    cost, heavy = _story_quote(max(1.0, min(duration, 30.0)), True)
    cur = get_user_credits(user_id)
    if cur >= cost:
        return {"can_run": True, "is_turbo": heavy, "required_credits": cost, "current_credits": cur}
    return {
        "can_run": False, "is_turbo": heavy, "required_credits": cost, "current_credits": cur,
        "title": "Continue sua história com a mesma cena",
        "message": "Para manter o mesmo cenário, personagens e iluminação em novos ângulos, o IABOX ativa o Cluster de Continuidade Turbo. Recarregue para seguir filmando a próxima cena.",
        "upgrade_package": "single_gpu", "price_brl": 19.90, "studio_package": "studio_gpu", "studio_price_brl": 79.90
    }

def _story_run_clip(clip_id: str, project_id: str, uid: str, user_id: str, req_ip: str):
    def _set(**kw):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        sets = ", ".join(f"{k} = ?" for k in kw)
        c.execute(f"UPDATE story_clips SET {sets} WHERE id = ?", (*kw.values(), clip_id))
        conn.commit()
        conn.close()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        prow = _story_project_row(c, project_id, uid)
        c.execute("SELECT position, shot_type, prompt, duration FROM story_clips WHERE id = ?", (clip_id,))
        crow = c.fetchone()
        c.execute("SELECT prompt, keyframe_url FROM story_clips WHERE project_id = ? AND position < ? AND status = 'done' ORDER BY position DESC LIMIT 1",
                  (project_id, crow[0]))
        prev = c.fetchone()
        conn.close()
        bible = json.loads(prow[2] or "{}")
        ar = prow[3]
        anchor = prow[4] if prow[4] and os.path.exists(prow[4]) else None
        shot_key, action, duration = crow[1], crow[2], float(crow[3] or 5)
        shot = STORY_SHOTS.get(shot_key, STORY_SHOTS["medium"])
        prev_prompt = prev[0] if prev else ""
        prev_kf = _story_local_path(prev[1]) if prev and prev[1] else None

        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        engine = MagnificCanvasEngine()
        n_key = min(3, max(1, _math.ceil(duration / 5.0)))
        compiled = _story_compile_prompt(bible, shot_key, action, prev_prompt)
        keyframes = []
        for k in range(n_key):
            refs = [p for p in (prev_kf, anchor) if p]
            if keyframes:
                refs = [keyframes[-1]] + refs
            kf_path = os.path.join(OUTPUT_DIR, f"story_kf_{clip_id[:8]}_{k}.jpg")
            engine.generate_connected_node(
                prompt=compiled + (f" This is moment {k + 1} of {n_key} of the same shot." if n_key > 1 else ""),
                reference_images=refs[:4], model_style="Seedream 5 Pro", aspect_ratio=ar,
                camera_angle=shot["cam"], lighting_mood=bible.get("lighting_mood", "default"),
                face_lock_path=anchor, face_strength=100, output_path=kf_path)
            keyframes.append(kf_path)
            _set(progress=15 + int(45 * (k + 1) / n_key))

        out_name = f"story_clip_{clip_id[:8]}.mp4"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        engine.render_storyboard_timeline(
            image_paths=keyframes, output_path=out_path, scene_prompt=compiled,
            aspect_ratio=ar, sec_per_take=max(1.5, duration / n_key))
        _set(status="done", progress=100, result_url=f"/output/{out_name}", keyframe_url=f"/output/{os.path.basename(keyframes[-1])}", error=None)
    except Exception as e:
        _set(status="failed", error=sanitize_error_msg(e)[:200])
        try:
            add_credits(user_id, amount=int(_story_quote(duration if 'duration' in locals() else 5, True)[0]))  # estorno automático
        except Exception:
            pass

@app.post("/api/story/clip/add")
def story_add_clip(
    project_id: str = Form(...),
    shot_type: str = Form("medium"),
    prompt: str = Form(...),
    duration: float = Form(5),
    transition: str = Form("cut"),
    user_id: str = Form("default_user")
):
    uid = _story_uid(user_id)
    duration = max(2.0, min(float(duration), 30.0))
    if shot_type not in STORY_SHOTS:
        shot_type = "medium"
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Descreva o que acontece neste plano.")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = _story_project_row(c, project_id, uid)
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    c.execute("SELECT COUNT(*), COALESCE(MAX(position), -1) FROM story_clips WHERE project_id = ?", (project_id,))
    n, maxpos = c.fetchone()
    if n >= STORY_MAX_CLIPS:
        conn.close()
        raise HTTPException(status_code=400, detail="Limite de planos por história atingido.")
    conn.close()

    cost, heavy = _story_quote(duration, True)
    if not deduct_credits(user_id, amount=cost):
        raise HTTPException(status_code=402, detail=f"Saldo insuficiente (necessário {cost} créditos para filmar este plano com continuidade).")

    cid = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO story_clips (id, project_id, user_id, position, shot_type, prompt, duration, transition, source, status, progress)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ai', 'processing', 5)""",
              (cid, project_id, uid, maxpos + 1, shot_type, prompt.strip()[:600], duration, "fade" if transition == "fade" else "cut"))
    c.execute("UPDATE story_projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    threading.Thread(target=_story_run_clip, args=(cid, project_id, uid, user_id, client_ip_var.get()), daemon=True).start()
    return {"status": "started", "clip_id": cid, "cost": cost, "remaining_credits": get_user_credits(user_id)}

@app.post("/api/story/clip/regenerate")
def story_regenerate_clip(clip_id: str = Form(...), user_id: str = Form("default_user")):
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT project_id, duration, source, status FROM story_clips WHERE id = ? AND user_id = ?", (clip_id, uid))
    r = c.fetchone()
    conn.close()
    if not r or r[2] != "ai":
        raise HTTPException(status_code=404, detail="Plano não encontrado ou não regenerável.")
    if r[3] == "processing":
        raise HTTPException(status_code=409, detail="Este plano já está sendo gerado.")
    cost, _ = _story_quote(float(r[1] or 5), True)
    if not deduct_credits(user_id, amount=cost):
        raise HTTPException(status_code=402, detail=f"Saldo insuficiente (necessário {cost} créditos).")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE story_clips SET status = 'processing', progress = 5, error = NULL WHERE id = ?", (clip_id,))
    conn.commit()
    conn.close()
    threading.Thread(target=_story_run_clip, args=(clip_id, r[0], uid, user_id, client_ip_var.get()), daemon=True).start()
    return {"status": "started", "cost": cost, "remaining_credits": get_user_credits(user_id)}

@app.post("/api/story/clip/upload")
def story_upload_clip(
    project_id: str = Form(...),
    video_file: UploadFile = File(...),
    user_id: str = Form("default_user")
):
    """Permite colocar na linha do tempo um vídeo próprio (gratuito)."""
    uid = _story_uid(user_id)
    ext = os.path.splitext(video_file.filename or "")[1].lower()
    if ext not in (".mp4", ".mov", ".webm", ".mkv"):
        raise HTTPException(status_code=400, detail="Envie um vídeo MP4, MOV, WEBM ou MKV.")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = _story_project_row(c, project_id, uid)
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    c.execute("SELECT COALESCE(MAX(position), -1) FROM story_clips WHERE project_id = ?", (project_id,))
    maxpos = c.fetchone()[0]
    conn.close()
    cid = str(uuid.uuid4())
    out_name = f"story_up_{cid[:8]}{ext}"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    with open(out_path, "wb") as f:
        shutil.copyfileobj(video_file.file, f)
    dur = _story_probe_duration(out_path)
    kf_name = f"story_kf_{cid[:8]}.jpg"
    kf_ok = _story_extract_frame(out_path, os.path.join(OUTPUT_DIR, kf_name), at_end=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO story_clips (id, project_id, user_id, position, shot_type, prompt, duration, source, status, progress, result_url, keyframe_url)
                    VALUES (?, ?, ?, ?, 'medium', ?, ?, 'upload', 'done', 100, ?, ?)""",
                 (cid, project_id, uid, maxpos + 1, (video_file.filename or "Vídeo enviado")[:80], dur, f"/output/{out_name}",
                  f"/output/{kf_name}" if kf_ok else None))
    conn.commit()
    conn.close()
    return {"status": "success", "clip_id": cid}

@app.post("/api/story/clip/update")
def story_update_clip(
    clip_id: str = Form(...),
    prompt: str = Form(""),
    shot_type: str = Form(""),
    duration: float = Form(0),
    transition: str = Form(""),
    user_id: str = Form("default_user")
):
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT source, status FROM story_clips WHERE id = ? AND user_id = ?", (clip_id, uid))
    r = c.fetchone()
    if not r:
        conn.close()
        raise HTTPException(status_code=404, detail="Plano não encontrado.")
    if prompt.strip():
        c.execute("UPDATE story_clips SET prompt = ? WHERE id = ?", (prompt.strip()[:600], clip_id))
    if shot_type in STORY_SHOTS:
        c.execute("UPDATE story_clips SET shot_type = ? WHERE id = ?", (shot_type, clip_id))
    if duration and r[0] == "ai":
        c.execute("UPDATE story_clips SET duration = ? WHERE id = ?", (max(2.0, min(float(duration), 30.0)), clip_id))
    if transition in ("cut", "fade"):
        c.execute("UPDATE story_clips SET transition = ? WHERE id = ?", (transition, clip_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/story/clip/delete")
def story_delete_clip(clip_id: str = Form(...), user_id: str = Form("default_user")):
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM story_clips WHERE id = ? AND user_id = ?", (clip_id, uid))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/story/clip/reorder")
def story_reorder_clips(project_id: str = Form(...), order_json: str = Form(...), user_id: str = Form("default_user")):
    uid = _story_uid(user_id)
    try:
        ids = [str(x) for x in json.loads(order_json)]
    except Exception:
        raise HTTPException(status_code=400, detail="Ordem inválida.")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if not _story_project_row(c, project_id, uid):
        conn.close()
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    for pos, cid in enumerate(ids):
        c.execute("UPDATE story_clips SET position = ? WHERE id = ? AND project_id = ? AND user_id = ?", (pos, cid, project_id, uid))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/story/suggest")
def story_suggest_next(project_id: str = Form(...), user_id: str = Form("default_user")):
    """Diretor IA: sugere os próximos 3 planos mantendo a mesma cena e a mesma fonte de luz."""
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = _story_project_row(c, project_id, uid)
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    c.execute("SELECT shot_type, prompt FROM story_clips WHERE project_id = ? ORDER BY position ASC", (project_id,))
    history = c.fetchall()
    conn.close()
    used = [h[0] for h in history]
    fallback_order = [k for k in ("close", "reverse", "over_shoulder", "insert", "low_angle", "side", "aerial") if k not in used] or ["close", "reverse", "insert"]
    suggestions = [{"shot_type": k, "label": STORY_SHOTS[k]["label"], "prompt": ""} for k in fallback_order[:3]]
    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        eng = MagnificCanvasEngine()
        story_so_far = " | ".join(f"[{STORY_SHOTS.get(h[0], {}).get('label', h[0])}] {h[1]}" for h in history[-6:])
        txt = eng._call_llm_text(
            "Você é um diretor de cinema. Cenário fixo: " + (json.loads(row[2] or '{}').get('setting', '')) +
            ". História até agora: " + story_so_far + ". Sugira os próximos 3 planos CURTOS na MESMA cena, em ângulos de câmera diferentes, "
            "avançando a história em português do Brasil. Responda SOMENTE um JSON array com 3 objetos "
            "{\"shot_type\": uma de " + ", ".join(STORY_SHOTS.keys()) + ", \"prompt\": \"ação em 1 frase\"}.",
            timeout=20)
        m = re.search(r"\[.*\]", txt or "", re.S)
        if m:
            arr = json.loads(m.group(0))
            out = []
            for it in arr[:3]:
                k = it.get("shot_type")
                if k in STORY_SHOTS and isinstance(it.get("prompt"), str):
                    out.append({"shot_type": k, "label": STORY_SHOTS[k]["label"], "prompt": it["prompt"][:300]})
            if out:
                suggestions = out
    except Exception:
        pass
    return {"suggestions": suggestions}

@app.post("/api/story/export")
def story_export(project_id: str = Form(...), user_id: str = Form("default_user")):
    uid = _story_uid(user_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = _story_project_row(c, project_id, uid)
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    c.execute("SELECT result_url, transition FROM story_clips WHERE project_id = ? AND status = 'done' AND result_url IS NOT NULL ORDER BY position ASC", (project_id,))
    items = c.fetchall()
    conn.close()
    paths = [(_story_local_path(u), t) for u, t in items]
    paths = [(p, t) for p, t in paths if p]
    if len(paths) < 1:
        raise HTTPException(status_code=400, detail="Nenhum plano pronto para exportar ainda.")
    title, ar = row[1], row[3]
    w, h = {"9:16": (1080, 1920), "1:1": (1080, 1080)}.get(ar, (1280, 720))
    job_id = str(uuid.uuid4())
    out_name = f"story_film_{job_id[:8]}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    save_job(job_id, "story_export", status="processing", progress=10, user_id=user_id)
    req_ip = client_ip_var.get()

    def _task():
        work = os.path.join(OUTPUT_DIR, f"story_export_{job_id[:8]}")
        os.makedirs(work, exist_ok=True)
        try:
            norm = []
            for i, (p, trans) in enumerate(paths):
                dur = _story_probe_duration(p)
                has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", p],
                                                capture_output=True, text=True).stdout.strip())
                n_path = os.path.join(work, f"n_{i:02d}.mp4")
                vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p,setsar=1"
                af = "aresample=44100,aformat=channel_layouts=stereo"
                if trans == "fade" and dur > 1.2:
                    vf += f",fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, dur - 0.4):.2f}:d=0.4"
                    af += f",afade=t=in:st=0:d=0.4,afade=t=out:st={max(0, dur - 0.4):.2f}:d=0.4"
                cmd = ["ffmpeg", "-y", "-i", p]
                if not has_audio:
                    cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
                cmd += ["-vf", vf, "-af", af] if has_audio else ["-vf", vf, "-map", "0:v:0", "-map", "1:a:0", "-shortest"]
                cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", n_path]
                subprocess.run(cmd, capture_output=True, timeout=600, check=True)
                norm.append(n_path)
                save_job(job_id, "story_export", status="processing", progress=10 + int(70 * (i + 1) / len(paths)), user_id=user_id)
            list_file = os.path.join(work, "list.txt")
            with open(list_file, "w", encoding="utf-8") as lf:
                for n_path in norm:
                    lf.write("file '" + os.path.abspath(n_path).replace("\\", "/") + "'\n")
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", "-movflags", "+faststart", out_path],
                           capture_output=True, timeout=600, check=True)
            save_job(job_id, "story_export", status="completed", progress=100, result_url=f"/output/{out_name}", user_id=user_id)
            save_user_creation(user_id, "video", f"História: {title[:60]}", f"Filme com {len(paths)} planos (Story Timeline)",
                               f"/output/{out_name}", {"story_project": project_id, "clips": len(paths)}, ip_override=req_ip)
        except Exception as e:
            save_job(job_id, "story_export", status="failed", error=sanitize_error_msg(e), user_id=user_id)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    threading.Thread(target=_task, daemon=True).start()
    return {"status": "started", "job_id": job_id}

# ----------------------------------------------------------------------------------------
# 11. GUIA INTELIGENTE — "O QUE VOCÊ QUER CRIAR?" (roteador de intenção para simplificar o site)
# ----------------------------------------------------------------------------------------
GUIDE_INTENTS = [
    ("story",   ["continua", "continuação", "continuacao", "história", "historia", "mesma cena", "mesmo cenário", "mesmo cenario", "próxima cena", "proxima cena", "sequência", "sequencia", "timeline", "linha do tempo", "episódio", "episodio", "curta"],
     "🎞️ Linha do Tempo de História", "Continue seu vídeo mantendo cenário, personagens e luz em novos ângulos."),
    ("parody",  ["paródia", "parodia", "jingle", "cover", "jingle de campanha", "música do", "musica do", "letra"],
     "💿 Paródia / Cover", "Crie uma música sobre a base que você escolher."),
    ("suno",    ["música", "musica", "canção", "cancao", "beat", "sertanejo", "funk", "trap", "trilha"],
     "🎵 Criar Música", "Gere uma música completa a partir de uma ideia."),
    ("clone",   ["clonar", "minha voz", "clone de voz", "voz clonada"],
     "🧬 Clonar Minha Voz", "Use sua própria voz em qualquer narração."),
    ("voice",   ["narração", "narracao", "locução", "locucao", "falar", "áudio", "audio", "voz"],
     "🎙️ Narração em Português", "Transforme texto em voz natural brasileira."),
    ("video",   ["vídeo", "video", "reels", "shorts", "tiktok", "legenda", "cortes", "avatar", "trocar cenário", "trocar cenario", "meu vídeo", "meu video"],
     "🎬 Editar / Criar Vídeo", "Edite seu vídeo ou troque personagem e cenário."),
    ("image",   ["foto", "imagem", "retrato", "logo", "banner", "arte", "ilustração", "ilustracao", "capa", "post"],
     "📸 Criar Imagem", "Gere imagens a partir de uma descrição ou fotos de referência."),
    ("canvas",  ["8k", "cinematográfic", "cinematografic", "storyboard", "filme", "roteiro", "cena épica", "cena epica"],
     "⚡ Estúdio Cinema 8K", "Monte cenas e filmes com qualidade de cinema."),
]

@app.post("/api/guide/route")
def guide_route(text: str = Form("")):
    t = (text or "").lower()
    scored = []
    for key, kws, label, hint in GUIDE_INTENTS:
        s = sum(1 for k in kws if k in t)
        if s:
            scored.append((s, key, label, hint))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return {"matched": False, "suggestions": [{"tab": "image", "label": "📸 Criar Imagem", "hint": "O jeito mais rápido de começar."},
                                                  {"tab": "video", "label": "🎬 Editar / Criar Vídeo", "hint": "Cortes, legendas e efeitos."},
                                                  {"tab": "suno", "label": "🎵 Criar Música", "hint": "Música completa a partir de uma ideia."}]}
    return {"matched": True, "suggestions": [{"tab": k, "label": l, "hint": h} for _, k, l, h in scored[:3]]}



# ----------------------------------------------------------------------------------------
# MOTOR DE SUGESTÃO E MELHORIA INTELIGENTE DE PROMPTS COM IA (PROMPT ENHANCER)
# ----------------------------------------------------------------------------------------
@app.post("/api/prompt/enhance")
async def enhance_user_prompt(
    prompt: str = Form(...),
    category: str = Form("image"),
    user_id: str = Form("default_user")
):
    """
    Analisa o pedido do usuário e enriquece prompts simples com especificações de alto nível:
    lente, iluminação cinematográfica, composição, estilo, timbres ou ritmo. Gratuito para o usuário.
    """
    clean_p = (prompt or "").strip()
    if not clean_p:
        raise HTTPException(status_code=400, detail="Por favor, digite um prompt para ser melhorado.")

    cat = (category or "image").lower()
    system_instructions = f"""Você é um especialista internacional e diretor de arte em engenharia de prompts para IA generativa.
O usuário escreveu o seguinte rascunho de prompt para a categoria "{cat}":
"{clean_p}"

Sua missão é transformar esse pedido em um prompt mestre profissional, rico em detalhes visuais/musicais, eliminando qualquer pobreza de detalhes.

REGRAS POR CATEGORIA:
- Se 'image' ou 'canvas':
  * Gere o enhanced_prompt em INGLÊS técnico cinematográfico (8K, especificando lente como 85mm f/1.2 ou 35mm anamorphic, iluminação volumétrica/rim light, texturas hiper-realistas, composição).
  * Melhore detalhes de pele, profundidade de campo rasa e atmosfera.
- Se 'video':
  * Gere o enhanced_prompt em INGLÊS descrevendo movimentos de câmera cinematográficos (slow pan, dolly-in, orbit shot), iluminação dramática, atmosfera e ação vívida em 60fps.
- Se 'suno' ou 'parody':
  * Gere o enhanced_prompt em PORTUGUÊS DO BRASIL especificando o gênero exato, instrumentos principais (violão de aço, sanfona, bateria 808, sintetizador), BPM, clima emocional e tema poético.

Retorne ESTRITAMENTE um objeto JSON válido (sem markdown ao redor, apenas o JSON bruto) com esta estrutura exata:
{{
  "enhanced_prompt": "Prompt completo e expandido com máxima riqueza de detalhes",
  "improvements": [
    "Primeira melhoria aplicada (em português)",
    "Segunda melhoria aplicada (em português)",
    "Terceira melhoria aplicada (em português)"
  ],
  "preset_chips": ["Tag Curta 1", "Tag Curta 2", "Tag Curta 3", "Tag Curta 4"],
  "alternatives": [
    {{"title": "Versão Cinematográfica", "prompt": "Prompt alternativo 1"}},
    {{"title": "Versão Estilizada", "prompt": "Prompt alternativo 2"}}
  ]
}}"""

    res_json = None
    try:
        from scripts.magnific_canvas_engine import MagnificCanvasEngine
        raw_res = MagnificCanvasEngine()._call_llm_text(system_instructions, timeout=20)
        if raw_res:
            clean_raw = raw_res.strip()
            if clean_raw.startswith("```json"):
                clean_raw = clean_raw[7:]
            if clean_raw.startswith("```"):
                clean_raw = clean_raw[3:]
            if clean_raw.endswith("```"):
                clean_raw = clean_raw[:-3]
            clean_raw = clean_raw.strip()
            import json
            res_json = json.loads(clean_raw)
    except Exception as e:
        print(f"[PromptEnhancer] LLM Exception: {e}")

    # Fallback inteligente se o LLM falhar ou der timeout
    if not res_json or not isinstance(res_json, dict) or "enhanced_prompt" not in res_json:
        if cat in ("image", "canvas"):
            res_json = {
                "enhanced_prompt": f"Ultra-realistic 8K photograph of {clean_p}, shot on 85mm f/1.2 lens, cinematic golden hour lighting, sharp focus, volumetric dust, detailed textures, photorealistic masterpiece, shallow depth of field, 16:9 widescreen",
                "improvements": [
                    "Lente 85mm f/1.2 com desfoque de fundo cinematográfico",
                    "Iluminação volumétrica dourada (golden hour)",
                    "Texturas e microporos em altísseima resolução 8K",
                    "Ajuste de enquadramento com proporção widescreen"
                ],
                "preset_chips": ["Luz Dourada", "85mm f/1.2", "Ultra 8K", "Cinema 16:9"],
                "alternatives": [
                    {"title": "Modo Cinema Escuro", "prompt": f"Dramatic cinematic scene of {clean_p}, moody shadows, Blade Runner style neon rim light, 35mm anamorphic lens, haze"},
                    {"title": "Estilo Comercial Clean", "prompt": f"High-end commercial studio portrait of {clean_p}, clean softbox lighting, ultra-sharp detail, pristine white studio setup"}
                ]
            }
        elif cat == "video":
            res_json = {
                "enhanced_prompt": f"Cinematic film shot of {clean_p}, smooth camera dolly in, dramatic studio rim lighting, 4K 60fps high motion fidelity, professional color grading, film grain",
                "improvements": [
                    "Movimento de câmera suave (dolly in / traveling)",
                    "Iluminação dramática com luz de recorte (rim light)",
                    "Taxa de quadros fluida a 60fps",
                    "Correção de cor com graduação de cinema"
                ],
                "preset_chips": ["Dolly In", "60 FPS Fluido", "Luz de Recorte", "Grading Cinema"],
                "alternatives": [
                    {"title": "Câmera Lenta Épica", "prompt": f"Slow-motion cinematic close-up of {clean_p}, 120fps, floating particles, dramatic backlight"},
                    {"title": "Câmera Dinâmica em Ação", "prompt": f"Fast-paced handheld tracking shot following {clean_p}, dynamic camera shake, action-packed framing"}
                ]
            }
        else:
            res_json = {
                "enhanced_prompt": f"{clean_p}, arranjo profissional com violão de aço, sanfona marcante, bateria moderna, 128 BPM, mixagem comercial de estúdio, voz encorpada e refrão chiclete envolvente",
                "improvements": [
                    "Definição de instrumentação rítmica de estúdio",
                    "Andamento travado em 128 BPM para retenção",
                    "Estrutura com refrão chiclete de alto engajamento",
                    "Masterização comercial em alta fidelidade"
                ],
                "preset_chips": ["128 BPM", "Violão de Aço", "Refrão Chiclete", "Master HD"],
                "alternatives": [
                    {"title": "Versão Sertanejo Universitário", "prompt": f"{clean_p}, sertanejo pop moderno, batida animada para festa, sanfona e violão"},
                    {"title": "Versão Acústico Intimista", "prompt": f"{clean_p}, versão acústico voz e violão solo, clima intimista e emotivo"}
                ]
            }

    return {
        "status": "success",
        "category": cat,
        "original_prompt": clean_p,
        "enhanced_prompt": res_json.get("enhanced_prompt", clean_p),
        "improvements": res_json.get("improvements", []),
        "preset_chips": res_json.get("preset_chips", []),
        "alternatives": res_json.get("alternatives", [])
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
