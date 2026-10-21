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
    "evandro",
    "evandrogallina",
    "silvaevandro815@gmail.com",
    "evandrosilvagallina@gmail.com",
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
    for secret_term in ("ffmpeg", "gradio", "huggingface", "pollinations", "gemini", "supabase", "sqlite", "edge_tts", "traceback", "hf.space"):
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
        ("last_login", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]
    for col_name, col_type in user_cols:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass

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
    ip = extract_client_ip(request)
    vip = is_founder_vip(user_id, ip)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if vip:
        c.execute("SELECT id, user_id, ip, category, title, prompt, result_url, metadata, created_at FROM user_creations ORDER BY created_at DESC LIMIT 100")
    else:
        c.execute("SELECT id, user_id, ip, category, title, prompt, result_url, metadata, created_at FROM user_creations WHERE user_id = ? OR ip = ? ORDER BY created_at DESC LIMIT 60", (user_id, ip))
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
    voice_sample: UploadFile = File(...),
    guide_file: Optional[UploadFile] = File(None),
    pitch_shift: int = Form(0),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=20):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 20 créditos).")

    req_ip = client_ip_var.get()
    job_id = str(uuid.uuid4())
    save_job(job_id, "parody", status="processing", progress=15, user_id=user_id)

    song_path = os.path.join(UPLOAD_DIR, f"song_{job_id[:8]}_{song_file.filename}")
    voice_path = os.path.join(UPLOAD_DIR, f"voice_{job_id[:8]}_{voice_sample.filename}")
    with open(song_path, "wb") as f: shutil.copyfileobj(song_file.file, f)
    with open(voice_path, "wb") as f: shutil.copyfileobj(voice_sample.file, f)

    guide_path = None
    if guide_file and guide_file.filename:
        guide_path = os.path.join(UPLOAD_DIR, f"guide_{job_id[:8]}_{guide_file.filename}")
        with open(guide_path, "wb") as f: shutil.copyfileobj(guide_file.file, f)

    out_filename = f"parodia_{job_id[:8]}.mp3"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    mode_label = "Paródia Musical" if guide_path else "AI Song Cover"

    def _task():
        try:
            import importlib
            if guide_path:
                # Modo Paródia (Instrumental Original + Guia com Nova Letra + Voz Clonada)
                mod = importlib.import_module("scripts.10_suno_studio_engine")
                engine = mod.SunoStudioEngine()
                engine.create_parody(
                    original_song_path=song_path,
                    parody_vocal_guide=guide_path,
                    user_voice_path=voice_path,
                    output_path=out_path,
                    pitch_shift=pitch_shift
                )
            else:
                # Modo AI Song Cover Direto (Substitui o Cantor Original pela Voz Clonada mantendo Instrumental)
                mod = importlib.import_module("scripts.09_ai_song_cover_engine")
                engine = mod.AISongCoverEngine()
                engine.create_ai_song_cover(
                    song_path=song_path,
                    user_voice_path=voice_path,
                    output_song=out_path,
                    pitch_shift=pitch_shift
                )
            save_job(job_id, "parody", status="completed", progress=100, result_url=f"/output/{out_filename}", user_id=user_id)
            save_user_creation(user_id, "parody", f"{mode_label}: {song_file.filename}", f"Voz: {voice_sample.filename}", f"/output/{out_filename}", {"mode": mode_label, "pitch_shift": pitch_shift}, ip_override=req_ip)
        except Exception as e:
            save_job(job_id, "parody", status="failed", error=str(e), user_id=user_id)

    t = threading.Thread(target=_task)
    t.start()

    return {"status": "started", "job_id": job_id, "message": f"Produção de {mode_label} iniciada.", "cost": 20}

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
@app.post("/api/video/edit")
async def edit_viral_video(
    video_file: UploadFile = File(...),
    ref_images: List[UploadFile] = File(default=[]),
    overlay_video: Optional[UploadFile] = File(None),
    vfx_mode: str = Form("full_production"),
    creative_prompt: str = Form(""),
    aspect_ratio: str = Form("9:16"),
    silence_removal: bool = Form(True),
    subtitles_karaoke: bool = Form(True),
    punch_zoom: bool = Form(True),
    user_id: str = Form("default_user")
):
    if not deduct_credits(user_id, amount=10):
        raise HTTPException(status_code=402, detail="Saldo insuficiente (necessário 10 créditos).")

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
    "viral": {"name": "Pacote Viral Agency (700 Créditos)", "credits": 700, "price_brl": 129.90, "cents": 12990}
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
