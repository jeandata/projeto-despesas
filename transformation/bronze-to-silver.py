import sys
import unicodedata
import re
import datetime
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
# Imports essenciais para limpeza de texto e moeda
from pyspark.sql.functions import col, split, current_timestamp, regexp_replace, trim
from pyspark.sql.types import IntegerType, DecimalType
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf

# ============================================================================
# FUNÇÕES
# ============================================================================

def normalize_column_name(name):
    name = name.lower().strip().replace(" ", "_")
    name = "".join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9_]', '', name)

def get_brasilia_date():
    return datetime.datetime.now() - datetime.timedelta(hours=3)

def find_date_column(columns):
    # Tenta achar a coluna de data
    target = "ano_e_mes_do_lancamento"
    if target in columns: return target
    patterns = [lambda c: "ano" in c and "mes" in c and "lancamento" in c,
                lambda c: "ano" in c and "mes" in c]
    for pattern in patterns:
        matches = [c for c in columns if pattern(c)]
        if matches: return matches[0]
    return columns[0] 

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
# CONFIGURAÇÃO
# ============================================================================

BUCKET_NAME = "db-despesas"
GLUE_DATABASE = "silver_db" 
TABLE_NAME = "tb_stg_governo_gastos"

BRONZE_BASE = f"s3://{BUCKET_NAME}/bronze/stg_governo_gastos/public-stg_governo_gastos"
SILVER_PATH = f"s3://{BUCKET_NAME}/silver/stg_governo_gastos"
WAREHOUSE_ROOT = f"s3://{BUCKET_NAME}/silver"
DATABASE_LOCATION = f"{WAREHOUSE_ROOT}/{GLUE_DATABASE}.db"

conf = SparkConf()
conf.set("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
conf.set("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
conf.set("spark.sql.adaptive.enabled", "true")
conf.set("spark.hadoop.fs.s3.metadata.type", "no_metadata") 
conf.set("spark.sql.warehouse.dir", WAREHOUSE_ROOT)

spark = SparkSession.builder.config(conf=conf).getOrCreate()
sc = spark.sparkContext
glueContext = GlueContext(sc)
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

ensure_database_exists(GLUE_DATABASE, DATABASE_LOCATION)

# ============================================================================
# EXECUÇÃO DO JOB
# ============================================================================

data_ref = get_brasilia_date()
ano = data_ref.strftime('%Y')
mes = data_ref.strftime('%m')
dia = 15

path_bronze = f"{BRONZE_BASE}/year={ano}/month={mes}/day={dia}/"
print(f"[INFO] Lendo: {path_bronze}")

try:
    df = spark.read.parquet(path_bronze)
    
    # 1. Normalização dos Nomes
    for c in df.columns:
        clean = normalize_column_name(c)
        if c != clean: df = df.withColumnRenamed(c, clean)

    # 2. Criação de Colunas Auxiliares de Data (Mesmo sem particionar, é bom ter)
    try:
        col_data = find_date_column(df.columns)
        df = df.withColumn("ano", split(col(col_data), "/").getItem(0).cast(IntegerType())) \
               .withColumn("mes", split(col(col_data), "/").getItem(1).cast(IntegerType()))
    except:
        print("[AVISO] Não foi possível extrair ano/mês. Seguindo sem essas colunas.")

    df = df.withColumn("dt_processamento", current_timestamp())

    # 3. Tipagem e CORREÇÃO DE MOEDA (R$ 1.500,00 -> 1500.00)
    final_cols = []
    for c in df.columns:
        # Padroniza abreviações
        n = c.replace("codigo", "cd").replace("nome", "nm").replace("valor", "vl")
        n = re.sub(r'_+', '_', n).strip('_')
        
        if n.startswith("vl_"):
            # LÓGICA DE OURO: Remove R$, Tira Ponto de Milhar, Troca Vírgula por Ponto
            col_tratada = regexp_replace(
                regexp_replace(
                    regexp_replace(trim(col(c)), "R\\$", ""), # Tira R$ e espaços
                    "\\.", "" # Tira ponto (separador de milhar brasileiro)
                ), 
                ",", "." # Troca vírgula por ponto (separador decimal americano)
            )
            final_cols.append(col_tratada.cast(DecimalType(18, 2)).alias(n))
            
        elif n.startswith("cd_"):
            final_cols.append(col(c).cast(IntegerType()).alias(n))
        else:
            final_cols.append(col(c).alias(n))
    
    df_silver = df.select(*final_cols)

    # 4. Escrita
    print(f"[INFO] Escrevendo Delta em: {SILVER_PATH}")
    
    df_silver.write \
        .format("delta") \
        .mode("overwrite") \
        .option("mergeSchema", "true") \
        .option("overwriteSchema", "false") \
        .save(SILVER_PATH) 
        
    print(f"[SUCESSO] Arquivos salvos.")

    # 5. Registro SQL
    spark.sql(f"DROP TABLE IF EXISTS {GLUE_DATABASE}.{TABLE_NAME}")
    
    sql_create = f"""
        CREATE TABLE {GLUE_DATABASE}.{TABLE_NAME}
        USING DELTA
        LOCATION '{SILVER_PATH}'
    """
    print(f"[INFO] Executando SQL: {sql_create}")
    spark.sql(sql_create)
    
    print(f"[SUCESSO] Tabela {GLUE_DATABASE}.{TABLE_NAME} registrada.")

except Exception as e:
    if "PATH_NOT_FOUND" in str(e): print("[AVISO] Caminho vazio ou não encontrado.")
    else: raise e

job.commit()
print("[INFO] Job finalizado.")