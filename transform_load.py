import os
import json
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# =========================================================
# CARREGA VARIÁVEIS DE AMBIENTE
# =========================================================

load_dotenv()

DB_URI = os.getenv("DB_URI")

# =========================================================
# CONEXÃO COM SUPABASE
# =========================================================

engine = create_engine(DB_URI)

# =========================================================
# FUNÇÃO PARA LER JSON
# =========================================================

def carregar_dados_json(caminho_arquivo):
    """
    Lê JSON com ou sem chave 'dados'
    """

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        conteudo = json.load(f)

    # quando a API retorna {"dados": [...]}
    if isinstance(conteudo, dict) and "dados" in conteudo:
        return pd.json_normalize(conteudo, record_path=["dados"])

    # quando já vem lista direta
    return pd.json_normalize(conteudo)

# =========================================================
# PROCESSAR DIMENSÕES
# =========================================================

def processar_dimensoes(engine):

    print("\n--- PROCESSANDO DIMENSÕES ---")

    # =====================================================
    # DIM_DEPUTADOS
    # =====================================================

    caminho_dep = "data/raw/deputados.json"

    if os.path.exists(caminho_dep):

        df_dep = carregar_dados_json(caminho_dep)

        df_dep = df_dep.drop_duplicates(subset=["id"])
        df_dep = df_dep.dropna(subset=["id", "nome"])

        colunas_dep = [
            "id",
            "nome",
            "siglaPartido",
            "siglaUf",
            "idLegislatura",
            "urlFoto"
        ]

        colunas_existentes = [
            col for col in colunas_dep
            if col in df_dep.columns
        ]

        df_dep_final = df_dep[colunas_existentes]

        # remove ids já existentes
        try:
            ids_existentes = pd.read_sql(
                "SELECT id FROM dim_deputados",
                engine
            )

            df_dep_final = df_dep_final[
                ~df_dep_final["id"].isin(ids_existentes["id"])
            ]

        except:
            pass

        # insere apenas novos
        if not df_dep_final.empty:

            df_dep_final.to_sql(
                "dim_deputados",
                engine,
                if_exists="append",
                index=False
            )

        print(f"✔ {len(df_dep_final)} novos deputados inseridos.")

    else:
        print(f"❌ Arquivo não encontrado: {caminho_dep}")

    # =====================================================
    # DIM_PARTIDOS
    # =====================================================

    caminho_part = "data/raw/partidos.json"

    if os.path.exists(caminho_part):

        df_part = carregar_dados_json(caminho_part)

        df_part = df_part.drop_duplicates(subset=["id"])

        colunas_part = [
            "id",
            "sigla",
            "nome",
            "uri"
        ]

        colunas_existentes = [
            col for col in colunas_part
            if col in df_part.columns
        ]

        df_part_final = df_part[colunas_existentes]

        # remove ids já existentes
        try:
            ids_existentes = pd.read_sql(
                "SELECT id FROM dim_partidos",
                engine
            )

            df_part_final = df_part_final[
                ~df_part_final["id"].isin(ids_existentes["id"])
            ]

        except:
            pass

        # insere apenas novos
        if not df_part_final.empty:

            df_part_final.to_sql(
                "dim_partidos",
                engine,
                if_exists="append",
                index=False
            )

        print(f"✔ {len(df_part_final)} novos partidos inseridos.")

    else:
        print(f"❌ Arquivo não encontrado: {caminho_part}")

# =========================================================
# PROCESSAR FATOS
# =========================================================

def processar_fatos(engine):

    print("\n--- PROCESSANDO FATOS ---")

    # =====================================================
    # FATO_PROPOSICOES
    # =====================================================

    caminho_prop = "data/raw/proposicoes.json"

    if os.path.exists(caminho_prop):

        df_prop = carregar_dados_json(caminho_prop)

        df_prop = df_prop.drop_duplicates(subset=["id"])

        colunas_prop = [
            "id",
            "siglaTipo",
            "numero",
            "ano",
            "ementa"
        ]

        colunas_existentes = [
            col for col in colunas_prop
            if col in df_prop.columns
        ]

        df_prop_final = df_prop[colunas_existentes]

        # remove ids já existentes
        try:
            ids_existentes = pd.read_sql(
                "SELECT id FROM fato_proposicoes",
                engine
            )

            df_prop_final = df_prop_final[
                ~df_prop_final["id"].isin(ids_existentes["id"])
            ]

        except:
            pass

        # insere apenas novos
        if not df_prop_final.empty:

            df_prop_final.to_sql(
                "fato_proposicoes",
                engine,
                if_exists="append",
                index=False
            )

        print(f"✔ {len(df_prop_final)} novas proposições inseridas.")

    else:
        print(f"❌ Arquivo não encontrado: {caminho_prop}")

    # =====================================================
    # FATO_VOTACOES
    # =====================================================

    caminho_vot = "data/raw/votacoes.json"

    if os.path.exists(caminho_vot):

        df_vot = carregar_dados_json(caminho_vot)

        df_vot = df_vot.drop_duplicates(subset=["id"])

        colunas_vot = [
            "id",
            "data",
            "descricao"
        ]

        colunas_existentes = [
            col for col in colunas_vot
            if col in df_vot.columns
        ]

        df_vot_final = df_vot[colunas_existentes]

        # remove ids já existentes
        try:
            ids_existentes = pd.read_sql(
                "SELECT id FROM fato_votacoes",
                engine
            )

            df_vot_final = df_vot_final[
                ~df_vot_final["id"].isin(ids_existentes["id"])
            ]

        except:
            pass

        # insere apenas novos
        if not df_vot_final.empty:

            df_vot_final.to_sql(
                "fato_votacoes",
                engine,
                if_exists="append",
                index=False
            )

        print(f"✔ {len(df_vot_final)} novas votações inseridas.")

    else:
        print(f"❌ Arquivo não encontrado: {caminho_vot}")

# =========================================================
# EXECUÇÃO PRINCIPAL
# =========================================================

if __name__ == "__main__":

    try:

        print("🚀 Conectando ao Supabase...")

        processar_dimensoes(engine)

        processar_fatos(engine)

        print("\n✅ PIPELINE FINALIZADO SEM DUPLICAÇÕES")

    except Exception as e:

        print(f"\n❌ ERRO NO PIPELINE:\n{e}")