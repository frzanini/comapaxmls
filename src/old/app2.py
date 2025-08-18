import logging
from datetime import datetime
import requests
from dotenv import load_dotenv
import os

# Caminho absoluto para o .env na raiz do projeto
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=os.path.abspath(env_path))
api_key = os.getenv("SIEG_API_KEY")
base_url = os.getenv("URL_BAIXAR_XMLS")

url = f"https://api.sieg.com/api/Certificado/ListarCertificados?active=true&api_key={api_key}"
logging.info(f"Enviando requisição para URL: {url}")


try:
    response = requests.get(url)
    response.raise_for_status()
    logging.info(f"Resposta recebida com sucesso: {response.status_code}")
    print(response.json())
except requests.RequestException as e:
    logging.error(f"Erro ao se comunicar com a API: {e}")