################################################################################
# CARGA DE DADOS PARA O BANCO DE DADOS
#
# Objetivo:
# Ler os arquivos JSON gerados pela etapa de extração da API da Câmara dos
# Deputados e carregar os dados para as tabelas dimensionais e factuais
# do banco de dados.
#
# Funcionamento:
# - Conecta ao banco utilizando a variável DB_URI.
# - Lê os arquivos JSON armazenados localmente.
# - Converte os dados para DataFrames do Pandas.
# - Seleciona apenas as colunas necessárias para cada tabela.
# - Verifica quais registros já existem no banco.
# - Insere somente novos registros, evitando duplicidades.
# - Atualiza as tabelas de dimensões e fatos.
#
# Tabelas alimentadas:
#
# Dimensões:
# - dim_deputados
# - dim_partidos
#
# Fatos:
# - fato_proposicoes
# - fato_votacoes
#
# Arquivos de origem:
# - data/raw/deputados.json
# - data/raw/partidos.json
# - data/raw/proposicoes.json
# - data/raw/votacoes.json
#
# Aplicação:
# Etapa de transformação e carga (ETL) responsável por popular o banco de
# dados utilizado em análises, dashboards e projetos de Business Intelligence.
################################################################################

import os
import json
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Cria a conexão com o banco de dados
engine = create_engine(os.getenv("DB_URI"))


def carregar_dados_json(caminho_arquivo):
    """
    Lê um arquivo JSON e converte seu conteúdo para um DataFrame.
    """

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        conteudo = json.load(f)

    # Trata arquivos que possuem a estrutura {"dados": [...]}
    if isinstance(conteudo, dict) and "dados" in conteudo:
        return pd.json_normalize(conteudo, record_path=["dados"])

    # Trata arquivos contendo lista simples de registros
    return pd.json_normalize(conteudo)


def processar_dimensoes(engine):
    """
    Realiza a carga das tabelas dimensionais.
    """

    print("\n--- PROCESSANDO DIMENSÕES ---")

    # =====================================================
    # DIM_DEPUTADOS
    # =====================================================

    caminho_dep = "data/raw/deputados.json"

    if os.path.exists(caminho_dep):

        # Carrega os dados do arquivo JSON
        df = carregar_dados_json(caminho_dep)

        # Padroniza o ID como texto
        df["id"] = df["id"].astype(str)

        # Seleciona apenas as colunas utilizadas na dimensão
        colunas_permitidas = [
            "id",
            "nome",
            "siglaPartido",
            "siglaUf",
            "idLegislatura",
            "urlFoto"
        ]

        df_final = df[
            [c for c in colunas_permitidas if c in df.columns]
        ]

        # Verifica registros já existentes no banco
        try:
            ids_db = pd.read_sql(
                "SELECT id::text FROM dim_deputados",
                engine
            )["id"]

            df_final = df_final[
                ~df_final["id"].isin(ids_db)
            ]

        except:
            pass

        # Insere somente registros novos
        if not df_final.empty:

            df_final.to_sql(
                "dim_deputados",
                engine,
                if_exists="append",
                index=False
            )

            print(f"✔ {len(df_final)} deputados inseridos.")

    # =====================================================
    # DIM_PARTIDOS
    # =====================================================

    caminho_part = "data/raw/partidos.json"

    if os.path.exists(caminho_part):

        # Carrega os dados do arquivo JSON
        df = carregar_dados_json(caminho_part)

        # Padroniza o ID como texto
        df["id"] = df["id"].astype(str)

        # Seleciona apenas as colunas utilizadas na dimensão
        colunas_permitidas = [
            "id",
            "sigla",
            "nome",
            "uri"
        ]

        df_final = df[
            [c for c in colunas_permitidas if c in df.columns]
        ]

        # Verifica registros já existentes
        try:
            ids_db = pd.read_sql(
                "SELECT id::text FROM dim_partidos",
                engine
            )["id"]

            df_final = df_final[
                ~df_final["id"].isin(ids_db)
            ]

        except:
            pass

        # Insere somente novos registros
        if not df_final.empty:

            df_final.to_sql(
                "dim_partidos",
                engine,
                if_exists="append",
                index=False
            )

            print(f"✔ {len(df_final)} partidos inseridos.")


