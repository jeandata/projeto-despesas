import sys
import unicodedata
import re
import datetime
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, split, current_timestamp, to_date, lit
from pyspark.sql.types import IntegerType, DecimalType
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf

# ============================================================================
# 1. FUNÇÕES AUXILIARES E LIMPEZA
# ============================================================================

def get_brasilia_date():
    return datetime.datetime.now() - datetime.timedelta(hours=3)

def delete_all_folder_markers_recursive(bucket_name, prefix):
    s3 = boto3.client('s3')
    clean_prefix = prefix.rstrip('/')
    
    print(f"[INFO] Varrendo marcadores em: s3://{bucket_name}/{clean_prefix}*")
    
    paginator = s3.get_paginator('list_objects_v2')
    files_to_delete = []
    
    # Varre usando o prefixo sem barra
    for page in paginator.paginate(Bucket=bucket_name, Prefix=clean_prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                # A lógica endswith garante que pegamos apenas os marcadores
                if obj['Key'].endswith('_$folder$'):
                    files_to_delete.append({'Key': obj['Key']})

    if files_to_delete:
        print(f"[INFO] Encontrados {len(files_to_delete)} marcadores. Deletando...")
        for i in range(0, len(files_to_delete), 1000):
            batch = files_to_delete[i:i+1000]
            try:
                s3.delete_objects(Bucket=bucket_name, Delete={'Objects': batch})
                print(f"[SUCESSO] Lote deletado.")
            except Exception as e:
                print(f"[ERRO] Falha no lote: {e}")
    else:
        print("[INFO] Nenhum marcador encontrado com este prefixo.")

def ensure_database_exists(database_name, warehouse_uri):
    glue = boto3.client('glue')
    try:
        glue.get_database(Name=database_name)
    except glue.exceptions.EntityNotFoundException:
        pass
    
    db_input = {'Name': database_name, 'LocationUri': warehouse_uri}
    try:
        glue.create_database(DatabaseInput=db_input)
    except glue.exceptions.AlreadyExistsException:
        glue.update_database(Name=database_name, DatabaseInput=db_input)

# ============================================================================
# 2. FUNÇÃO GENÉRICA DE ESCRITA
# ============================================================================

def save_delta_table(df, database, table_name, s3_path, partition_cols=None):
    print(f"[INFO] Processando tabela: {table_name}")
    
    writer = df.write.format("delta").mode("overwrite") \
        .option("mergeSchema", "true").option("overwriteSchema", "false")
    
    if partition_cols:
        writer = writer.partitionBy(*partition_cols)
        
    writer.save(s3_path)
    
    spark.sql(f"DROP TABLE IF EXISTS {database}.{table_name}")
    sql_create = f"CREATE TABLE {database}.{table_name} USING DELTA LOCATION '{s3_path}'"
    spark.sql(sql_create)
    print(f"[SUCESSO] Tabela {database}.{table_name} criada.")

# ============================================================================
# 3. CONFIGURAÇÃO
# ============================================================================

BUCKET_NAME = "db-despesas"
GLUE_DATABASE_GOLD = "gold_db"
WAREHOUSE_ROOT = f"s3://{BUCKET_NAME}/gold"
DATABASE_LOCATION = f"{WAREHOUSE_ROOT}/{GLUE_DATABASE_GOLD}.db"

# Caminhos (Adicionei os que faltavam)
PATH_SILVER = f"s3://{BUCKET_NAME}/silver/stg_governo_gastos"

PATH_GOLD_DIM_ORGAO = f"s3://{BUCKET_NAME}/gold/dim_orgao"
PATH_GOLD_DIM_TEMPO = f"s3://{BUCKET_NAME}/gold/dim_tempo"
PATH_GOLD_DIM_GESTAO = f"s3://{BUCKET_NAME}/gold/dim_gestao"
PATH_GOLD_DIM_UNIDADE_GESTORA = f"s3://{BUCKET_NAME}/gold/dim_unidade_gestora"
PATH_GOLD_DIM_UNIDADE_ORCAMENTARIA = f"s3://{BUCKET_NAME}/gold/dim_unidade_orcamentaria"
PATH_GOLD_FT_DESPESAS = f"s3://{BUCKET_NAME}/gold/ft_despesas"

conf = SparkConf()
conf.set("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
conf.set("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
conf.set("spark.sql.adaptive.enabled", "true")
conf.set("spark.hadoop.fs.s3.metadata.type", "no_metadata")
conf.set("spark.hadoop.mapreduce.fileoutputcommitter.marksuccessfuljobs", "false")
conf.set("spark.sql.warehouse.dir", WAREHOUSE_ROOT)

spark = SparkSession.builder.config(conf=conf).getOrCreate()
sc = spark.sparkContext
glueContext = GlueContext(sc)
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Cria DB Gold
ensure_database_exists(GLUE_DATABASE_GOLD, DATABASE_LOCATION)

# ============================================================================
# 4. EXECUÇÃO - MODELAGEM STAR SCHEMA
# ============================================================================

print("[INFO] Lendo camada Silver...")
df_silver = spark.read.format("delta").load(PATH_SILVER)

# --- A. CRIAR DIMENSÃO ÓRGÃO (dim_orgao) ---
print("[INFO] Criando dim_orgao...")

col_cd = "cd_orgao_superior"
col_nm = "nm_orgao_superior"

if col_cd in df_silver.columns and col_nm in df_silver.columns:
    df_dim_orgao = df_silver.select(
        col(col_cd).alias("id_orgao"),
        col(col_nm).alias("nome_orgao")
    ).distinct().orderBy("id_orgao")
    
    save_delta_table(df_dim_orgao, GLUE_DATABASE_GOLD, "dim_orgao", PATH_GOLD_DIM_ORGAO)
else:
    print(f"[AVISO] Colunas ({col_cd}, {col_nm}) não encontradas. Pulando dim_orgao.")

# --- B. CRIAR DIMENSÃO TEMPO (dim_tempo) ---
print("[INFO] Criando dim_tempo...")
df_dim_tempo = df_silver.select("ano", "mes").distinct() \
    .withColumn("data_ref", to_date(col("ano").cast("string"), "yyyy")) \
    .withColumn("semestre", (col("mes") > 6).cast("int") + 1) \
    .orderBy("ano", "mes")

save_delta_table(df_dim_tempo, GLUE_DATABASE_GOLD, "dim_tempo", PATH_GOLD_DIM_TEMPO)

# --- C. CRIAR DIMENSÃO GESTÃO (dim_gestao) ---
print("[INFO] Criando dim_gestao...")

col_cd = "cd_gestao"
col_nm = "nm_gestao"

if col_cd in df_silver.columns and col_nm in df_silver.columns:
    df_dim_gestao = df_silver.select(
        col(col_cd).alias("id_gestao"),
        col(col_nm).alias("nome_gestao")
    ).distinct().orderBy("id_gestao")
    
    save_delta_table(df_dim_gestao, GLUE_DATABASE_GOLD, "dim_gestao", PATH_GOLD_DIM_GESTAO)
else:
    print(f"[AVISO] Colunas ({col_cd}, {col_nm}) não encontradas. Pulando dim_gestao.")

# --- D. CRIAR DIMENSÃO UNIDADE GESTORA (dim_unidade_gestora) ---
print("[INFO] Criando dim_unidade_gestora...")

col_cd = "cd_unidade_gestora"
col_nm = "nm_unidade_gestora"

if col_cd in df_silver.columns and col_nm in df_silver.columns:
    df_dim_unidade_gestora = df_silver.select(
        col(col_cd).alias("id_unidade_gestora"),
        col(col_nm).alias("nome_unidade_gestora")
    ).distinct().orderBy("id_unidade_gestora")
    
    save_delta_table(df_dim_unidade_gestora, GLUE_DATABASE_GOLD, "dim_unidade_gestora", PATH_GOLD_DIM_UNIDADE_GESTORA)
else:
    print(f"[AVISO] Colunas ({col_cd}, {col_nm}) não encontradas. Pulando dim_unidade_gestora.")

# --- E. CRIAR DIMENSÃO UNIDADE ORÇAMENTÁRIA (dim_unidade_orcamentaria) ---
print("[INFO] Criando dim_unidade_orcamentaria...")

col_cd = "cd_unidade_orcamentaria"
col_nm = "nm_unidade_orcamentaria"

if col_cd in df_silver.columns and col_nm in df_silver.columns:
    df_dim_unidade_orcamentaria = df_silver.select(
        col(col_cd).alias("id_unidade_orcamentaria"),
        col(col_nm).alias("nome_unidade_orcamentaria")
    ).distinct().orderBy("id_unidade_orcamentaria")
    
    save_delta_table(df_dim_unidade_orcamentaria, GLUE_DATABASE_GOLD, "dim_unidade_orcamentaria", PATH_GOLD_DIM_UNIDADE_ORCAMENTARIA)
else:
    print(f"[AVISO] Colunas ({col_cd}, {col_nm}) não encontradas. Pulando dim_unidade_orcamentaria.")

# --- F. CRIAR TABELA FATO (ft_despesas) ---
print("[INFO] Criando ft_despesas...")

# Procura colunas de valor
cols_valor = [c for c in df_silver.columns if c.startswith("vl_")]

if cols_valor:
    # 1. Chaves de Tempo
    cols_fato = [col("ano"), col("mes")]
    
    # 2. Chaves das Dimensões (Se existirem na Silver, trazemos renomeadas para bater com a Dimensão)
    if "cd_orgao_superior" in df_silver.columns:
        cols_fato.append(col("cd_orgao_superior").alias("id_orgao"))
        
    if "cd_gestao" in df_silver.columns:
        cols_fato.append(col("cd_gestao").alias("id_gestao"))
        
    if "cd_unidade_gestora" in df_silver.columns:
        cols_fato.append(col("cd_unidade_gestora").alias("id_unidade_gestora"))
        
    if "cd_unidade_orcamentaria" in df_silver.columns:
        cols_fato.append(col("cd_unidade_orcamentaria").alias("id_unidade_orcamentaria"))
    
    # 3. Métricas (Valores)
    for c_val in cols_valor:
        cols_fato.append(col(c_val))
        
    # 4. Auditoria
    cols_fato.append(current_timestamp().alias("dt_carga"))

    df_fact = df_silver.select(*cols_fato)
    
    save_delta_table(df_fact, GLUE_DATABASE_GOLD, "ft_despesas", PATH_GOLD_FT_DESPESAS, partition_cols=["ano", "mes"])
else:
    print("[ERRO] Nenhuma coluna de valor (vl_*) encontrada para criar a Fato.")

job.commit()

# ============================================================================
# 5. LIMPEZA FINAL
# ============================================================================
print("[INFO] Executando limpeza Gold...")
delete_all_folder_markers_recursive(BUCKET_NAME, "gold")
print("[INFO] Job finalizado.")