# 📊 Projeto de Análise de Despesas Públicas

## 📋 Visão Geral

Este projeto tem como objetivo extrair, transformar e disponibilizar dados de despesas do governo brasileiro através de uma plataforma de análise inteligente. O sistema utiliza tecnologias modernas de processamento de dados e inteligência artificial para tornar as informações sobre gastos públicos mais acessíveis e compreensíveis.

### O que este projeto faz?

1. **Extrai** dados de despesas de uma base de dados PostgreSQL
2. **Transforma** os dados usando Apache Spark no AWS Glue, organizando-os em camadas (Bronze, Silver e Gold)
3. **Disponibiliza** os dados através de uma interface web com inteligência artificial, permitindo que usuários façam perguntas em linguagem natural sobre as despesas públicas

### Arquitetura

A arquitetura completa do projeto está documentada no arquivo `Arquitetura.drawio.png` na raiz do projeto. O sistema segue uma arquitetura em camadas (medallion architecture) que garante qualidade e organização dos dados.

---

## 🔄 Ingestão de Dados

A etapa de ingestão é responsável por coletar os dados brutos da fonte e armazená-los na camada Bronze do S3.

### Como funciona?

A ingestão utiliza o **Meltano**, uma ferramenta open-source que facilita a extração e carregamento de dados (ELT). O processo funciona da seguinte forma:

1. **Extração**: Os dados são extraídos de uma tabela PostgreSQL chamada `stg_governo_gastos`
2. **Carregamento**: Os dados são carregados diretamente no S3 no formato Parquet, organizados por data (year/month/day)
3. **Armazenamento**: Os arquivos são salvos na camada Bronze do bucket `db-despesas`

### Estrutura de Pastas

```
ingestion/
├── meltano.yml          # Configuração do Meltano
├── plugins/             # Plugins de extração e carregamento
├── extract/             # Scripts de extração
├── transform/           # Transformações (se necessário)
├── load/                # Scripts de carregamento
└── orchestrate/         # Orquestração de pipelines
```

### Configuração

O arquivo `meltano.yml` contém toda a configuração necessária:
- **Extrator**: `tap-postgres` (extrai dados do PostgreSQL)
- **Carregador**: `target-s3` (carrega dados no S3)
- **Formato**: Parquet (otimizado para análise)
- **Particionamento**: Por data (year/month/day)

### Execução

Para executar a ingestão, você pode usar o comando Meltano:

```bash
meltano run tap-postgres target-s3
```

---

## ⚙️ Transformação de Dados

A transformação é realizada em duas etapas principais, utilizando Apache Spark no AWS Glue. Os dados passam por três camadas: Bronze → Silver → Gold.

### Bronze → Silver (`bronze-to-silver.py`)

Esta etapa realiza a limpeza e normalização inicial dos dados brutos.

**O que é feito:**
- Normalização dos nomes das colunas (remoção de acentos, espaços, caracteres especiais)
- Padronização de formatos de moeda (conversão de R$ 1.500,00 para 1500.00)
- Criação de colunas auxiliares (ano, mês, data de processamento)
- Tipagem correta dos dados (valores decimais, códigos inteiros)
- Armazenamento em formato Delta Lake para melhor performance e controle de versão

**Resultado:**
- Dados limpos e padronizados na camada Silver
- Tabela registrada no Glue Data Catalog: `silver_db.tb_stg_governo_gastos`

### Silver → Gold (`silver-to-gold.py`)

Esta etapa modela os dados em um esquema estrela (Star Schema) otimizado para análise.

**O que é feito:**
- Criação de tabelas dimensão:
  - `dim_orgao`: Órgãos superiores
  - `dim_tempo`: Dimensão temporal (ano, mês, semestre)
  - `dim_gestao`: Gestões
  - `dim_unidade_gestora`: Unidades gestoras
  - `dim_unidade_orcamentaria`: Unidades orçamentárias
- Criação de tabela fato:
  - `ft_despesas`: Tabela principal com as métricas de despesas, particionada por ano e mês

**Resultado:**
- Modelo de dados dimensional pronto para análise
- Tabelas registradas no Glue Data Catalog: `gold_db.*`
- Dados particionados para melhor performance em consultas

### Estrutura de Pastas

```
transformation/
├── bronze-to-silver.py  # Job de transformação Bronze → Silver
└── silver-to-gold.py    # Job de transformação Silver → Gold
```

### Execução

Os jobs são executados no AWS Glue. Cada job pode ser agendado ou executado manualmente através do console do AWS Glue ou via API.

---

## 🎨 Visualização e Interface com IA

A visualização é feita através de uma aplicação web desenvolvida em Streamlit que utiliza inteligência artificial para responder perguntas sobre as despesas públicas.

### Como funciona?

A aplicação permite que usuários façam perguntas em linguagem natural sobre as despesas públicas. Por exemplo:
- "Qual o valor total pago em 2025?"
- "Quais são os órgãos que mais gastaram este ano?"
- "Mostre as despesas do mês de janeiro"

A IA (AWS Bedrock Agent) processa essas perguntas, consulta os dados na camada Gold e retorna respostas compreensíveis.

