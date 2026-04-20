import os
import json
from google import genai
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class IntentionParser:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada nas variáveis de ambiente.")

        # Nova biblioteca google-genai
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-1.5-flash'

    def parse(self, text: str):
        """
        Analisa a mensagem do usuário e extrai a plataforma e o intervalo de datas.
        Retorna um dicionário com platform, start_date e end_date.
        """
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_month = now.strftime("%B")
        current_year = now.strftime("%Y")

        prompt = f"""
        Você é um assistente especializado em extrair datas de mensagens para relatórios de marketing.
        Data atual: {current_date} ({current_month} {current_year})

        Analise a mensagem do usuário e extraia:
        1. Plataforma: 'google' ou 'meta'.
        2. Data de Início (start_date): Formato YYYY-MM-DD.
        3. Data de Fim (end_date): Formato YYYY-MM-DD.

        Regras:
        - Se o usuário disser 'ontem', start_date e end_date devem ser a data de ontem.
        - Se disser 'mês atual' ou 'este mês', start_date é o dia 1 do mês corrente e end_date é hoje.
        - Se disser 'semana passada', calcule as datas da segunda a domingo da semana anterior.
        - Se não mencionar plataforma, deixe como null.
        - Se não conseguir determinar a data, use 'ontem' como padrão.

        Retorne APENAS um JSON no seguinte formato:
        {{
            "platform": "google" | "meta" | null,
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "reasoning": "breve explicação do porquê escolheu essas datas"
        }}

        Mensagem do usuário: "{text}"
        """

        try:
            # Nova sintaxe da biblioteca google-genai
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )

            print(f"GEMINI RAW RESPONSE: {response.text}")

            # Remove possíveis marcações de markdown do JSON (ex: ```json ... ```)
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            parsed_json = json.loads(clean_text)
            print(f"GEMINI PARSED JSON: {parsed_json}")
            return parsed_json
        except Exception as e:
            print(f"Erro ao processar intenção com Gemini: {e}")
            import traceback
            traceback.print_exc()
            return None
