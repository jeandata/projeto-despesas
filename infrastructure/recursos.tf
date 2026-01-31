# ---------------------------------------------------------
# DEFINIÇÕES LOCAIS (Configuração Dinâmica)
# ---------------------------------------------------------

locals {
  bucket_assets_name = "aws-glue-assets-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
}

# ---------------------------------------------------------
# AWS GLUE JOBS (ETL Bronze/Silver/Gold)
# ---------------------------------------------------------

resource "aws_glue_job" "job_despesas_bronze_to_silver" {
  name              = "job-despesas-bronze-to-silver"
  role_arn          = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/Glue-Spark-Despesas-Role"
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60
  execution_class   = "STANDARD"

  command {
    name            = "glueetl"
    python_version  = "3"
    # AQUI: Usando o local em vez do var fixo
    script_location = "s3://${local.bucket_assets_name}/scripts/job-despesas-bronze-to-silver.py"
  }

  default_arguments = {
    "--TempDir"                    = "s3://${local.bucket_assets_name}/temporary/"
    "--datalake-formats"           = "delta"
    "--enable-metrics"             = "true"
    "--enable-spark-ui"            = "true"
    "--spark-event-logs-path"      = "s3://${local.bucket_assets_name}/sparkHistoryLogs/"
    "--enable-glue-datacatalog"    = "true"
  }

  tags = var.project_tags
}

resource "aws_glue_job" "job_despesas_silver_to_gold" {
  name              = "job-despesas-silver-to-gold"
  role_arn          = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/Glue-Spark-Despesas-Role"
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${local.bucket_assets_name}/scripts/job-despesas-silver-to-gold.py"
  }

  default_arguments = {
    "--TempDir"                    = "s3://${local.bucket_assets_name}/temporary/"
    "--datalake-formats"           = "delta"
    "--enable-glue-datacatalog"    = "true"
    "--spark-event-logs-path"      = "s3://${local.bucket_assets_name}/sparkHistoryLogs/"
  }

  tags = var.project_tags
}

# ---------------------------------------------------------
# AWS BEDROCK AGENT (Text-to-SQL AI)
# ---------------------------------------------------------

resource "aws_bedrockagent_agent" "gerar_texto_para_sql" {
  agent_name              = "Gerar-texto-para-sql"
  agent_resource_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/service-role/AmazonBedrockExecutionRoleForAgents_HGZTO645ANT"
  foundation_model        = "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0"
  
  description                 = "Agente Especialista em SQL para Base Orçamentária"
  idle_session_ttl_in_seconds = 600
  prepare_agent               = true

  # Instrução resumida para segurança no GitHub
  instruction = <<-EOT
    # SYSTEM ROLE
    Você é um Arquiteto de Banco de Dados Sênior e Especialista em SQL.
    Sua missão é atuar como uma interface entre usuários não técnicos e o banco de dados da empresa.
    
    # REGRAS
    1. RESPONDA APENAS com base nos dados recuperados.
    2. Gere APENAS comandos SELECT.
    3. Use formatação padrão SQL.

    # SCHEMA (Exemplo)
    - Tabela: ft_despesas (Fatos de despesas orçamentárias)
    - Tabela: dim_orgao (Dimensão de órgãos governamentais)
  EOT
}

# ---------------------------------------------------------
# STORAGE & COMPUTE (S3 & EC2)
# ---------------------------------------------------------

resource "aws_s3_bucket" "datalake_bucket" {
  bucket = "db-despesas"
  tags   = var.project_tags
}

resource "aws_instance" "ec2_meltano" {
  ami           = "ami-06f1fc9ae5ae7f31e" # Idealmente usar data.aws_ami aqui
  instance_type = "m7i-flex.large"
  key_name      = "ec2-ing"
  subnet_id     = "subnet-097ad93f42032be8a"
  
  vpc_security_group_ids = ["sg-05f842a94c6f02f4f", "sg-0a0440f2b2327fadd"]

  root_block_device {
    volume_size = 200
    volume_type = "gp3"
    encrypted   = false
  }

  tags = merge(var.project_tags, {
    Name = "ec2-ing"
  })
}

resource "aws_instance" "ec2_app_streamlit" {
  ami                  = "ami-06f1fc9ae5ae7f31e"
  instance_type        = "t3.micro"
  key_name             = "ec2-ing"
  iam_instance_profile = "Bedrock-processor"
  subnet_id            = "subnet-0984e9a59d2860366"
  
  vpc_security_group_ids = ["sg-01876cbdbef4404ef"]

  root_block_device {
    volume_size = 32
    volume_type = "gp3"
  }

  tags = merge(var.project_tags, {
    Name = "ec2-streamlit"
  })
}