import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta
import streamlit as st
import plotly.express as px

def get_data_api():
    """Busca dados da API e garante que a coluna de data tem o nome 'data_hora'."""
    url = "http://dados.apac.pe.gov.br:41120/cemaden/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # O retorno é uma lista direta de dicionários, não um dicionário com 'result'
            dados = response.json()
            df = pd.DataFrame(dados)
            
            if df.empty:
                return pd.DataFrame(columns=['Estação', 'data_hora', 'chuva_mm'])
            
            # Renomeação forçada para padronizar
            df.rename(columns={'Data-hora': 'data_hora'}, inplace=True)
            
            # Tratamento da coluna 'Dados_completos' (que contém um JSON dentro da string)
            def extrair_chuva(x):
                try:
                    # x é uma string representando um JSON
                    dicionario = json.loads(x)
                    # Retorna o valor de 'chuva', convertendo para float
                    return float(dicionario.get('chuva', 0))
                except (ValueError, TypeError, json.JSONDecodeError):
                    return 0.0

            df['chuva_mm'] = df['Dados_completos'].apply(extrair_chuva)
            
            # Conversão segura de datas
            df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')
            
            # Retorna apenas as colunas necessárias
            return df[['Estação', 'data_hora', 'chuva_mm']]
    except Exception as e:
        st.error(f"Erro ao ler API: {e}")
    return pd.DataFrame(columns=['Estação', 'data_hora', 'chuva_mm'])

def get_history():
    """Lê o histórico, garante nomes de colunas e junta com o novo."""
    csv_path = 'historico_chuvas.csv'
    df_novo = get_data_api()
    
    # Lista de colunas esperadas
    cols_esperadas = ['Estação', 'data_hora', 'chuva_mm']
    
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        try:
            df_hist = pd.read_csv(csv_path)
            # Renomeação forçada para garantir padrão
            df_hist.rename(columns={'Data-hora': 'data_hora'}, inplace=True)
            
            # Garantir que df_hist tem as colunas certas
            for col in cols_esperadas:
                if col not in df_hist.columns:
                    df_hist[col] = None
            
            df_hist['data_hora'] = pd.to_datetime(df_hist['data_hora'], errors='coerce')
            
            # Junta tudo
            df_full = pd.concat([df_hist[cols_esperadas], df_novo[cols_esperadas]]).drop_duplicates()
        except Exception as e:
            st.warning(f"Erro ao processar CSV: {e}. Usando apenas dados da API.")
            df_full = df_novo
    else:
        df_full = df_novo
        
    # Salva o arquivo final com cabeçalhos padrão
    df_full.to_csv(csv_path, index=False)
    
    # Segurança extra: se mesmo assim não tiver a coluna, o app avisa em vez de quebrar
    if 'data_hora' not in df_full.columns:
        st.error("ERRO: Coluna 'data_hora' não encontrada. Verifique o CSV.")
        
    return df_full


st.set_page_config(page_title="Monitoramento Recife", layout="wide")

st.title("🌧️ Monitoramento de Chuvas - Recife")
st.write("Dados históricos e tempo real integrados.")

# 1. Carrega os dados atualizados
df_completo = get_history()

# --- VACINA: Forçar conversão de data aqui ---
# Mesmo que já tenhamos convertido antes, vamos garantir isso antes do gráfico
df_completo['data_hora'] = pd.to_datetime(df_completo['data_hora'], errors='coerce')
# Removemos linhas que não conseguiram ser convertidas (valores nulos ou erros)
df_completo = df_completo.dropna(subset=['data_hora'])
# ---------------------------------------------

df_plot = df_completo

# AGORA, com a garantia de que df_plot['data_hora'] é datetime, podemos agrupar
df_agrupado = df_plot.groupby(df_plot['data_hora'].dt.floor('h'))['chuva_mm'].sum().reset_index()

# Visualização
st.subheader(f"Precipitação")
fig = px.bar(df_agrupado, x='data_hora', y='chuva_mm', 
             labels={'chuva_mm': 'Chuva (mm)', 'data_hora': 'Hora/Data'},
             color_discrete_sequence=['#1f77b4'])
st.plotly_chart(fig, use_container_width=True)

st.write("### Dados Brutos")
st.dataframe(df_plot.sort_values(by='data_hora', ascending=False))
