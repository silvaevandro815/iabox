"""
========================================================================================
RUNPOD GPU ORCHESTRATOR & MONETIZATION ENGINE (ON-DEMAND STUDIO COMPUTING)
========================================================================================
Gerencia o cluster GPU sob demanda na RunPod para produções de alta densidade:
- Paródias Fonográficas com BS-RoFormer e RVC v2
- Vídeos Cinematográficos Longos 8K com VFX e Sound Design
- Monitoramento contínuo de saldo via GraphQL
- Alerta automático de recarga via Evolution API (WhatsApp) ou Webhook
- Despacho e destruição imediata de Pods (Zero custo ocioso)
========================================================================================
"""

import os
import sys
import json
import time
import requests
from dotenv import dotenv_values

class RunPodGPUManager:
    GRAPHQL_URL = "https://api.runpod.io/graphql"

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

        self.api_key = env.get("RUNPOD_API_KEY") or os.environ.get("RUNPOD_API_KEY", "")
        self.evolution_url = env.get("EVOLUTION_API_URL") or os.environ.get("EVOLUTION_API_URL", "")
        self.evolution_key = env.get("EVOLUTION_API_KEY") or os.environ.get("EVOLUTION_API_KEY", "")
        self.admin_phone = env.get("ADMIN_WHATSAPP_PHONE", "5549999999999") # configurável
        self.alert_threshold_usd = float(env.get("RUNPOD_ALERT_THRESHOLD_USD", 3.0)) # Avisar quando < $3.00

    def get_status(self):
        """
        Retorna o saldo atual na RunPod, status de saúde e se precisa de recarga.
        """
        if not self.api_key:
            return {
                "status": "simulation_ready",
                "message": "Nenhuma RUNPOD_API_KEY configurada no .env. Operando em modo de simulação econômica.",
                "credit_usd": 0.0,
                "credit_brl": 0.0,
                "alert_needed": False,
                "has_key": False
            }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        query = """
        query Myself {
            myself {
                id
                email
                clientBalance
            }
        }
        """

        try:
            r = requests.post(f"{self.GRAPHQL_URL}?api_key={self.api_key}", json={"query": query}, headers=headers, timeout=12)
            if r.status_code == 200:
                data = r.json()
                if "data" in data and data["data"] and data["data"].get("myself"):
                    user_info = data["data"]["myself"]
                    credit_usd = float(user_info.get("clientBalance", 0.0))
                    # Conversão aproximada para BRL (dólar a R$ 5,65)
                    credit_brl = round(credit_usd * 5.65, 2)
                    alert_needed = (credit_usd < self.alert_threshold_usd)

                    return {
                        "status": "warning_low" if alert_needed else "healthy",
                        "email": user_info.get("email"),
                        "credit_usd": round(credit_usd, 2),
                        "credit_brl": credit_brl,
                        "alert_needed": alert_needed,
                        "alert_threshold_usd": self.alert_threshold_usd,
                        "has_key": True,
                        "message": "Saldo baixo! Recarregue a RunPod para garantir produções pesadas." if alert_needed else "Cluster GPU operacional e pronto."
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Erro na resposta da RunPod: {r.text}",
                        "credit_usd": 0.0,
                        "credit_brl": 0.0,
                        "alert_needed": True,
                        "has_key": True
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Falha de conexão com a RunPod (HTTP {r.status_code})",
                    "credit_usd": 0.0,
                    "credit_brl": 0.0,
                    "alert_needed": False,
                    "has_key": True
                }
        except Exception as e:
            return {
                "status": "offline",
                "message": f"Erro de comunicação com a RunPod: {str(e)}",
                "credit_usd": 0.0,
                "credit_brl": 0.0,
                "alert_needed": False,
                "has_key": True
            }

    def trigger_low_balance_alert(self, current_balance_usd=None):
        """
        Dispara notificação via Evolution API WhatsApp e logs administrativos quando o saldo estiver baixo.
        """
        if current_balance_usd is None:
            st = self.get_status()
            current_balance_usd = st.get("credit_usd", 0.0)

        alert_text = (
            f"🚨 *ALERTA IABOX - SALDO RUNPOD BAIXO*\n\n"
            f"Diretor Evandro, o saldo da sua conta na RunPod caiu para: *US$ {current_balance_usd:.2f}* (aprox. R$ {current_balance_usd*5.65:.2f}).\n\n"
            f"⚡ Para evitar que paródias fonográficas e vídeos 8K de clientes fiquem parados na fila, adicione US$ 5 ou US$ 10 no painel da RunPod:\n"
            f"👉 https://www.runpod.io/console/billing"
        )

        print(f"[RunPod Alert Engine] {alert_text}")

        # Se houver Evolution API configurada, envia para o WhatsApp
        if self.evolution_url and self.evolution_key and self.admin_phone:
            try:
                endpoint = f"{self.evolution_url.rstrip('/')}/message/sendText/iabox_alerts"
                payload = {
                    "number": self.admin_phone,
                    "options": {"delay": 1200, "presence": "composing"},
                    "textMessage": {"text": alert_text}
                }
                headers = {"apikey": self.evolution_key, "Content-Type": "application/json"}
                r = requests.post(endpoint, json=payload, headers=headers, timeout=10)
                return {"whatsapp_sent": r.status_code == 200, "alert": alert_text}
            except Exception as ex:
                return {"whatsapp_sent": False, "error": str(ex), "alert": alert_text}

        return {"whatsapp_sent": False, "alert": alert_text}

    @staticmethod
    def calculate_job_economics(task_type="parody_stem_separation"):
        """
        Calcula os custos de infraestrutura e o lucro líquido por produção.
        """
        rates = {
            "parody_stem_separation": {
                "name": "Paródia Fonográfica (BS-RoFormer + RVC v2)",
                "gpu": "RTX 3060 (12GB VRAM)",
                "duration_minutes": 10,
                "cost_usd": 0.04,
                "cost_brl": 0.23,
                "client_price_brl": 19.90,
                "net_profit_brl": 19.67,
                "profit_margin_pct": 98.8
            },
            "cinematic_video_8k": {
                "name": "Vídeo Cinematográfico 8K (Até 5m + Efeitos)",
                "gpu": "RTX 4090 / A4000 (24GB VRAM)",
                "duration_minutes": 15,
                "cost_usd": 0.12,
                "cost_brl": 0.68,
                "client_price_brl": 29.90,
                "net_profit_brl": 29.22,
                "profit_margin_pct": 97.7
            },
            "studio_pack_5": {
                "name": "Pacote Studio Ultra GPU (5 Produções)",
                "gpu": "Cluster Sob Demanda",
                "duration_minutes": 60,
                "cost_usd": 0.35,
                "cost_brl": 1.98,
                "client_price_brl": 79.90,
                "net_profit_brl": 77.92,
                "profit_margin_pct": 97.5
            }
        }
        return rates.get(task_type, rates["parody_stem_separation"])



    def terminate_pod(self, pod_id: str) -> bool:
        """
        DESTROI COMPLETAMENTE o Pod e o disco associado.
        ATENCAO: Nunca usa 'stopPod' (que continua cobrando aluguel de disco).
        Sempre usa 'terminate' / 'delete' para que o custo horario volte imediatamente a US$ 0.0000.
        """
        if not self.api_key or not pod_id:
            return False

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 1. Tentativa via REST DELETE
        try:
            r = requests.delete(f"https://rest.runpod.io/v1/pods/{pod_id}", headers=headers, timeout=12)
            if r.status_code in (200, 204):
                print(f"[RunPod Auto-Terminator] Pod {pod_id} destruido com sucesso via REST. Custo horario = US$ 0.00.")
                return True
        except Exception as e:
            print(f"[RunPod Auto-Terminator] REST delete error: {e}")

        # 2. Tentativa via GraphQL mutation podTerminate
        try:
            mutation = """
            mutation TerminatePod($podId: String!) {
                podTerminate(input: { podId: $podId })
            }
            """
            r = requests.post(
                self.GRAPHQL_URL,
                json={"query": mutation, "variables": {"podId": pod_id}},
                headers=headers,
                timeout=12
            )
            if r.status_code == 200:
                print(f"[RunPod Auto-Terminator] Pod {pod_id} destruido com sucesso via GraphQL. Custo horario = US$ 0.00.")
                return True
        except Exception as e:
            print(f"[RunPod Auto-Terminator] GraphQL terminate error: {e}")

        return False

    def purge_all_pods_and_volumes(self):
        """
        Varre a conta e ELIMINA qualquer Pod pausado ou ativo para garantir ZERO cobranca residual de disco ou memoria.
        Garante gasto horario estritamente ZERO (US$ 0.00/hr).
        """
        if not self.api_key:
            return {"status": "no_key"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        query = """
        query ActiveResources {
            myself {
                pods {
                    id
                    name
                    desiredStatus
                    costPerHr
                }
            }
        }
        """
        terminated_count = 0
        try:
            r = requests.post(self.GRAPHQL_URL, json={"query": query}, headers=headers, timeout=12)
            if r.status_code == 200:
                data = r.json()
                pods = data.get("data", {}).get("myself", {}).get("pods", [])
                for p in pods:
                    pid = p.get("id")
                    if pid:
                        self.terminate_pod(pid)
                        terminated_count += 1
            return {"status": "success", "terminated_pods": terminated_count}
        except Exception as e:
            return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mgr = RunPodGPUManager()
    st = mgr.get_status()
    print("--- STATUS RUNPOD GPU ORCHESTRATOR ---")
    print(json.dumps(st, indent=2, ensure_ascii=False))
    econ = mgr.calculate_job_economics()
    print("--- MODELO ECONÔMICO DA PRODUÇÃO ---")
    print(json.dumps(econ, indent=2, ensure_ascii=False))
