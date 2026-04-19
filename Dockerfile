# Use uma imagem leve do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o conteúdo do diretório local para /app no container
COPY . .

# Garante que o Python encontre os módulos na pasta /app
ENV PYTHONPATH=/app

# Expõe a porta que o FastAPI usa
EXPOSE 8000

# Comando para iniciar o servidor
CMD ["uvicorn", "whatsapp_agent:app", "--host", "0.0.0.0", "--port", "8000"]
