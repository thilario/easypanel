import requests
import base64
import time
import json
from dotenv import load_dotenv
import os

# Carrega as credenciais do arquivo .env
load_dotenv()
EMAIL = os.getenv("UTMIFY_EMAIL")
PASSWORD = os.getenv("UTMIFY_PASSWORD")

# Configurações da API
BASE_URL = "https://server.utmify.com.br"
LOGIN_URL = f"{BASE_URL}/users/auth"
META_DATA_URL = f"{BASE_URL}/orders/search-objects"

# Headers obrigatórios para evitar bloqueios
COMMON_HEADERS = {
    "Origin": "https://app.utmify.com.br",
    "Referer": "https://app.utmify.com.br/",
    "Accept": "application/json"
}

def get_jwt_token():
    """Realiza o login via Basic Auth e retorna o JWT token."""
    print("Autenticando na UTMify...")

    # Cria a string email:senha e codifica em Base64
    auth_str = f"{EMAIL}:{PASSWORD}"
    auth_base64 = base64.b64encode(auth_str.encode()).decode()

    headers = {
        **COMMON_HEADERS,
        "Authorization": f"Basic {auth_base64}"
    }

    try:
        response = requests.get(LOGIN_URL, headers=headers)
        response.raise_for_status()
        data = response.json()

        # O token fica em data -> auth -> token
        token = data.get("auth", {}).get("token")
        if not token:
            print(f"DEBUG: Response data: {data}")
            raise Exception("Token não encontrado na resposta do servidor.")

        print("Login realizado com sucesso!")
        return token
    except Exception as e:
        print(f"Erro no login: {e}")
        return None

def fetch_meta_data(token):
    """Puxa os dados de campanhas do Meta usando o Bearer Token."""
    print("Extraindo dados do Meta...")

    headers = {
        **COMMON_HEADERS,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8"
    }

    # Endpoint específico para Google Ads
    url = f"{META_DATA_URL}/google"

    # Payload de busca com a estrutura correta de dateRange
    payload = {
        "level": "campaign",
        "dashboardId": "68a4b09891a5675eada2f046",
        "dateRange": {
            "from": "2026-04-18T03:00:00.000Z",
            "to": "2026-04-19T02:59:59.999Z"
        }
    }

    # Implementação de Retry Exponencial para erros 502/503
    retries = [2, 4, 6]
    for i, delay in enumerate(retries):
        try:
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code in [502, 503]:
                print(f"Servidor instavel (Erro {response.status_code}). Tentando novamente em {delay}s...")
                time.sleep(delay)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if i == len(retries) - 1:
                print(f"Falha definitiva apos {len(retries)} tentativas: {e}")
                return None
            print(f"Erro na requisicao: {e}. Tentando novamente em {retries[i]}s...")
            time.sleep(retries[i])

def main():
    if not EMAIL or not PASSWORD:
        print("Erro: Credenciais nao encontradas no arquivo .env")
        print("Por favor, edite o arquivo .env com seu e-mail e senha.")
        return

    token = get_jwt_token()
    if not token:
        return

    data = fetch_meta_data(token)

    if data:
        print("\nDados extraidos com sucesso!")
        # Salva em um arquivo JSON para análise
        with open("utmify_meta_results.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("Resultados salvos em: utmify_meta_results.json")

        # Imprime um resumo rápido no console
        print("\n--- Resumo dos Dados ---")
        print(json.dumps(data, indent=2)[:1000] + "...")
    else:
        print("Nao foi possivel extrair os dados.")

if __name__ == "__main__":
    main()
