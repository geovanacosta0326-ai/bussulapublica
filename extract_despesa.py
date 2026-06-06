################################################################################
# EXTRAÇÃO DE DESPESAS DOS DEPUTADOS FEDERAIS
#
# Objetivo:
# Consultar a API de Dados Abertos da Câmara dos Deputados e coletar as
# despesas parlamentares de todos os deputados referentes ao mês anterior.
#
# Funcionamento:
# - Identifica automaticamente o mês e ano anterior à execução.
# - Lê a lista de deputados previamente extraída.
# - Consulta a API de despesas para cada deputado.
# - Realiza paginação automática dos resultados.
# - Trata falhas temporárias da API (erro 504).
# - Normaliza os dados para um padrão compatível com o banco de dados.
# - Salva os resultados em arquivos JSON individuais.
# - Mantém um arquivo de controle para retomada em caso de interrupção.
#
# Arquivos de origem:
# - data/raw/deputados.json
#
# Arquivos gerados:
# - data/raw/despesas/ANO_MES/{id_deputado}.json
# - data/raw/despesas/ANO_MES/{id_deputado}_controle.json
#
# Aplicação:
# Etapa de extração (ETL) responsável pela coleta das despesas parlamentares
# para utilização em bancos de dados, dashboards, auditorias e análises de
# gastos públicos.
################################################################################

import requests
import json
import os
import time
from datetime import datetime, timedelta

# =========================================================
# CONFIGURAÇÃO DO PERÍODO DE EXTRAÇÃO
# =========================================================

# Obtém a data atual do sistema
agora = datetime.now()

# Determina o primeiro dia do mês atual
primeiro_dia_mes_atual = agora.replace(day=1)

# Calcula automaticamente o último dia do mês anterior
mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)

# Define o período alvo para consulta das despesas
ANO_ALVO = mes_anterior.year
MES_ALVO = mes_anterior.month

# Define a pasta onde os arquivos serão armazenados
PASTA_DESTINO = f"data/raw/despesas/{ANO_ALVO}_{MES_ALVO}"

# Cria a estrutura de diretórios caso ela não exista
os.makedirs(PASTA_DESTINO, exist_ok=True)


def baixar_despesas_deputado(deputado_id):
    """
    Consulta todas as despesas de um deputado para o período informado,
    realiza a paginação automática e salva os dados em JSON.
    """

    # Monta a URL da API para o deputado informado
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputado_id}/despesas"

    # Arquivo que armazenará os dados do deputado
    caminho_arquivo = f"{PASTA_DESTINO}/{deputado_id}.json"

    # Arquivo utilizado para controle de retomada da execução
    caminho_controle = f"{PASTA_DESTINO}/{deputado_id}_controle.json"

    # =====================================================
    # RECUPERA DADOS JÁ EXISTENTES
    # =====================================================

    todos_dados = []

    # Caso já exista um arquivo salvo, carrega os dados anteriores
    if os.path.exists(caminho_arquivo):
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                todos_dados = json.load(f)

        except (json.JSONDecodeError, IOError):
            todos_dados = []

    # =====================================================
    # RECUPERA A ÚLTIMA PÁGINA PROCESSADA
    # =====================================================

    pagina = 1

    if os.path.exists(caminho_controle):
        try:
            with open(caminho_controle, "r", encoding="utf-8") as f:
                pagina = json.load(f).get("ultima_pagina", 1)

        except:
            pagina = 1

    # =====================================================
    # PROCESSA TODAS AS PÁGINAS DA API
    # =====================================================

    while True:

        params = {
            "pagina": pagina,
            "itens": 100,
            "ano": ANO_ALVO,
            "mes": MES_ALVO
        }

        try:

            # Realiza a consulta à API
            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            # Em caso de timeout da API, aguarda e tenta novamente
            if response.status_code == 504:
                time.sleep(10)
                continue

            # Encerra se a API retornar erro
            if response.status_code != 200:
                break

            # Obtém os registros retornados
            registros = response.json().get("dados", [])

            # Encerra quando não houver mais páginas
            if not registros:
                break

            # Adiciona os registros à lista principal
            todos_dados.extend(registros)

            print(
                f"  Deputado {deputado_id} - "
                f"Pág {pagina} | +{len(registros)} itens"
            )

            # Avança para a próxima página
            pagina += 1

            # Pequena pausa para respeitar o limite da API
            time.sleep(0.5)

        except Exception as e:

            print(
                f"  Erro ao processar deputado "
                f"{deputado_id}: {e}"
            )

            break

    # =====================================================
    # NORMALIZAÇÃO DOS DADOS
    # =====================================================

    # Padroniza os nomes das colunas em minúsculo
    # e adiciona o ID do deputado em cada registro

    dados_limpos = []

    for item in todos_dados:

        item_limpo = {
            k.lower(): v
            for k, v in item.items()
        }

        item_limpo["deputado_id"] = deputado_id

        dados_limpos.append(item_limpo)

    # =====================================================
    # SALVAMENTO DOS DADOS
    # =====================================================

    # Salva os dados coletados
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(
            dados_limpos,
            f,
            ensure_ascii=False,
            indent=4
        )

    # Salva a última página processada
    with open(caminho_controle, "w", encoding="utf-8") as f:
        json.dump(
            {"ultima_pagina": pagina},
            f,
            ensure_ascii=False,
            indent=4
        )


if __name__ == "__main__":

    print(
        f"🚀 Iniciando extração de despesas "
        f"para {MES_ALVO}/{ANO_ALVO}"
    )

    # =====================================================
    # VERIFICA A EXISTÊNCIA DA BASE DE DEPUTADOS
    # =====================================================

    if not os.path.exists("data/raw/deputados.json"):

        print(
            "❌ Erro: Arquivo "
            "'data/raw/deputados.json' não encontrado."
        )

    else:

        # Carrega a lista de deputados
        with open(
            "data/raw/deputados.json",
            "r",
            encoding="utf-8"
        ) as f:

            deputados = json.load(f)

        # Processa cada deputado individualmente
        for i, dep in enumerate(deputados, 1):

            dep_id = dep.get("id")

            if dep_id:

                print(
                    f"[{i}/{len(deputados)}] "
                    f"Processando ID: {dep_id}"
                )

                baixar_despesas_deputado(dep_id)

    print(
        f"\n✅ Pipeline concluído com sucesso."
        f" Dados salvos em: {PASTA_DESTINO}"
    )