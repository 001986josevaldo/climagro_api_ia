import os
from dotenv import load_dotenv

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
#from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq


# Carrega as variáveis do .env
load_dotenv()


os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY', '')


class AgroAIBot:

    def __init__(self):
        self.__chat = ChatGroq(
            model="openai/gpt-oss-20b"  # Modelo recomendado para raciocínio agronômico
        )

    def __build_messages(self, history_messages, question):
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

    def analisar_balanco_hidrico(self, dados_balanco: dict, question: str = None, history_messages: list = None):
        """
        Gera uma análise agronômica baseada nos dados de balanço hídrico recebidos.
        """
        if history_messages is None:
            history_messages = []

        if not question:
            question = "analise diaria do balanço hídrico simplificado."

        SYSTEM_TEMPLATE = '''
            Você é um Engenheiro Agrônomo e consultor direto de campo.
            Forneça respostas diretas ao ponto e objetivas.

            ## Dados do Balanço Hídrico Recebido
            <balanco_hidrico>
            - Estação: {estacao} ({codigo_estacao})
            - Data/Hora de Referência: {data_referencia} às {hora_referencia}h
            - Precipitação Acumulada (P): {precipitacao_mm} mm
            - Evapotranspiração de Referência (ETo): {eto_mm} mm
            - Saldo do Balanço Hídrico (P - ETo): {balanco_hidrico_mm} mm
            - Status Atmosférico: {status}
            </balanco_hidrico>

            ## Regras de Resposta
            - Responda em no máximo 3 tópicos curtos (máximo 2 linhas por tópico).
            - **Situação Atual:** Impacto do saldo no solo.
            - **Manejo:** Recomendação direta de irrigação (ligar, desligar ou reduzir).
            - **Alerta Rápido:** Doença fúngica ou estresse hídrico (apenas se crítico).
            - Não use introduções, saudações formais ou explicações teóricas.
            '''


        prompt = ChatPromptTemplate.from_messages(
            [
                ('system', SYSTEM_TEMPLATE),
                MessagesPlaceholder(variable_name='messages'),
            ]
        )

        chain = prompt | self.__chat | StrOutputParser()

        # Injeta os valores do dicionário do balanço no template
        response = chain.invoke(
            {
                'estacao': dados_balanco.get('estacao', 'N/A'),
                'codigo_estacao': dados_balanco.get('codigo_estacao', 'N/A'),
                'data_referencia': dados_balanco.get('data_referencia', 'N/A'),
                'hora_referencia': dados_balanco.get('hora_referencia', 'N/A'),
                'precipitacao_mm': dados_balanco.get('precipitacao_mm', 0),
                'eto_mm': dados_balanco.get('eto_mm', 0),
                'balanco_hidrico_mm': dados_balanco.get('balanco_hidrico_mm', 0),
                'status': dados_balanco.get('status', 'N/A'),
                'messages': self.__build_messages(history_messages, question),
            }
        )

        return response