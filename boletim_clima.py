from datetime import date, timedelta
import requests


class BoletimClimatologicoINMET:

    def __init__(self, token: str, cd_estacao: str = "A025"):
        self.token = token
        self.cd_estacao = cd_estacao
        self.base_url = "https://apitempo.inmet.gov.br/token/estacao"

    def _formatar_horario(self, hora_str: str) -> str:
        """Padroniza horários para o formato '0800'."""
        return hora_str.replace(":", "").zfill(4)

    @staticmethod
    def _para_float(valor):
        """Converte um valor para float; retorna None para valores ausentes ou inválidos."""
        if valor is None or str(valor).strip() == "":
            return None

        try:
            return float(valor)
        except (TypeError, ValueError):
            return None

    def buscar_dados_24h(self, data_ref: date) -> list[dict]:
        """Busca as últimas 24 leituras horárias disponíveis até a data informada."""
        data_inicio = (data_ref - timedelta(days=1)).isoformat()
        data_fim = data_ref.isoformat()

        url = f"{self.base_url}/{data_inicio}/{data_fim}/{self.cd_estacao}/{self.token}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        registros = response.json()

        if not isinstance(registros, list) or not registros:
            raise ValueError("Resposta inválida ou sem dados retornados pela API do INMET.")

        # Ordena cronologicamente por Data (DT_MEDICAO) e Hora (HR_MEDICAO)
        registros_ordenados = sorted(
            registros,
            key=lambda x: (
                x.get("DT_MEDICAO", ""),
                str(x.get("HR_MEDICAO", "")).zfill(4),
            ),
        )

        # Retorna as últimas 24 medições acumuladas mais recentes até o momento
        return registros_ordenados[-24:]

    def gerar_boletim_24h(
        self, data_ref: date = None) -> dict:
        """Calcula agregados (médias, somas, máximos e mínimos) das últimas 24h."""
        if data_ref is None:
            data_ref = date.today()

        dados_24h = self.buscar_dados_24h(data_ref)

        if not dados_24h:
            raise ValueError("Nenhum dado encontrado para o período.")

        # Extrai data e hora da última leitura real obtida (ex: "2300" -> "23:00")
        hr_raw = str(dados_24h[-1].get("HR_MEDICAO", "0000")).zfill(4)
        hora_referencia = f"{hr_raw[:2]}:{hr_raw[2:]}"
        data_referencia_leitura = dados_24h[-1].get("DT_MEDICAO", data_ref.isoformat())
        

        # 1. Temperatura (°C)
        # TEM_MIN/TEM_MAX podem vir vazios nas leituras horárias.
        # Nesse caso, o mínimo e o máximo devem ser calculados a partir de TEM_INS,
        # sem inserir 0 artificialmente na lista.
        temps = [
            valor
            for r in dados_24h
            if (valor := self._para_float(r.get("TEM_INS"))) is not None
        ]

        temp_media = sum(temps) / len(temps) if temps else None
        temp_max = max(temps) if temps else None
        temp_min = min(temps) if temps else None

        # 2. Umidade Relativa (%)
        umidades = [
            valor
            for r in dados_24h
            if (valor := self._para_float(r.get("UMD_INS"))) is not None
        ]

        umidade_media = sum(umidades) / len(umidades) if umidades else None
        umidade_max = max(umidades) if umidades else None
        umidade_min = min(umidades) if umidades else None

        # 3. Chuva (Acumulado total em mm)
        chuvas = [
            valor
            for r in dados_24h
            if (valor := self._para_float(r.get("CHUVA"))) is not None
        ]
        chuva_total = sum(chuvas) if chuvas else 0.0

        # 4. Ventos (m/s)
        ventos = [
            valor
            for r in dados_24h
            if (valor := self._para_float(r.get("VEN_VEL"))) is not None
        ]
        rajadas = [
            valor
            for r in dados_24h
            if (valor := self._para_float(r.get("VEN_RAJ"))) is not None
        ]

        vento_medio = sum(ventos) / len(ventos) if ventos else None
        vento_rajada_max = max(rajadas) if rajadas else None

        # 5. Radiação Global (Soma kJ/m² e conversão para MJ/m²)
        radiacoes = [
            valor
            for r in dados_24h
            if (valor := self._para_float(r.get("RAD_GLO"))) is not None
            and valor > 0
        ]
        radiacao_total_mj = sum(radiacoes) / 1000.0 if radiacoes else 0.0

        def arredondar(valor):
            return round(valor, 1) if valor is not None else None

        return {
            "estacao": dados_24h[0].get("DC_NOME", "N/A"),
            "codigo_estacao": self.cd_estacao,
            "data_referencia": data_referencia_leitura,
            "hora_referencia": hora_referencia,
            "temp_max": arredondar(temp_max),
            "temp_min": arredondar(temp_min),
            "temp_media": arredondar(temp_media),
            "umidade_max": arredondar(umidade_max),
            "umidade_min": arredondar(umidade_min),
            "umidade_media": arredondar(umidade_media),
            "chuva_mm": round(chuva_total, 1),
            "vento_vel": arredondar(vento_medio),
            "vento_rajada": arredondar(vento_rajada_max),
            "radiacao_mj": round(radiacao_total_mj, 1),
        }