### Tecnologias Utilizadas

- **Streamlit**: Framework para criar interfaces web em Python
- **AWS Bedrock Agent**: Serviço de IA generativa da AWS que permite criar agentes conversacionais
- **boto3**: SDK da AWS para Python

### Estrutura de Pastas

```
visualization/
└── app.py  # Aplicação Streamlit principal
```

### Configuração Necessária

A aplicação requer as seguintes variáveis de ambiente:
- `AGENT_ID`: ID do agente Bedrock configurado
- `AGENT_ALIAS_ID`: ID do alias do agente

### Execução Local

```bash
cd visualization
streamlit run app.py
```

### Deploy

A aplicação pode ser executada em uma instância EC2 ou em um serviço de container (ECS, EKS) na AWS.

---

## ☁️ Configuração de Ambientes AWS

Esta seção descreve os recursos AWS necessários para o funcionamento completo do projeto. Os detalhes específicos de cada ambiente devem ser preenchidos conforme a configuração real.

### 🖥️ Instância EC2 - Ingestão

**Propósito**: Executar o processo de ingestão de dados usando Meltano.

**Configurações necessárias:**
- [ ] Tipo de instância: _______________
- [ ] Sistema operacional: _______________
- [ ] Tamanho do disco: _______________
- [ ] Security Group: _______________
  - [ ] Regras de entrada: _______________
  - [ ] Regras de saída: _______________
- [ ] IAM Role: _______________
  - [ ] Permissões S3: _______________
  - [ ] Permissões RDS/PostgreSQL: _______________
- [ ] Variáveis de ambiente configuradas:
  - [ ] `PG_HOST`: _______________
  - [ ] `PG_USER`: _______________
  - [ ] `PG_PASSWORD`: _______________
  - [ ] `PG_DATABASE`: _______________
- [ ] Software instalado:
  - [ ] Python: _______________
  - [ ] Meltano: _______________
  - [ ] Plugins Meltano: _______________

### 🖥️ Instância EC2 - Visualização

**Propósito**: Hospedar a aplicação Streamlit de visualização.

**Configurações necessárias:**
- [ ] Tipo de instância: _______________
- [ ] Sistema operacional: _______________
- [ ] Tamanho do disco: _______________
- [ ] Security Group: _______________
  - [ ] Regras de entrada (porta 8501 para Streamlit): _______________
  - [ ] Regras de saída: _______________
- [ ] IAM Role: _______________
  - [ ] Permissões Bedrock: _______________
  - [ ] Permissões S3 (se necessário): _______________
  - [ ] Permissões Glue (se necessário): _______________
- [ ] Variáveis de ambiente configuradas:
  - [ ] `AGENT_ID`: _______________
  - [ ] `AGENT_ALIAS_ID`: _______________
- [ ] Software instalado:
  - [ ] Python: _______________
  - [ ] Streamlit: _______________
  - [ ] boto3: _______________
- [ ] Configuração de serviço (systemd/supervisor):
  - [ ] Nome do serviço: _______________
  - [ ] Comando de inicialização: _______________

### 🔧 AWS Glue

**Propósito**: Executar os jobs de transformação de dados (Bronze → Silver → Gold).

**Configurações necessárias:**

#### Glue Database - Silver
- [ ] Nome do database: `silver_db`
- [ ] Localização S3: `s3://db-despesas/silver/silver_db.db`
- [ ] Tabelas criadas:
  - [ ] `tb_stg_governo_gastos`

#### Glue Database - Gold
- [ ] Nome do database: `gold_db`
- [ ] Localização S3: `s3://db-despesas/gold/gold_db.db`
- [ ] Tabelas criadas:
  - [ ] `dim_orgao`
  - [ ] `dim_tempo`
  - [ ] `dim_gestao`
  - [ ] `dim_unidade_gestora`
  - [ ] `dim_unidade_orcamentaria`
  - [ ] `ft_despesas`

#### Glue Job - Bronze to Silver
- [ ] Nome do job: _______________
- [ ] Tipo: Spark
- [ ] Versão do Glue: _______________
- [ ] Número de workers: _______________
- [ ] Tipo de worker: _______________
- [ ] Script S3: `s3://_____________/transformation/bronze-to-silver.py`
- [ ] IAM Role: _______________
  - [ ] Permissões S3 (read/write): _______________
  - [ ] Permissões Glue Catalog: _______________
- [ ] Parâmetros do job:
  - [ ] `--JOB_NAME`: _______________
- [ ] Agendamento (opcional):
  - [ ] Frequência: _______________
  - [ ] Horário: _______________

#### Glue Job - Silver to Gold
- [ ] Nome do job: _______________
- [ ] Tipo: Spark
- [ ] Versão do Glue: _______________
- [ ] Número de workers: _______________
- [ ] Tipo de worker: _______________
- [ ] Script S3: `s3://_____________/transformation/silver-to-gold.py`
- [ ] IAM Role: _______________
  - [ ] Permissões S3 (read/write): _______________
  - [ ] Permissões Glue Catalog: _______________
- [ ] Parâmetros do job:
  - [ ] `--JOB_NAME`: _______________
