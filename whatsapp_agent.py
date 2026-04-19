import os
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
import requests
from utmify_client import UTMifyClient
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configurações Evolution API
EVOLUTION_URL = "https://evolutionapi-evolution-api.eaxyla.easypanel.host"
EVOLUTION_API_KEY = "6F853DC40B80-4B5C-846A-3A2CF033A6E7"
INSTANCE_NAME = "Thiago"

# Cliente UTMify
utmify = UTMifyClient()

class EvolutionWebhook(BaseModel):
    event: str
    data: dict

def send_whatsapp_message(remote_jid: str, text: str):
    """Envia mensagem via Evolution API."""
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE_NAME}"
    payload = {
        "number": remote_jid,
        "options": {"delay": 1200, "presence": "composing"},
        "textMessage": {"text": text}
    }
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def process_request(text: str, remote_jid: str):
    """Lógica simplificada de interpretação e resposta."""
    text_lower = text.lower()

    platform = None
    if "google" in text_lower:
        platform = "google"
    elif "meta" in text_lower or "facebook" in text_lower:
        platform = "meta"

    if not platform:
        response_text = "Por favor, especifique se deseja dados do *Google* ou *Meta*."
    else:
        # Busca dados de ontem por padrão
        results = utmify.fetch_metrics(platform)
        summary = utmify.calculate_summary(results)

        response_text = (
            f"📊 *Relatório {platform.upper()} (Ontem)*\n\n"
            f"💰 *Gasto:* R$ {summary['spend']:.2f}\n"
            f"✅ *Vendas:* {summary['sales']}\n"
            f"📈 *ROAS:* {summary['roas']:.2f}\n"
            f"🎯 *CAC:* R$ {summary['cac']:.2f}"
        )

    send_whatsapp_message(remote_jid, response_text)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Recebe eventos da Evolution API."""
    body = await request.json()

    # Verificamos se é um evento de mensagem recebida
    if body.get("event") == "messages.upsert":
        data = body.get("data", {})
        message_text = data.get("message", {}).get("conversation", "") or \
                        data.get("message", {}).get("extendedTextMessage", {}).get("text", "")

        remote_jid = data.get("remoteJid")

        # Lógica de Menção: Responde apenas se for mencionado ou se for chat privado
        # No grupo, a menção vem no campo 'mentionedJid' ou no texto da mensagem
        is_group = remote_jid.endswith("@g.us")

        if not is_group or (is_group and "@" in message_text):
            background_tasks.add_task(process_request, message_text, remote_jid)

    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
