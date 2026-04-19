import requests
import base64
import time
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class UTMifyClient:
    def __init__(self):
        self.email = os.getenv("UTMIFY_EMAIL")
        self.password = os.getenv("UTMIFY_PASSWORD")
        self.base_url = "https://server.utmify.com.br"
        self.login_url = f"{self.base_url}/users/auth"
        self.common_headers = {
            "Origin": "https://app.utmify.com.br",
            "Referer": "https://app.utmify.com.br/",
            "Accept": "application/json"
        }
        self.token = None

    def authenticate(self):
        """Realiza o login e obtém o JWT token."""
        auth_str = f"{self.email}:{self.password}"
        auth_base64 = base64.b64encode(auth_str.encode()).decode()

        headers = {
            **self.common_headers,
            "Authorization": f"Basic {auth_base64}"
        }

        try:
            response = requests.get(self.login_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.token = data.get("auth", {}).get("token")
            if not self.token:
                raise Exception("Token não encontrado na resposta do servidor.")
            return self.token
        except Exception as e:
            print(f"Erro na autenticação UTMify: {e}")
            return None

    def get_date_range(self, days_back=1):
        """Retorna o dateRange no formato ISO UTC para a API."""
        # Exemplo: ontem (UTC-3 para UTC)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Ajuste aproximado para o formato usado no painel (03:00:00.000Z)
        from_str = start_date.strftime("%Y-%m-%dT03:00:00.000Z")
        to_str = (start_date + timedelta(days=1)).strftime("%Y-%m-%dT02:59:59.999Z")

        return {"from": from_str, "to": to_str}

    def fetch_metrics(self, platform="meta", date_range=None):
        """
        Extrai métricas de Meta ou Google Ads.
        platform: 'meta' ou 'google'
        """
        if not self.token:
            self.authenticate()

        # Define o endpoint baseado na plataforma
        url = f"{self.base_url}/orders/search-objects"
        if platform.lower() == "google":
            url = f"{self.base_url}/orders/search-objects/google"

        if not date_range:
            date_range = self.get_date_range()

        headers = {
            **self.common_headers,
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=UTF-8"
        }

        payload = {
            "level": "campaign",
            "dashboardId": "68a4b09891a5675eada2f046", # ID fixo do usuário
            "dateRange": date_range
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json().get("results", [])
        except Exception as e:
            print(f"Erro ao buscar dados de {platform}: {e}")
            return []

    def calculate_summary(self, results):
        """Processa a lista de resultados e retorna métricas agregadas."""
        total_spend = 0
        total_sales = 0
        total_revenue = 0

        for item in results:
            total_spend += item.get('spend', 0)
            total_sales += item.get('approvedOrdersCount', 0)
            total_revenue += item.get('revenue', 0)

        # Conversão de centavos para Real
        spend_brl = total_spend / 100
        revenue_brl = total_revenue / 100

        roas = revenue_brl / spend_brl if spend_brl > 0 else 0
        cac = spend_brl / total_sales if total_sales > 0 else 0

        return {
            "spend": spend_brl,
            "sales": total_sales,
            "revenue": revenue_brl,
            "roas": roas,
            "cac": cac
        }

if __name__ == "__main__":
    # Teste rápido do módulo
    client = UTMifyClient()
    if client.authenticate():
        print("Autenticado!")
        meta_data = client.fetch_metrics("meta")
        print(f"Meta Summary: {client.calculate_summary(meta_data)}")
        google_data = client.fetch_metrics("google")
        print(f"Google Summary: {client.calculate_summary(google_data)}")
