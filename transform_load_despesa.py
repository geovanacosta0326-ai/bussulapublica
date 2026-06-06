################################################################################
# CARGA DE DESPESAS PARLAMENTARES PARA O BANCO DE DADOS
#
# Objetivo:
# Ler os arquivos JSON gerados pela etapa de extração das despesas dos
# deputados federais e carregar os dados para a tabela "despesas"
# no banco de dados Supabase.
#
# Funcionamento:
# - Conecta ao banco utilizando a variável DB_URI.
# - Identifica os registros já existentes na tabela despesas.
# - Lê todos os arquivos JSON da pasta informada.
# - Converte os dados para DataFrames do Pandas.
# - Compara os registros pelo campo coddocumento.
# - Insere somente registros ainda não existentes no banco.
# - Registra todas as operações em log para acompanhamento.
#
# Tabela alimentada:
# - fato_despesas
#
# Arquivos de origem:
# - data/raw/despesas/ANO_MES/*.json
#
# Aplicação:
# Etapa de carga (Load) do processo ETL responsável por armazenar
# as despesas parlamentares no banco de dados para consultas,
# auditorias, relatórios e dashboards analíticos.
################################################################################

import pandas as pd
import os
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Configuração de Logs: Monitora o progresso com timestamps
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
engine = create_engine(os.getenv("DB_URI"))

# --- CÁLCULO AUTOMÁTICO DO MÊS ANTERIOR ---
hoje = datetime.now()
primeiro_dia_mes = hoje.replace(day=1)
mes_passado = primeiro_dia_mes - timedelta(days=1)

ANO_ALVO = mes_passado.year
MES_ALVO = mes_passado.month
PASTA_ALVO = f"data/raw/despesas/{ANO_ALVO}_{MES_ALVO}"

def limpar_dados(df):
    """Remove linhas vazias e duplicatas antes de enviar ao banco."""
    if 'coddocumento' in df.columns:
        df = df.dropna(subset=['coddocumento'])
        df = df.drop_duplicates(subset=['coddocumento'])
    return df

def carregar_para_supabase(caminho_pasta):
    """
    Processa arquivos JSON da pasta do mês anterior e realiza o upload 
    para o Supabase, filtrando apenas registros novos.
    """
    logging.info(f"Iniciando carga de dados na pasta: {caminho_pasta}")

    if not os.path.exists(caminho_pasta):
        logging.error(f"Pasta não encontrada: {caminho_pasta}")
        return

    # Obtém IDs existentes para evitar duplicatas
    try:
        ids_existentes = pd.read_sql("SELECT coddocumento FROM fato_despesas", engine)["coddocumento"].astype(str).tolist()
    except Exception:
        ids_existentes = []

    # Lista apenas arquivos .json dentro da pasta alvo
    arquivos = [f for f in os.listdir(caminho_pasta) if f.endswith(".json") and "_controle" not in f]
    
    for arquivo in arquivos:
        caminho_completo = os.path.join(caminho_pasta, arquivo)
        
        try:
            with open(caminho_completo, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception as e:
            logging.error(f"Erro ao ler arquivo {arquivo}: {e}")
            continue
        
        if not isinstance(dados, list) or len(dados) == 0:
            continue
        
        df = pd.DataFrame(dados)
        
        # --- LIMPEZA E SEGURANÇA ---
        df = limpar_dados(df)
        
        if "coddocumento" not in df.columns:
            logging.warning(f"Aviso: Arquivo {arquivo} ignorado (coluna 'coddocumento' ausente).")
            continue
        
        df["coddocumento"] = df["coddocumento"].astype(str)
        df_novos = df[~df["coddocumento"].isin(ids_existentes)]
        
        # Carga
        if not df_novos.empty:
            try:
                df_novos.to_sql("despesas", engine, if_exists="append", index=False)
                logging.info(f"Sucesso: {len(df_novos)} novos registros inseridos de {arquivo}")
            except Exception as e:
                logging.error(f"Erro crítico ao inserir dados do arquivo {arquivo}: {e}")
        else:
            logging.info(f"Sem novos dados em: {arquivo}")

# ------------------------------------------------------------------

if __name__ == "__main__":
    carregar_para_supabase(PASTA_ALVO)
    logging.info("--- Processo de carga finalizado ---")