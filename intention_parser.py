import os
import json
from groq import Groq
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class IntentionParser:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY não encontrada nas variáveis de ambiente.")

        self.client = Groq(api_key=api_key)
        self.model_id = "llama-3.3-70b-versatile"

    def parse(self, text: str):
        """
        Analisa a mensagem do usuário e extrai a plataforma e o intervalo de datas usando Groq.
        Retorna um dicionário com platform, start_date e end_date.
        """
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_month = now.strftime("%B")
        current_year = now.strftime("%Y")

        prompt = f"""
        Você é um assistente especializado em extrair datas de mensagens para relatórios de marketing.
        DATA ATUAL: {current_date} ({current_month} {current_year})

        Sua tarefa é extrair a plataforma e o intervalo de datas exato.

        Regras Rigorosas de Data:
        1. 'Ontem': Se a data atual é {current_date}, 'ontem' deve ser obrigatoriamente o dia anterior.
        2. 'Mês atual' ou 'este mês': start_date é o dia 01 do mês corrente ({current_month} {current_year}) e end_date é hoje ({current_date}).
        3. 'Semana passada': calcule as datas da segunda a domingo da semana anterior à data atual.
        4. Datas específicas: extraia exatamente o dia mencionado.
        5. Padrão: Se não for possível determinar, use a data de ontem.

        Extraia:
        - Plataforma: 'google' ou 'meta'.
        - start_date: Formato YYYY-MM-DD.
        - end_date: Formato YYYY-MM-DD.

        Retorne APENAS um JSON no seguinte formato, sem marcações de markdown:
        {{
            "platform": "google" | "meta" | null,
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "reasoning": "explique brevemente o cálculo da data"
        }}

        Mensagem do usuário: "{text}"
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.1, # Baixa temperatura para maior precisão no JSON
                response_format={"type": "json_object"}
            )

            text_response = completion.choices[0].message.content
            print(f"GROQ RAW RESPONSE: {text_response}")

            parsed_json = json.loads(text_response)
            print(f"GROQ PARSED JSON: {parsed_json}")
            return parsed_json
        except Exception as e:
            print(f"Erro ao processar intenção com Groq: {e}")
            import traceback
            traceback.print_exc()
            return None
