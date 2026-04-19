print("SISTEMA INICIANDO... Verificando config...")
import os
import sys
print(f"Caminho atual (CWD): {os.getcwd()}")
print(f"Caminhos de busca do Python (sys.path): {sys.path}")
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
import requests
from utmify_client import UTMifyClient
from dotenv import load_dotenv
from intention_parser import IntentionParser

load_dotenv()

load_dotenv()

app = FastAPI()

# Configurações Evolution API
EVOLUTION_URL = "https://evolutionapi-evolution-api.eaxyla.easypanel.host"
EVOLUTION_API_KEY = "8DE0548DAD46-45B4-8CFC-13D2359243E4"
INSTANCE_NAME = "robo"

# Cliente UTMify
utmify = UTMifyClient()
# Analisador de Intenções (Gemini)
parser = IntentionParser()

class EvolutionWebhook(BaseModel):
    event: str
    data: dict

def send_whatsapp_message(remote_jid: str, text: str):
    """Envia mensagem via Evolution API v2."""
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE_NAME}"
    payload = {
        "number": remote_jid,
        "text": text,
        "options": {"delay": 1200, "presence": "composing"}
    }
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def process_request(text: str, remote_jid: str):
    """Lógica inteligente de interpretação e resposta usando Gemini."""
    # 1. Usa o Gemini para entender o que o usuário quer
    intention = parser.parse(text)

    if not intention:
        response_text = "Desculpe, não consegui entender seu pedido. Tente algo como 'Gasto do Google ontem' ou 'Relatório Meta deste mês'."
        send_whatsapp_message(remote_jid, response_text)
        return

    platform = intention.get("platform")
    start_date = intention.get("start_date")
    end_date = intention.get("end_date")

    if not platform:
        response_text = "Você não especificou a plataforma. Deseja dados do *Google* ou *Meta*?"
        send_whatsapp_message(remote_jid, response_text)
        return

    # 2. Converte as datas do Gemini para o formato que a API da UTMify aceita
    # O Gemini retorna YYYY-MM-DD, precisamos de ISO UTC (ex: YYYY-MM-DDT03:00:00.000Z)
    date_range = {
        "from": f"{start_date}T03:00:00.000Z",
        "to": f"{end_date}T02:59:59.999Z"
    }

    # 3. Busca os dados
    results = utmify.fetch_metrics(platform, date_range=date_range)
    summary = utmify.calculate_summary(results)

    # 4. Monta a resposta
    period_desc = f"de {start_date} até {end_date}"
    response_text = (
        f"📊 *Relatório {platform.upper()}* ({period_desc})\n\n"
        f"💰 *Gasto:* R$ {summary['spend']:.2f}\n"
        f"✅ *Vendas:* {summary['sales']}\n"
        f"📈 *ROAS:* {summary['roas']:.2f}\n"
        f"🎯 *CAC:* R$ {summary['cac']:.2f}"
    )

    send_whatsapp_message(remote_jid, response_text)

@app.get("/test")
async def test():
    """Rota simples para verificar se o servidor está online."""
    return {"status": "Alive!", "message": "O servidor do agente está funcionando perfeitamente."}

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Recebe eventos da Evolution API com tratamento robusto de erros."""
    try:
        body = await request.json()
        print(f"WEBHOOK RECEIVED: {body}") # LOG DE DEBUG
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

        # Tenta extrair o texto de todas as formas possíveis (Evolution API v1 e v2)
        message_text = ""
        if isinstance(message, dict):
            # Tenta conversation (mensagens simples)
            if "conversation" in message:
                message_text = message["conversation"]
            # Tenta extendedTextMessage (mensagens com link, formatação ou menção)
            elif "extendedTextMessage" in message:
                message_text = message["extendedTextMessage"].get("text", "")
            # Tenta apenas o campo text
            elif "text" in message:
                message_text = message["text"]
            # Fallback: tenta procurar qualquer chave que contenha texto
            else:
                for key, value in message.items():
                    if key in ["text", "content", "body"] and isinstance(value, str):
                        message_text = value
                        break

        remote_jid = data.get("key", {}).get("remoteJid")

        if not remote_jid or not message_text:
            print(f"DEBUG: Mensagem ignorada. RemoteJid: {remote_jid}, Texto: {message_text}")
            return {"status": "ignored", "message": "Missing remoteJid or text"}

        # Lógica de Menção: DESATIVADA para testes
        # Respondemos a qualquer mensagem para validar o fluxo
        print(f"SISTEMA: Processando requisição de {remote_jid}: {message_text}")
        background_tasks.add_task(process_request, message_text, remote_jid)

    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
