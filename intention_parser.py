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
        Analisa a mensagem do usuário e extrai a intenção, métrica e plataforma.
        Retorna um dicionário com platform, period_type, e a métrica de interesse.
        """
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")

        prompt = f"""
        Você é um assistente especializado em extrair intenções de relatórios de marketing.
        Data atual: {current_date}

        Analise a mensagem do usuário e identifique:
        1. Plataforma: 'google' ou 'meta'.
        2. Tipo de Período:
           - 'ontem' (se pedir ontem, dia anterior, etc)
           - 'mes_atual' (se pedir mês atual, este mês, mensal)
           - 'semana_passada' (se pedir semana passada)
           - 'especifico' (se mencionar datas exatas como 'dia 10', 'de 01 a 05')

        3. Objetivo da Análise:
           - 'geral' (resumo de todas as métricas)
           - 'gasto' (foco em custo/spend)
           - 'vendas' (foco em conversões/sales)
           - 'performance' (foco em ROAS, CAC e eficiência)
           - 'insights' (análise crítica e sugestões)

        Se for 'especifico', extraia as datas no formato YYYY-MM-DD.

        Retorne APENAS um JSON no seguinte formato:
        {{
            "platform": "google" | "meta" | null,
            "period_type": "ontem" | "mes_atual" | "semana_passada" | "especifico",
            "objective": "geral" | "gasto" | "vendas" | "performance" | "insights",
            "start_date": "YYYY-MM-DD" | null,
            "end_date": "YYYY-MM-DD" | null
        }}

        Mensagem do usuário: "{text}"
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            text_response = completion.choices[0].message.content
            print(f"GROQ RAW RESPONSE: {text_response}")

            parsed_json = json.loads(text_response)
            print(f"GROQ PARSED JSON: {parsed_json}")
            return parsed_json
        except Exception as e:
            print(f"Erro ao processar intenção com Groq: {e}")
            return None
