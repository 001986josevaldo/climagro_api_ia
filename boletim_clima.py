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

    def buscar_dados_24h(
        self, data_ref: date, hora_ref: str = "2330"
    ) -> list[dict]:
        """Busca as 24 leituras horárias que encerram na data/hora informadas."""
        hora_alvo = self._formatar_horario(hora_ref)

        data_inicio = (data_ref - timedelta(days=1)).isoformat()
        data_fim = data_ref.isoformat()

        url = f"{self.base_url}/{data_inicio}/{data_fim}/{self.cd_estacao}/{self.token}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        registros = response.json()

        if not isinstance(registros, list):
            raise ValueError("Resposta inválida da API do INMET.")

        registros_ordenados = sorted(
            registros,
            key=lambda x: (
                x.get("DT_MEDICAO", ""),
                str(x.get("HR_MEDICAO", "")).zfill(4),
            ),
        )

        indice_fim = None
        for i, reg in enumerate(registros_ordenados):
            dt = reg.get("DT_MEDICAO")
            hr = str(reg.get("HR_MEDICAO", "")).zfill(4)

            if dt == data_fim and hr == hora_alvo:
                indice_fim = i
                break

        if indice_fim is None:
            registros_24h = registros_ordenados[-24:]
        else:
            inicio = max(0, indice_fim - 23)
            registros_24h = registros_ordenados[inicio : indice_fim + 1]

        return registros_24h

    def gerar_boletim_24h(
        self, data_ref: date = None, hora_ref: str = "0800"
    ) -> dict:
        """Calcula agregados (médias, somas, máximos e mínimos) das últimas 24h."""
        if data_ref is None:
            data_ref = date.today()

        dados_24h = self.buscar_dados_24h(data_ref, hora_ref)

        if not dados_24h:
            raise ValueError("Nenhum dado encontrado para o período.")

        total_leituras = len(dados_24h)

        # 1. Temperatura (°C)
        temps = [
            float(r.get("TEM_INS"))
            for r in dados_24h
            if r.get("TEM_INS") is not None
        ]
        temp_max_lista = [
            float(r.get("TEM_MAX") or r.get("TEM_INS") or 0) for r in dados_24h
        ]
        temp_min_lista = [
            float(r.get("TEM_MIN") or r.get("TEM_INS") or 0) for r in dados_24h
        ]

        temp_media = sum(temps) / len(temps) if temps else 0.0
        temp_max = max(temp_max_lista) if temp_max_lista else 0.0
        temp_min = min(temp_min_lista) if temp_min_lista else 0.0

        # 2. Umidade Relativa (%)
        umidades = [
            float(r.get("UMD_INS"))
            for r in dados_24h
            if r.get("UMD_INS") is not None
        ]
        umid_max_lista = [
            float(r.get("UMD_MAX") or r.get("UMD_INS") or 0) for r in dados_24h
        ]
        umid_min_lista = [
            float(r.get("UMD_MIN") or r.get("UMD_INS") or 0) for r in dados_24h
        ]

        umidade_media = sum(umidades) / len(umidades) if umidades else 0.0
        umidade_max = max(umid_max_lista) if umid_max_lista else 0.0
        umidade_min = min(umid_min_lista) if umid_min_lista else 0.0

        # 3. Chuva (Acumulado total em mm)
        chuva_total = sum(float(r.get("CHUVA") or 0) for r in dados_24h)

        # 4. Ventos (m/s)
        ventos = [
            float(r.get("VEN_VEL"))
            for r in dados_24h
            if r.get("VEN_VEL") is not None
        ]
        rajadas = [
            float(r.get("VEN_RAJ") or 0)
            for r in dados_24h
            if r.get("VEN_RAJ") is not None
        ]

        vento_medio = sum(ventos) / len(ventos) if ventos else 0.0
        vento_rajada_max = max(rajadas) if rajadas else 0.0

        # 5. Radiação Global (Soma kJ/m² e conversão para MJ/m²)
        radiacao_total_mj = (
            sum(
                float(r.get("RAD_GLO") or 0)
                for r in dados_24h
                if float(r.get("RAD_GLO") or 0) > 0
            )
            / 1000.0
        )

        return {
            "estacao": dados_24h[0].get("DC_NOME", "N/A"),
            "codigo_estacao": self.cd_estacao,
            "data_referencia": data_ref.isoformat(),
            "hora_referencia": self._formatar_horario(hora_ref),
            "temp_max": round(temp_max, 1),
            "temp_min": round(temp_min, 1),
            "temp_media": round(temp_media, 1),
            "umidade_max": round(umidade_max, 1),
            "umidade_min": round(umidade_min, 1),
            "umidade_media": round(umidade_media, 1),
            "chuva_mm": round(chuva_total, 1),
            "vento_vel": round(vento_medio, 1),
            "vento_rajada": round(vento_rajada_max, 1),
            "radiacao_mj": round(radiacao_total_mj, 1),
        }