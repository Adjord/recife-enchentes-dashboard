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
            registros = response.json()['result']['records']
            df = pd.DataFrame(registros)
            
            # Renomeação forçada imediata
            df.rename(columns={'Data-hora': 'data_hora'}, inplace=True)
            
            # Verifica se a coluna existe, se não, cria vazia para não quebrar
            if 'data_hora' not in df.columns:
                df['data_hora'] = pd.NaT
                
            df['chuva_mm'] = df['Dados_completos'].apply(lambda x: json.loads(x).get('chuva', 0))
            df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce')
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
# --- DEBUG: Ver o que a API está trazendo ---
st.write("### Debug: Dados Brutos da API")
df_debug = get_data_api()
st.write(f"Linhas retornadas pela API: {len(df_debug)}")
st.dataframe(df_debug.head())

# --- DEBUG: Ver o histórico carregado ---
st.write("### Debug: Histórico Carregado")
df_hist_debug = get_history()
st.write(f"Total de linhas no histórico total: {len(df_hist_debug)}")
st.write(f"Intervalo de datas: {df_hist_debug['data_hora'].min()} até {df_hist_debug['data_hora'].max()}")
# ---- fim debug ----

# 1. Carrega os dados atualizados
df_completo = get_history()

# --- VACINA: Forçar conversão de data aqui ---
# Mesmo que já tenhamos convertido antes, vamos garantir isso antes do gráfico
df_completo['data_hora'] = pd.to_datetime(df_completo['data_hora'], errors='coerce')
# Removemos linhas que não conseguiram ser convertidas (valores nulos ou erros)
df_completo = df_completo.dropna(subset=['data_hora'])
# ---------------------------------------------

# Filtro lateral
st.sidebar.header("Filtros")
periodo = st.sidebar.selectbox("Período de Visualização:", ['Últimas 24h', 'Histórico Completo'])

# Lógica de Filtro
if periodo == 'Últimas 24h':
    limite = datetime.now() - timedelta(hours=24)
    # Garante que 'limite' também é datetime para comparar com 'data_hora'
    df_plot = df_completo[df_completo['data_hora'] > pd.to_datetime(limite)]
else:
    df_plot = df_completo

# AGORA, com a garantia de que df_plot['data_hora'] é datetime, podemos agrupar
df_agrupado = df_plot.groupby(df_plot['data_hora'].dt.floor('h'))['chuva_mm'].sum().reset_index()

# Visualização
st.subheader(f"Precipitação - {periodo}")
fig = px.bar(df_agrupado, x='data_hora', y='chuva_mm', 
             labels={'chuva_mm': 'Chuva (mm)', 'data_hora': 'Hora/Data'},
             color_discrete_sequence=['#1f77b4'])
st.plotly_chart(fig, use_container_width=True)

st.write("### Dados Brutos")
st.dataframe(df_plot.sort_values(by='data_hora', ascending=False).head(10))
