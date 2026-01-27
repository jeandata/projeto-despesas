import boto3
import time
import json

ATHENA_DATABASE = 'gold_db'
S3_OUTPUT = 's3://db-despesas/athena/'

athena_client = boto3.client('athena')

def lambda_handler(event, context):
    print(f"📥 EVENTO RECEBIDO:\n{json.dumps(event, indent=2)}")
    
    try:
        # Extrai metadados
        action_group = event.get('actionGroup', '')
        function_name = event.get('function', '')
        
        # Extrai a query SQL do parâmetro
        query_sql = None
        parameters = event.get('parameters', [])
        
        for param in parameters:
            if param.get('name') == 'query':
                query_sql = param.get('value', '')
                break
        
        if not query_sql:
            raise ValueError("❌ Parâmetro 'query' não encontrado")
        
        print(f"🔍 SQL: {query_sql}")
        
        # Executa no Athena
        query_id = athena_client.start_query_execution(
            QueryString=query_sql.strip(),
            QueryExecutionContext={'Database': ATHENA_DATABASE},
            ResultConfiguration={'OutputLocation': S3_OUTPUT}
        )['QueryExecutionId']
        
        print(f"⏳ Query ID: {query_id}")
        
        # Aguarda conclusão (máx 30s)
        for _ in range(30):
            response = athena_client.get_query_execution(QueryExecutionId=query_id)
            status = response['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'CANCELLED']:
                reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Desconhecido')
                raise Exception(f"Athena falhou: {reason}")
            
            time.sleep(1)
        
        # Processa resultado
        results = athena_client.get_query_results(QueryExecutionId=query_id)
        rows = results['ResultSet']['Rows']
        
        if len(rows) > 1:
            valores = [col.get('VarCharValue', '') for col in rows[1]['Data']]
            resultado = valores[0] if len(valores) == 1 else ' | '.join(valores)
            
            # Formata como moeda se for número
            try:
                num = float(resultado.replace(',', ''))
                resultado = f"R$ {num:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
            except:
                pass
            
            mensagem = f"✅ Resultado encontrado: {resultado}"
        else:
            mensagem = "ℹ️ A consulta não retornou dados"
        
        print(f"📤 RESPOSTA: {mensagem}")
        
    except Exception as e:
        mensagem = f"❌ Erro: {str(e)}"
        print(f"🚨 ERRO: {e}")
    
    # FORMATO CORRETO - Estrutura simplificada
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': action_group,
            'function': function_name,
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': mensagem
                    }
                }
            }
        }
    }