- [ ] Agendamento (opcional):
  - [ ] Frequência: _______________
  - [ ] Horário: _______________

#### Dependências
- [ ] Delta Lake JAR: `s3://_____________/jars/delta-core_2.12-2.x.x.jar`
- [ ] Outras dependências: _______________

### ⚡ AWS Lambda

**Propósito**: Orquestração e automação de processos (opcional, se necessário).

**Configurações necessárias:**

#### Lambda Function 1 (se aplicável)
- [ ] Nome da função: _______________
- [ ] Runtime: Python _______________
- [ ] Handler: _______________
- [ ] Timeout: _______________
- [ ] Memória: _______________
- [ ] IAM Role: _______________
  - [ ] Permissões: _______________
- [ ] Variáveis de ambiente:
  - [ ] _______________
- [ ] Triggers:
  - [ ] EventBridge (CloudWatch Events): _______________
  - [ ] S3 Event: _______________
  - [ ] Outros: _______________

#### Lambda Function 2 (se aplicável)
- [ ] Nome da função: _______________
- [ ] Runtime: Python _______________
- [ ] Handler: _______________
- [ ] Timeout: _______________
- [ ] Memória: _______________
- [ ] IAM Role: _______________
  - [ ] Permissões: _______________
- [ ] Variáveis de ambiente:
  - [ ] _______________
- [ ] Triggers:
  - [ ] EventBridge (CloudWatch Events): _______________
  - [ ] S3 Event: _______________
  - [ ] Outros: _______________

### 🤖 AWS Bedrock

**Propósito**: Fornecer a capacidade de IA generativa para responder perguntas sobre os dados.

**Configurações necessárias:**

#### Modelo Base
- [ ] Modelo utilizado: _______________ (ex: Claude 3 Sonnet, Claude 3 Haiku)
- [ ] Região: `us-east-2` (ou outra conforme necessário)

#### Bedrock Agent
- [ ] Nome do agente: _______________
- [ ] ID do agente: _______________
- [ ] Alias ID: _______________
- [ ] Versão do alias: _______________
- [ ] Instruções do agente: _______________
  - [ ] Descrição do propósito: _______________
  - [ ] Contexto sobre os dados: _______________
  - [ ] Formato de resposta esperado: _______________

#### Knowledge Base (Base de Conhecimento)
- [ ] Nome da knowledge base: _______________
- [ ] Fonte de dados:
  - [ ] Tipo: S3 / Glue Data Catalog
  - [ ] Localização: `s3://db-despesas/gold/` ou `gold_db`
- [ ] Modelo de embedding: _______________
- [ ] Configuração de indexação:
  - [ ] Frequência de atualização: _______________
  - [ ] Campos indexados: _______________

#### IAM Permissions
- [ ] IAM Role para o Bedrock Agent: _______________
  - [ ] Permissões de leitura na Knowledge Base: _______________
  - [ ] Permissões de leitura no S3 (camada Gold): _______________
  - [ ] Permissões de leitura no Glue Data Catalog: _______________
  - [ ] Permissões de invocação do modelo: _______________

#### Configuração de Conexão
- [ ] Data Source:
  - [ ] Tipo: _______________
  - [ ] Configuração: _______________
- [ ] Schema de dados:
  - [ ] Tabelas disponíveis: _______________
  - [ ] Descrição das tabelas: _______________

---

## 📦 Estrutura do Projeto

```
Despesas/
├── Arquitetura.drawio.png    # Diagrama de arquitetura
├── README.md                  # Este arquivo
├── data/                      # Dados iniciais e scripts de carga
│   ├── *.csv                  # Arquivos CSV de despesas
│   ├── carga_base.py          # Script para carregar dados no PostgreSQL
│   └── Dicionario.xlsx        # Dicionário de dados
├── ingestion/                 # Pipeline de ingestão
│   ├── meltano.yml            # Configuração do Meltano
│   └── plugins/               # Plugins de extração e carregamento
├── transformation/            # Jobs de transformação
│   ├── bronze-to-silver.py    # Transformação Bronze → Silver
│   └── silver-to-gold.py      # Transformação Silver → Gold
└── visualization/             # Interface de visualização
    └── app.py                 # Aplicação Streamlit
```

---

## 🚀 Como Começar

1. **Configure os ambientes AWS** conforme a seção de configuração acima
2. **Execute a ingestão** na instância EC2 de ingestão
3. **Execute os jobs de transformação** no AWS Glue
4. **Configure o Bedrock Agent** com acesso à camada Gold
5. **Inicie a aplicação de visualização** na instância EC2 de visualização

---

## 📝 Notas Importantes

- Os dados são armazenados no bucket S3 `db-despesas` na região `us-east-2`
- O formato Delta Lake é utilizado nas camadas Silver e Gold para melhor performance e controle de versão
- A aplicação de visualização requer que o Bedrock Agent esteja configurado e acessível
- As permissões IAM devem ser configuradas corretamente para cada serviço acessar os recursos necessários

---

## 📧 Contato e Suporte

Para dúvidas ou suporte sobre este projeto, consulte a documentação específica de cada módulo ou entre em contato com a equipe responsável.
