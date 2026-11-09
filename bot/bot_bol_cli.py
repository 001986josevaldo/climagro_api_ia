import os
from dotenv import load_dotenv

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq

load_dotenv()

os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY', '')


class BoletimClimatologicoBot:

    def __init__(self, model_name: str = "openai/gpt-oss-20b"):
        self.__chat = ChatGroq(model=model_name)

    def __build_messages(self, history_messages: list, question: str) -> list:
        messages = []
        if history_messages:
            for message in history_messages:
                if "role" in message:
                    role = message.get("role")
                    content = message.get("content")
                else:
                    role = "assistant" if message.get("fromMe") else "user"
                    content = message.get("body")

                if not content or not str(content).strip():
                    continue

                if role == "user":
                    messages.append(HumanMessage(content=str(content).strip()))
                else:
                    messages.append(AIMessage(content=str(content).strip()))

        if question:
            messages.append(HumanMessage(content=question))

        return messages

    def analisar_boletim(
        self,
        dados_boletim: dict,
        question: str = None,
        history_messages: list = None,
    ) -> str:
        """
        Gera uma análise agronômica concisa baseada no boletim climatológico diário.
        """
        if history_messages is None:
            history_messages = []

        if not question:
            question = "Resumo e análise agronômica do boletim climatológico das últimas 24h."

        SYSTEM_TEMPLATE = '''
            Você é um Engenheiro Agrônomo e consultor agrometeorológico de campo.
            Forneça respostas diretas ao ponto, executivas e objetivas.

            ## Dados Climatológicos Recebidos (Últimas 24h)
            <boletim_climatologico>
            - Estação: {estacao} ({codigo_estacao})
            - Data de Referência: {data_referencia}
            - Temperatura: Máx {temp_max}°C | Mín {temp_min}°C | Média {temp_media}°C
            - Umidade Relativa: Máx {umidade_max}% | Mín {umidade_min}% | Média {umidade_media}%
            - Precipitação Acumulada: {chuva_mm} mm
            - Vento Médio: {vento_vel} m/s | Rajada Máx: {vento_rajada} m/s
            - Radiação Global Total: {radiacao_mj} MJ/m²
                        </boletim_climatologico>

                        ## Regras de Resposta
            - Responda em no máximo 3 tópicos curtos (máximo 2 linhas por tópico).
            - **Panorama Geral:** Resumo das condições térmicas, hídricas e de radiação.
            - **Impacto Agronômico:** Efeito no desenvolvimento da cultura, transpiração e janelas de operação (ex: pulverização).
            - **Alerta de Campo:** Risco de estresse térmico/hídrico, deriva por vento ou favorecimento de pragas/doenças.
            - Não use introduções, saudações formais ou explicações teóricas.
            '''

        prompt = ChatPromptTemplate.from_messages(
            [
                ('system', SYSTEM_TEMPLATE),
                MessagesPlaceholder(variable_name='messages'),
            ]
        )

        chain = prompt | self.__chat | StrOutputParser()

        response = chain.invoke(
            {
                'estacao': dados_boletim.get('estacao', 'N/A'),
                'codigo_estacao': dados_boletim.get('codigo_estacao', 'N/A'),
                'data_referencia': dados_boletim.get('data_referencia', 'N/A'),
                'temp_max': dados_boletim.get('temp_max', 0),
                'temp_min': dados_boletim.get('temp_min', 0),
                'temp_media': dados_boletim.get('temp_media', 0),
                'umidade_max': dados_boletim.get('umidade_max', 0),
                'umidade_min': dados_boletim.get('umidade_min', 0),
                'umidade_media': dados_boletim.get('umidade_media', 0),
                'chuva_mm': dados_boletim.get('chuva_mm', 0),
                'vento_vel': dados_boletim.get('vento_vel', 0),
                'vento_rajada': dados_boletim.get('vento_rajada', 0),
                'radiacao_mj': dados_boletim.get('radiacao_mj', 0),
                'messages': self.__build_messages(history_messages, question),
            }
        )

        return response 