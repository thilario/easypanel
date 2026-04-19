# Use uma imagem leve do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do código para o container
COPY . .

# Expõe a porta que o FastAPI usa
EXPOSE 3000

# Comando para iniciar o servidor
CMD ["uvicorn", "whatsapp_agent:app", "--host", "0.0.0.0", "--port", "8000"]
