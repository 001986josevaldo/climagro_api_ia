import os
from contextlib import asynccontextmanager
from datetime import date
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from apscheduler.schedulers.background import BackgroundScheduler

from balanco_hidrico import BalancoHidricoINMET
from boletim_clima import BoletimClimatologicoINMET
from bot.bot_bal_hid import AgroAIBot
from bot.bot_bol_cli import BoletimClimatologicoBot

load_dotenv()

INMET_TOKEN = os.getenv("INMET_TOKEN")
if not INMET_TOKEN:
    raise ValueError("Token do INMET não encontrado no arquivo .env")

# Dicionário em memória que guardará os relatórios gerados
CACHE_DADOS = {
    "boletim": None,
    "balanco": None,
    "ultima_atualizacao": None
}


def atualizar_relatorios():
    """Executa as requisições do INMET e as análises das IAs, salvando no cache."""
    print("\n[CRON] Iniciando atualização diária dos relatórios...")
    hoje = date.today()
    hora_ref = "23:30"  # Às 23:30, o horário de referência de 23:30 é o ideal

    try:
        # 1. Processar Boletim Climatológico
        proc_boletim = BoletimClimatologicoINMET(token=INMET_TOKEN, cd_estacao="A025")
        dados_boletim = proc_boletim.gerar_boletim_24h(data_ref=hoje, hora_ref=hora_ref)
        
        #print(f"[CRON] Boletim climatológico obtido: {dados_boletim}")
        
        bot_boletim = BoletimClimatologicoBot()
        analise_boletim = bot_boletim.analisar_boletim(dados_boletim=dados_boletim)

        CACHE_DADOS["boletim"] = {
            "dados_meteorologicos": dados_boletim,
            "analise_ia": analise_boletim
        }

        # 2. Processar Balanço Hídrico
        proc_balanco = BalancoHidricoINMET(token=INMET_TOKEN, cd_estacao="A025")
        dados_balanco = proc_balanco.calcular_balanco_hidrico_24h(data_ref=hoje, hora_ref=hora_ref)

        #print(f"[CRON] Balanço hídrico obtido: {dados_balanco}")

        bot_balanco = AgroAIBot()
        pergunta = "analise diaria do balanço hídrico simplificado."
        analise_balanco = bot_balanco.analisar_balanco_hidrico(
            dados_balanco=dados_balanco,
            question=pergunta,
            history_messages=[]
        )

        CACHE_DADOS["balanco"] = {
            "dados_meteorologicos": dados_balanco,
            "analise_ia": analise_balanco
        }

        CACHE_DADOS["ultima_atualizacao"] = f"{hoje.isoformat()} 23:30:00"
        print("[CRON] Relatórios atualizados com sucesso!")

    except Exception as erro:
        print(f"[CRON] Erro ao atualizar relatórios: {erro}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configurar agendador diário para as 23:30
    scheduler = BackgroundScheduler()
    scheduler.add_job(atualizar_relatorios, "cron", hour=23, minute=30)
    scheduler.start()

    # Executa uma vez na inicialização para popular o cache se estiver vazio
    atualizar_relatorios()
    
    yield
    
    scheduler.shutdown()


app = FastAPI(
    title="API Climagro_IA",
    description="Serviço de geração e análise de relatórios agrometeorológicos com IA",
    lifespan=lifespan
)


@app.get("/boletimclimatologico")
def get_boletim_climatologico():
    if not CACHE_DADOS["boletim"]:
        raise HTTPException(status_code=503, detail="Dados do boletim ainda não disponíveis.")
    return CACHE_DADOS["boletim"]


@app.get("/balancohidrico")
def get_balanco_hidrico():
    if not CACHE_DADOS["balanco"]:
        raise HTTPException(status_code=503, detail="Dados do balanço hídrico ainda não disponíveis.")
    return CACHE_DADOS["balanco"]


@app.post("/atualizar-agora")
def forcar_atualizacao():
    """Rota utilitária para forçar a atualização imediata dos dados sem esperar as 23:30."""
    atualizar_relatorios()
    return {"message": "Atualização manual concluída com sucesso!"}