import streamlit as st
import boto3
import uuid

# Configurações do Agente (Pegue no Console do Bedrock)
AGENT_ID = "FTADGEDRB9" 
AGENT_ALIAS_ID = "TSTALIASID" # Use o ID do seu Alias
REGION = "us-east-2"

st.set_page_config(page_title="IA de Despesas Públicas", page_icon="📊")
st.title("📊 Realize sua consulta sobre as despesas públicas")

# Inicializa o histórico de chat na sessão do navegador
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Exibe as mensagens do histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Campo de entrada do usuário
if prompt := st.chat_input("Ex: Qual o valor total pago em 2025?"):
    # Adiciona pergunta ao chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Chamada ao Bedrock Agent
    with st.chat_message("assistant"):
        with st.spinner("Consultando Athena..."):
            try:
                client = boto3.client("bedrock-agent-runtime", region_name=REGION)
                
                response = client.invoke_agent(
                    agentId=AGENT_ID,
                    agentAliasId=AGENT_ALIAS_ID,
                    sessionId=st.session_state.session_id,
                    inputText=prompt,
                )

                # Processa a resposta em stream
                full_response = ""
                for event in response.get("completion"):
                    chunk = event.get("chunk", {})
                    if chunk:
                        full_response += chunk.get("bytes").decode("utf-8")
                
                st.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"Erro na conexão: {e}")