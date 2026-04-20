import os
import json
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class IntentionParser:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada nas variáveis de ambiente.")

        genai.configure(api_key=api_key)
        # Lista de modelos em ordem de preferência
        self.models_to_try = ['gemini-1.5-flash', 'gemini-pro']
        self.current_model_name = self.models_to_try[0]
        self.model = genai.GenerativeModel(self.current_model_name)

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

        # Tenta os modelos disponíveis até encontrar um que funcione
        for model_name in self.models_to_try:
            try:
                if self.current_model_name != model_name:
                    self.current_model_name = model_name
                    self.model = genai.GenerativeModel(model_name)

                response = self.model.generate_content(prompt)
                print(f"GEMINI RAW RESPONSE ({model_name}): {response.text}")

                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                parsed_json = json.loads(clean_text)
                print(f"GEMINI PARSED JSON: {parsed_json}")
                return parsed_json
            except Exception as e:
                print(f"Erro ao tentar modelo {model_name}: {e}")
                continue

        print("Falha total ao processar intenção com todos os modelos do Gemini.")
        return None
