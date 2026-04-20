print("SISTEMA INICIANDO... Verificando config...")
import os
import sys
import json
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
import requests
from utmify_client import UTMifyClient
from dotenv import load_dotenv
from intention_parser import IntentionParser
import pytz
from datetime import datetime, timedelta

load_dotenv()

app = FastAPI()

# Configurações Evolution API
EVOLUTION_URL = "https://evolutionapi-evolution-api.eaxyla.easypanel.host"
EVOLUTION_API_KEY = "8DE0548DAD46-45B4-8CFC-13D2359243E4"
INSTANCE_NAME = "robo"

# Cliente UTMify e Parser
utmify = UTMifyClient()
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

def synthesize_response(text: str, platform: str, period_name: str, summary: dict):
    """Usa a IA para transformar dados brutos em uma resposta analítica e natural."""
    # Se for 'all', passamos o sumário como um dicionário de plataformas
    data_context = ""
    if platform == "all":
        for p, s in summary.items():
            data_context += f"\nPlataforma {p.upper()}:\n- Gasto Total: R$ {s['spend']:.2f}\n- Vendas Totais: {s['sales']}\n- ROAS: {s['roas']:.2f}\n- CAC: R$ {s['cac']:.2f}\n- Receita: R$ {s['revenue']:.2f}\n"
    else:
        data_context = f"- Gasto Total: R$ {summary['spend']:.2f}\n- Vendas Totais: {summary['sales']}\n- ROAS: {summary['roas']:.2f}\n- CAC: R$ {summary['cac']:.2f}\n- Receita: R$ {summary['revenue']:.2f}"

    prompt = f"""
    Você é um Analista de Performance de Marketing sênior.
    Sua tarefa é transformar dados brutos da UTMify em uma resposta natural e profissional para o WhatsApp.

    Pergunta do usuário: "{text}"
    Plataforma: {platform.upper()}
    Período: {period_name}
    Dados Brutos:
    {data_context}

    Instruções de Redação:
    1. Seja direto, mas profissional. Use emojis moderadamente.
    2. Se o usuário pediu 'insights', analise se o ROAS está bom ou se o CAC está alto.
    3. Se o gasto for 0, informe que não houve investimento no período.
    4. Não use termos técnicos excessivos, foque no resultado financeiro.
    5. Formate a resposta com negritos para destacar os números.
    6. Se for 'ALL', compare brevemente as duas plataformas.

    Exemplo de tom: "Olá! No Google, ontem tivemos um gasto de R$ 10,00 com 2 vendas, resultando em um ROAS de 5.0. O CAC está bem saudável!"
    """

    try:
        completion = parser.client.chat.completions.create(
            model=parser.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Erro ao sintetizar resposta: {e}")
        return f"📊 *Relatório {platform.upper()}* ({period_name})\n\nConsulte os dados no dashboard."

def process_request(text: str, remote_jid: str):
    """Lógica inteligente de interpretação e resposta usando Groq e Python para datas."""

    # 1. Usa o Groq para entender a intenção
    intention = parser.parse(text)

    if not intention:
        response_text = "Desculpe, não consegui entender seu pedido. Tente algo como 'Gasto do Google ontem' ou 'Relatório Meta deste mês'."
        send_whatsapp_message(remote_jid, response_text)
        return

    platform = intention.get("platform")
    period_type = intention.get("period_type")

    if not platform:
        response_text = "Você não especificou a plataforma. Deseja dados do *Google* ou *Meta*?"
        send_whatsapp_message(remote_jid, response_text)
        return

    # 2. CÁLCULO DE DATAS NO PYTHON (Sincronizado com São Paulo)
    tz = pytz.timezone('America/Sao_Paulo')
    now = datetime.now(tz)
    print(f"SISTEMA: Data Atual (SP): {now.strftime('%Y-%m-%d %H:%M:%S')}")

    if period_type == "hoje":
        start_date = now.strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        period_name = "Hoje"
    elif period_type == "ontem":
        yesterday = now - timedelta(days=1)
        start_date = yesterday.strftime("%Y-%m-%d")
        end_date = yesterday.strftime("%Y-%m-%d")
        period_name = "Ontem"
    elif period_type == "mes_atual":
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        period_name = "Mês Atual"
    elif period_type == "semana_passada":
        start_date_dt = now - timedelta(days=now.weekday() + 7)
        start_date = start_date_dt.strftime("%Y-%m-%d")
        end_date_dt = start_date_dt + timedelta(days=6)
        end_date = end_date_dt.strftime("%Y-%m-%d")
        period_name = "Semana Passada"
    elif period_type == "especifico":
        start_date = intention.get("start_date")
        end_date = intention.get("end_date")
        period_name = f"de {start_date} até {end_date}"
        if not start_date or not end_date:
            response_text = "Não consegui identificar as datas exatas. Pode repetir, por favor?"
            send_whatsapp_message(remote_jid, response_text)
            return
    else:
        yesterday = now - timedelta(days=1)
        start_date = yesterday.strftime("%Y-%m-%d")
        end_date = yesterday.strftime("%Y-%m-%d")
        period_name = "Ontem"

    # 3. Monta o date_range para a API da UTMify (Sincronizado com Brasília UTC-3)
    # Para pegar o dia exato no Brasil, precisamos deslocar 3 horas no UTC.
    # Ex: 2026-04-18 00:00 BRT = 2026-04-18 03:00:00 UTC
    # Ex: 2026-04-18 23:59 BRT = 2026-04-19 02:59:59 UTC

    # Calculamos a data de fim (se for ontem, o fim é no dia seguinte às 03h)
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    end_date_utc = end_date_dt.strftime("%Y-%m-%d")

    date_range = {
        "from": f"{start_date}T03:00:00.000Z",
        "to": f"{end_date_utc}T02:59:59.999Z"
    }

    # 4. Busca os dados
    print(f"SISTEMA: Chamando API UTMify para {platform} | Período: {date_range}")

    if platform == "all":
        all_summaries = {}
        for p in ["google", "meta"]:
            res = utmify.fetch_metrics(p, date_range=date_range)
            all_summaries[p] = utmify.calculate_summary(res)
        summary = all_summaries
    else:
        results = utmify.fetch_metrics(platform, date_range=date_range)
        print(f"SISTEMA: API UTMify retornou {len(results)} itens")
        if len(results) > 0:
            for i, item in enumerate(results):
                print(f"ITEM {i} -> Nome: {item.get('name')} | Gasto: {item.get('spend')} | Vendas: {item.get('approvedOrdersCount')}")
        else:
            print("SISTEMA: A API da UTMify retornou uma lista VAZIA. Verifique se há dados para este período.")
        summary = utmify.calculate_summary(results)

    print(f"SISTEMA: Sumário Calculado: {summary}")

    # 5. GERA RESPOSTA DINÂMICA COM IA
    response_text = synthesize_response(text, platform, period_name, summary)

    send_whatsapp_message(remote_jid, response_text)

@app.get("/test")
async def test():
    return {"status": "Alive!", "message": "O servidor do agente está funcionando perfeitamente."}

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        print(f"WEBHOOK RECEIVED: {body}")
    except Exception as e:
        print(f"Erro ao processar JSON do webhook: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    event = body.get("event") if isinstance(body, dict) else None

    if event == "messages.upsert":
        data = body.get("data", {}) if isinstance(body, dict) else {}
        if not data:
            return {"status": "ignored", "message": "No data found in payload"}

        message = data.get("message", {})
        if not message:
            return {"status": "ignored", "message": "No message found in data"}

        message_text = ""
        if isinstance(message, dict):
            if "conversation" in message:
                message_text = message["conversation"]
            elif "extendedTextMessage" in message:
                message_text = message["extendedTextMessage"].get("text", "")
            elif "text" in message:
                message_text = message["text"]
            else:
                for key, value in message.items():
                    if key in ["text", "content", "body"] and isinstance(value, str):
                        message_text = value
                        break

        remote_jid = data.get("key", {}).get("remoteJid")
        is_group = remote_jid.endswith("@g.us") if remote_jid else False

        # Verifica se o bot foi mencionado
        mentioned = False
        if is_group:
            context_info = data.get("contextInfo", {})
            mentions = context_info.get("mentionedJid", [])
            if mentions:
                mentioned = True
        else:
            mentioned = True

        if not remote_jid or not message_text:
            print(f"DEBUG: Mensagem ignorada. RemoteJid: {remote_jid}, Texto: {message_text}")
            return {"status": "ignored", "message": "Missing remoteJid or text"}

        if not mentioned:
            print(f"SISTEMA: Mensagem em grupo ignorada (sem menção). RemoteJid: {remote_jid}")
            return {"status": "ignored", "message": "Bot not mentioned in group"}

        print(f"SISTEMA: Processando requisição de {remote_jid}: {message_text}")
        background_tasks.add_task(process_request, message_text, remote_jid)

    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
