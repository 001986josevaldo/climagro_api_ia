import os
from datetime import date
import requests
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

INMET_TOKEN = os.getenv("INMET_TOKEN")

if not INMET_TOKEN:
    raise ValueError("Token do INMET não encontrado no arquivo .env")

# Solicitar a data ao usuário (formato YYYY-MM-DD)
data_input = input("Digite a data para consulta (Formato: YYYY-MM-DD) [Enter para hoje]: ").strip()

if not data_input:
    data_consulta = date.today().isoformat()
else:
    data_consulta = data_input

# 1. Buscar a lista de estações automáticas
URL_ESTACOES = "https://apitempo.inmet.gov.br/estacoes/T"

try:
    response = requests.get(URL_ESTACOES, timeout=30)
    response.raise_for_status()
    estacoes = response.json()
except requests.RequestException as erro:
    raise SystemExit(f"Erro ao carregar a lista de estações: {erro}")

# 2. Localizar a estação de Rio Verde - GO (A025)
estacao_alvo = next(
    (e for e in estacoes if e.get("CD_ESTACAO") == "A025"),
    None
)

if not estacao_alvo:
    print("Estação de Rio Verde - GO não encontrada.")
else:
    codigo_estacao = estacao_alvo["CD_ESTACAO"]

    url_dados = (
        f"https://apitempo.inmet.gov.br/token/"
        f"estacao/{data_consulta}/{data_consulta}/{codigo_estacao}/{INMET_TOKEN}"
    )

    print(f"\nBuscando dados de {estacao_alvo.get('DC_NOME')} ({codigo_estacao}) para a data {data_consulta}...")

    try:
        resposta = requests.get(url_dados, timeout=30)
        resposta.raise_for_status()
        dados = resposta.json()

        if isinstance(dados, list) and len(dados) > 0:
            # 3. Somar o campo 'CHUVA' de todas as horas retornadas no dia
            chuva_total_mm = sum(float(registro.get("CHUVA") or 0) for registro in dados)
            total_leituras = len(dados)

            # 4. Exibir informações da estação
            print("\n================ INFORMAÇÕES DA ESTAÇÃO ================")
            print(f"Nome:      {estacao_alvo.get('DC_NOME')}")
            print(f"Código:    {estacao_alvo.get('CD_ESTACAO')}")
            print(f"Estado:    {estacao_alvo.get('SG_ESTADO')}")
            print(f"Latitude:  {estacao_alvo.get('VL_LATITUDE')}")
            print(f"Longitude: {estacao_alvo.get('VL_LONGITUDE')}")
            print(f"Altitude:  {estacao_alvo.get('VL_ALTITUDE')} m")
            print("========================================================\n")

            # 5. Exibir resultado da precipitação total
            print("================ PRECIPITAÇÃO DIÁRIA (CHUVA) ================")
            print(f"Data consultada:     {data_consulta}")
            print(f"Leituras no dia:     {total_leituras} de 24 horas")
            print(f"Total acumulado:     {round(chuva_total_mm, 2)} mm")
            print("=============================================================")
        else:
            print(f"\nNenhum registro encontrado para a data {data_consulta}.")

    except requests.RequestException as erro:
        print("Erro na requisição dos dados climáticos:", erro)