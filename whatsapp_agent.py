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
    """Recebe eventos da Evolution API com tratamento robusto de erros."""
    try:
        body = await request.json()
    except Exception as e:
        print(f"Erro ao processar JSON do webhook: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    # A Evolution API pode enviar o evento na raiz ou dentro de um objeto
    event = body.get("event") if isinstance(body, dict) else None

    if event == "messages.upsert":
        data = body.get("data", {}) if isinstance(body, dict) else {}
        if not data:
            return {"status": "ignored", "message": "No data found in payload"}

        message = data.get("message", {})
        if not message:
            return {"status": "ignored", "message": "No message found in data"}

        # Tenta extrair o texto de diferentes campos comuns da Evolution API
        message_text = ""
        if isinstance(message, dict):
            message_text = message.get("conversation") or \
                           message.get("extendedTextMessage", {}).get("text", "") or \
                           message.get("text", "")

        remote_jid = data.get("remoteJid")

        if not remote_jid or not message_text:
            return {"status": "ignored", "message": "Missing remoteJid or text"}

        # Lógica de Menção: Responde se for chat privado ou se houver @ no texto do grupo
        is_group = remote_jid.endswith("@g.us")
        if not is_group or (is_group and "@" in message_text):
            print(f"Processando mensagem de {remote_jid}: {message_text}")
            background_tasks.add_task(process_request, message_text, remote_jid)

    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
