from datetime import date, datetime, timedelta
import math
import requests
from dotenv import load_dotenv
import os

# Carregar variáveis do arquivo .env
load_dotenv()

INMET_TOKEN = os.getenv("INMET_TOKEN")

if not INMET_TOKEN:
    raise ValueError("Token do INMET não encontrado no arquivo .env")



class BalancoHidricoINMET:

    def __init__(self, token: str, cd_estacao: str = "A025"):
        self.token = token
        self.cd_estacao = cd_estacao
        self.base_url = "https://apitempo.inmet.gov.br/token/estacao"

    def _formatar_horario(self, hora_str: str) -> str:
        """Padroniza strings como '8', '08:00', '8:00' para o formato do INMET '0800'."""
        limpo = hora_str.replace(":", "").zfill(4)
        return limpo

    def buscar_dados_24h(
        self, data_ref: date, hora_ref: str = "2330"
    ) -> list[dict]:
        """Busca e filtra exatamente as 24 leituras horárias acumuladas até o horário informado."""
        hora_alvo = self._formatar_horario(hora_ref)

        # Como 24 horas podem cruzar para o dia anterior, buscamos ontens e hoje
        data_inicio = (data_ref - timedelta(days=1)).isoformat()
        data_fim = data_ref.isoformat()

        url = f"{self.base_url}/{data_inicio}/{data_fim}/{self.cd_estacao}/{self.token}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        registros = response.json()

        if not isinstance(registros, list):
            raise ValueError("A resposta da API do INMET não retornou uma lista válida.")

        # Ordenar registros cronologicamente por DT_MEDICAO e HR_MEDICAO
        registros_ordenados = sorted(
            registros,
            key=lambda x: (x.get("DT_MEDICAO", ""), x.get("HR_MEDICAO", "")),
        )

        # Identificar a posição do registro final (data_ref no hora_ref)
        indice_fim = None
        for i, reg in enumerate(registros_ordenados):
            dt = reg.get("DT_MEDICAO")
            hr = str(reg.get("HR_MEDICAO", "")).zfill(4)

            if dt == data_fim and hr == hora_alvo:
                indice_fim = i
                break

        if indice_fim is None:
            # Caso o horário exato de hoje não tenha entrado ainda, pega os últimos 24 disponíveis
            registros_24h = registros_ordenados[-24:]
        else:
            # Pega os 24 registros que encerram na hora de referência
            inicio = max(0, indice_fim - 23)
            registros_24h = registros_ordenados[inicio : indice_fim + 1]

        return registros_24h

    def _calcular_eto_fao56(self, dados_24h: list[dict]) -> float:
        """Calcula a Evapotranspiração de Referência (ETo) em mm/dia pelo método Penman-Monteith FAO-56."""
        # Extract metadata
        lat = float(dados_24h[0].get("VL_LATITUDE", -17.78))
        alt = float(dados_24h[0].get("VL_ALTITUDE", 700))

        # 1. Agregação dos dados meteorológicos do período
        temp_max = max(
            float(r.get("TEM_MAX") or r.get("TEM_INS") or 0) for r in dados_24h
        )
        temp_min = min(
            float(r.get("TEM_MIN") or r.get("TEM_INS") or 0) for r in dados_24h
        )
        temp_med = (temp_max + temp_min) / 2.0

        umid_med = sum(
            float(r.get("UMD_INS") or 0) for r in dados_24h
        ) / len(dados_24h)
        vento_med = sum(
            float(r.get("VEN_VEL") or 0) for r in dados_24h
        ) / len(dados_24h)
        pressao_med = (
            sum(float(r.get("PRE_INS") or 930) for r in dados_24h)
            / len(dados_24h)
        ) / 10.0  # hPa para kPa

        # Radiação Global total (soma de kJ/m² convertida para MJ/m²/dia)
        rad_total_mj = (
            sum(
                float(r.get("RAD_GLO") or 0)
                for r in dados_24h
                if float(r.get("RAD_GLO") or 0) > 0
            )
            / 1000.0
        )

        # 2. Equações Psicrométricas e Termodinâmicas (FAO-56)
        # Constante psicrométrica (gamma)
        gamma = 0.000665 * pressao_med

        # Inclinação da curva de pressão de vapor (Delta)
        delta = (4098 * (0.6108 * math.exp((17.27 * temp_med) / (temp_med + 237.3)))) / (
            (temp_med + 237.3) ** 2
        )

        # Pressão saturada de vapor (es) e pressão atual (ea)
        e0_tmax = 0.6108 * math.exp((17.27 * temp_max) / (temp_max + 237.3))
        e0_tmin = 0.6108 * math.exp((17.27 * temp_min) / (temp_min + 237.3))
        es = (e0_tmax + e0_tmin) / 2.0
        ea = es * (umid_med / 100.0)

        # 3. Radiação Líquida (Rn)
        # Estimativa astronômica da radiação de céu claro (Rso)
        rso = (0.75 + 2e-5 * alt) * max(rad_total_mj, 1.0)
        rns = 0.77 * rad_total_mj  # Saldo de radiação de onda curta (albedo = 0.23)

        # Saldo de radiação de onda longa (Rnl)
        tmax_k = temp_max + 273.16
        tmin_k = temp_min + 273.16
        sigma = 4.903e-9  # Constante Stefan-Boltzmann (MJ/K^4/m^2/dia)

        fator_umid = 0.34 - 0.14 * math.sqrt(ea)
        fator_sol = 1.35 * min(rad_total_mj / rso if rso > 0 else 1.0, 1.0) - 0.35

        rnl = (
            sigma
            * ((tmax_k**4 + tmin_k**4) / 2.0)
            * fator_umid
            * fator_sol
        )
        rn = rns - rnl

        # 4. Equação Final FAO-56 Penman-Monteith
        g = 0  # Fluxo de calor no solo (insignificante para escala diária)
        num = 0.408 * delta * (rn - g) + gamma * (900 / (temp_med + 273)) * vento_med * (
            es - ea
        )
        den = delta + gamma * (1 + 0.34 * vento_med)

        eto = num / den
        return max(round(eto, 2), 0.0)

    def calcular_balanco_hidrico_24h(
        self, data_ref: date = None, hora_ref: str = "0800"
    ) -> dict:
        """Calcula a precipitação acumulada, a ETo e o Balanço Hídrico final das últimas 24h."""
        if data_ref is None:
            data_ref = date.today()

        dados_24h = self.buscar_dados_24h(data_ref, hora_ref)

        if not dados_24h:
            raise ValueError("Nenhum dado encontrado para o período informado.")

        # Soma total de precipitação nas 24h (mm)
        chuva_24h = sum(float(r.get("CHUVA") or 0) for r in dados_24h)

        # Cálculo da Evapotranspiração de Referência (ETo)
        eto_24h = self._calcular_eto_fao56(dados_24h)

        # Balanço Hídrico Atmosférico (P - ETo)
        balanco = chuva_24h - eto_24h

        status = "Excedente Hídrico" if balanco  > 0 else "Déficit Hídrico"

        return {
            "estacao": dados_24h[0].get("DC_NOME"),
            "codigo_estacao": self.cd_estacao,
            "periodo_leituras": len(dados_24h),
            "data_referencia": data_ref.isoformat(),
            "hora_referencia": self._formatar_horario(hora_ref),
            "precipitacao_mm": round(chuva_24h, 2),
            "eto_mm": eto_24h,
            "balanco_hidrico_mm": round(balanco, 2),
            "status": status,
        }

