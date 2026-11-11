import os
from datetime import date
import requests
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

INMET_TOKEN = os.getenv("INMET_TOKEN")

if not INMET_TOKEN:
    raise ValueError("Token do INMET não encontrado no arquivo .env")

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
    #hoje = date.today().isoformat()  # YYYY-MM-DD
    hoje = "2026-11-10"
    url_dados = (
        f"https://apitempo.inmet.gov.br/token/"
        f"estacao/{hoje}/{hoje}/{codigo_estacao}/{INMET_TOKEN}"
    )

    print(f"Buscando dados de {estacao_alvo.get('DC_NOME')} ({codigo_estacao}) do dia {hoje}...")

    try:
        resposta = requests.get(url_dados, timeout=30)
        resposta.raise_for_status()
        dados = resposta.json()

        # 3. Filtrar a medição por horario
        horario_alvo = "1600"
        # Remove os dois-pontos e garante 4 dígitos (ex: "08:00" -> "0800")
        horario_formatado = horario_alvo.replace(":", "").zfill(4)
        registro_horario = None
        
        if isinstance(dados, list):
            for registro in dados:
                hr = str(registro.get("HR_MEDICAO", ""))

                if hr == horario_formatado or hr == horario_alvo:
                    registro_horario = registro
                    break

        # 4. Exibir informações da estação
        print("\n================ INFORMAÇÕES DA ESTAÇÃO ================")
        print(f"Nome:      {estacao_alvo.get('DC_NOME')}")
        print(f"Código:    {estacao_alvo.get('CD_ESTACAO')}")
        print(f"Estado:    {estacao_alvo.get('SG_ESTADO')}")
        print(f"Latitude:  {estacao_alvo.get('VL_LATITUDE')}")
        print(f"Longitude: {estacao_alvo.get('VL_LONGITUDE')}")
        print(f"Altitude:  {estacao_alvo.get('VL_ALTITUDE')} m")
        print("========================================================\n")

        # 5. Exibir todos os campos retornados para o horário das 09:00
        print(f"================ DADOS COMPLETOS DAS {horario_alvo} UTC ================")
        if registro_horario:
            for chave, valor in registro_horario.items():
                print(f"{chave:<15}: {valor if valor is not None else '-'}")
        else:
            print(f"Medição das {horario_alvo} UTC ainda não disponível ou não encontrada para a data atual.")
        print("===============================================================")

    except requests.RequestException as erro:
        print("Erro na requisição dos dados climáticos:", erro)