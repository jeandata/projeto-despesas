# Refatoração do Agente Bedrock
moved {
  from = aws_bedrockagent_agent.Gerar-texto-para-sql
  to   = aws_bedrockagent_agent.gerar_texto_para_sql
}

# Refatoração dos Jobs Glue
moved {
  from = aws_glue_job.job-despesas-bronze-to-silver
  to   = aws_glue_job.job_despesas_bronze_to_silver
}

moved {
  from = aws_glue_job.job-despesas-silver-to-gold
  to   = aws_glue_job.job_despesas_silver_to_gold
}