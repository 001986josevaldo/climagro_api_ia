# 🌾 Climagro API - Agrometeorologia & Inteligência Agronômica

API em Python/FastAPI projetada para coletar, processar e analisar automaticamente os dados agrometeorológicos da estação automática do INMET em **Rio Verde - GO (A025)**.

O sistema calcula o **Balanço Hídrico Diário** via método Penman-Monteith (FAO-56), consolida estatísticas diárias e utiliza **LLMs (Groq / `openai/gpt-oss-20b`)** para entregar pareceres e recomendações práticas de irrigação e manejo fitossanitário para produtores rurais.

---

## 🚀 Funcionalidades

- **Cálculo de ETo (FAO-56):** Implementação rigorosa do método Penman-Monteith para Evapotranspiração de Referência.
- **Balanço Hídrico Diário:** Cálculo automático de saldo hídrico ($P - ETo$) das últimas 24 horas.
- **Boletim Climatológico:** Agregação diária de máximas, mínimas e médias de temperatura, umidade, vento, chuva e radiação solar global.
- **IA Agrônomo Especialista:** Resumo de dados e recomendações objetivas de manejo geradas por IA via LangChain.
- **Agendamento Inteligente (Cache):** Execução em segundo plano via `APScheduler` às 23:30 para atualizar o cache em memória e garantir respostas em milissegundos nas rotas da API.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Framework Web:** FastAPI & Uvicorn
- **Agendador:** APScheduler
- **LLM & IA:** LangChain Core, LangChain Groq (`llama-3.1-70b-versatile`)
- **Integração de Dados:** API de Estações Automáticas do INMET
- **Implantação:** Docker / Docker Compose

---

## 📂 Estrutura do Projeto

```text
├── bot/
│   ├── bot_bal_hid.py      # Agente IA para Balanço Hídrico
│   └── bot_bol_cli.py      # Agente IA para Boletim Climatológico
├── balanco_hidrico.py      # Regra de negócio (Penman-Monteith FAO-56)
├── boletim_clima.py        # Processador estatístico de 24h
├── main.py                 # Servidor FastAPI + Agendador Cron
├── Dockerfile              # Imagem Docker da aplicação
├── docker-compose.yml      # Orquestração do container
└── .env                    # Variáveis de ambiente (tokens e chaves)
```
