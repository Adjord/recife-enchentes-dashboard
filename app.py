import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta
import streamlit as st
import plotly.express as px

def get_data_api():
    """Busca os dados mais recentes da API e padroniza o nome da coluna."""
    url = "http://dados.recife.pe.gov.br/api/3/action/datastore_search?resource_id=7ccabb3f-1411-4770-aeab-ce151ed59223&limit=100"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            records = response.json()['result']['records']
            df = pd.DataFrame(records)
            
            # Padronização aqui:
            df.rename(columns={'Data-hora': 'data_hora'}, inplace=True)
            
            df['chuva_mm'] = df['Dados_completos'].apply(lambda x: json.loads(x).get('chuva', 0))
            df['data_hora'] = pd.to_datetime(df['data_hora'])
            return df[['Estação', 'data_hora', 'chuva_mm']]
    except Exception as e:
        st.error(f"Erro ao buscar API: {e}")
        return pd.DataFrame() 
    return pd.DataFrame()

def get_history():
    """Lê o histórico, padroniza a coluna e junta com o novo."""
    csv_path = 'historico_chuvas.csv'
    df_novo = get_data_api()
    
    if os.path.exists(csv_path):
        df_hist = pd.read_csv(csv_path)
        # Padronização aqui também, caso o CSV tenha sido salvo com outro nome:
        df_hist.rename(columns={'Data-hora': 'data_hora'}, inplace=True)
        
        df_hist['data_hora'] = pd.to_datetime(df_hist['data_hora'])
        
        # Junta o novo com o antigo e remove duplicatas
        df_full = pd.concat([df_hist, df_novo]).drop_duplicates(subset=['Estação', 'data_hora'])
    else:
        df_full = df_novo
        
    # Garante que o arquivo salvo tenha a coluna correta
    df_full.to_csv(csv_path, index=False)
    return df_full


st.set_page_config(page_title="Monitoramento Recife", layout="wide")

st.title("🌧️ Monitoramento de Chuvas - Recife")
st.write("Dados históricos e tempo real integrados.")

# Carrega os dados atualizados
df_completo = get_history()

# Filtro lateral
st.sidebar.header("Filtros")
periodo = st.sidebar.selectbox("Período de Visualização:", ['Últimas 24h', 'Histórico Completo'])

# Lógica de Filtro
if periodo == 'Últimas 24h':
    limite = datetime.now() - timedelta(hours=24)
    df_plot = df_completo[df_completo['data_hora'] > limite]
else:
    df_plot = df_completo

# Agrupamento para o gráfico (soma da chuva total por hora, para facilitar a visualização)
df_agrupado = df_plot.groupby(df_plot['data_hora'].dt.floor('H'))['chuva_mm'].sum().reset_index()

# Visualização
st.subheader(f"Precipitação - {periodo}")
fig = px.bar(df_agrupado, x='data_hora', y='chuva_mm', 
             labels={'chuva_mm': 'Chuva (mm)', 'data_hora': 'Hora/Data'},
             color_discrete_sequence=['#1f77b4'])
st.plotly_chart(fig, use_container_width=True)

st.write("### Dados Brutos")
st.dataframe(df_plot.sort_values(by='data_hora', ascending=False).head(10))