def processar_fatos(engine):
    """
    Realiza a carga das tabelas factuais.
    """

    print("\n--- PROCESSANDO FATOS ---")

    # =====================================================
    # FATO_PROPOSICOES
    # =====================================================

    caminho_prop = "data/raw/proposicoes.json"

    if os.path.exists(caminho_prop):

        # Carrega os dados do arquivo JSON
        df = carregar_dados_json(caminho_prop)

        # Padroniza o ID como texto
        df["id"] = df["id"].astype(str)

        # Seleciona as colunas necessárias
        colunas_permitidas = [
            "id",
            "uri",
            "siglaTipo",
            "codTipo",
            "numero",
            "ano",
            "ementa",
            "dataApresentacao"
        ]

        df_final = df[
            [c for c in colunas_permitidas if c in df.columns]
        ].copy()

        # -----------------------------------------------
        # TRATAMENTO: ementa vazia → "Sem ementa"
        # -----------------------------------------------
        if "ementa" in df_final.columns:
            df_final["ementa"] = (
                df_final["ementa"]
                .fillna("")
                .str.strip()
                .replace("", "Sem ementa")
            )

        # -----------------------------------------------
        # TRATAMENTO: ano vazio → extrai de dataApresentacao
        # -----------------------------------------------
        if "ano" in df_final.columns and "dataApresentacao" in df_final.columns:
            ano_num = pd.to_numeric(df_final["ano"], errors="coerce")
            mask_sem_ano = df_final["ano"].isna() | (df_final["ano"].astype(str).str.strip() == "") | (ano_num == 0)
            df_final.loc[mask_sem_ano, "ano"] = (
                pd.to_datetime(df_final.loc[mask_sem_ano, "dataApresentacao"], errors="coerce")
                .dt.year
            )

        # Verifica registros já existentes
        try:
            ids_db = pd.read_sql(
                "SELECT id::text FROM fato_proposicoes",
                engine
            )["id"]

            df_final = df_final[
                ~df_final["id"].isin(ids_db)
            ]

        except:
            pass

        # Insere somente novos registros
        if not df_final.empty:

            df_final.to_sql(
                "fato_proposicoes",
                engine,
                if_exists="append",
                index=False
            )

            print(f"✔ {len(df_final)} proposições inseridas.")

    # =====================================================
    # FATO_VOTACOES
    # =====================================================

    caminho_vot = "data/raw/votacoes.json"

    if os.path.exists(caminho_vot):

        # Carrega os dados do arquivo JSON
        df = carregar_dados_json(caminho_vot)

        # Padroniza o ID como texto
        df["id"] = df["id"].astype(str)

        # Seleciona as colunas necessárias
        colunas_permitidas = [
            "id",
            "uri",
            "data",
            "dataHoraRegistro",
            "siglaOrgao",
            "uriOrgao",
            "uriEvento",
            "proposicaoObjeto",
            "uriProposicaoObjeto",
            "descricao",
            "aprovacao"
        ]

        df_final = df[
            [c for c in colunas_permitidas if c in df.columns]
        ]

        # Verifica registros já existentes
        try:
            ids_db = pd.read_sql(
                "SELECT id::text FROM fato_votacoes",
                engine
            )["id"]

            df_final = df_final[
                ~df_final["id"].isin(ids_db)
            ]

        except:
            pass

        # Insere somente novos registros
        if not df_final.empty:

            df_final.to_sql(
                "fato_votacoes",
                engine,
                if_exists="append",
                index=False
            )

            print(f"✔ {len(df_final)} votações inseridas.")


if __name__ == "__main__":

    try:

        # Executa a carga das dimensões
        processar_dimensoes(engine)

        # Executa a carga das tabelas fato
        processar_fatos(engine)

        print("\n✅ PIPELINE FINALIZADO COM SUCESSO!")

    except Exception as e:

        print(f"\n❌ ERRO:\n{e}")