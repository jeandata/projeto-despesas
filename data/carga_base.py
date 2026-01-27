import pandas as pd
import os
import glob
import datetime  # Faltava este!
from sqlalchemy import create_engine

# 1. Conexão (Dica: Use variáveis de ambiente no futuro!)
DB_URL = os.getenv('URLRENDER')
engine = create_engine(DB_URL)

def carregar_com_auditoria(caminho_pasta, engine):
    # BUSCANDO TODOS OS CSVS NA PASTA
    arquivos = glob.glob(os.path.join(caminho_pasta, "*.csv"))
    
    if not arquivos:
        print(f"Nenhum arquivo CSV encontrado em: {caminho_pasta}")
        return

    for arquivo_path in arquivos:
        nome_arquivo = os.path.basename(arquivo_path)
        print(f"🚀 Iniciando processamento de: {nome_arquivo}")
        
        try:
            # Lendo o dado bruto
            df = pd.read_csv(arquivo_path, sep=';', encoding='latin-1', low_memory=False)
            
            # 1. Padronização de nomes
            df.columns = [c.replace(' ', '_').lower().strip() for c in df.columns]
            
            # 2. Adição de Metadados
            df['load_timestamp'] = datetime.datetime.now()
            df['source_file_name'] = nome_arquivo
            
            # 3. Conversão de Tipos (Exemplo: Valor)
            # Dica: Verifique o nome exato da coluna no seu CSV (pode ser 'Valor Empenhado')
            coluna_valor = 'valor_empenhado'
            if coluna_valor in df.columns:
                df[coluna_valor] = df[coluna_valor].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)

            # 4. Carga Segura com performance (method='multi')
            df.to_sql('stg_governo_gastos', engine, if_exists='append', index=False, chunksize=1000)
            print(f"✅ Arquivo {nome_arquivo} carregado com sucesso.")
            
        except Exception as e:
            print(f"❌ Erro ao processar {nome_arquivo}: {e}")

carregar_com_auditoria(r'E:\Despesas', engine)