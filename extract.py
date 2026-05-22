import requests
import json
import os
import time

# =========================================================
# SCRIPT DE EXTRAÇÃO - API CÂMARA DOS DEPUTADOS
# VERSÃO INCREMENTAL (SEM DUPLICAÇÃO)
# =========================================================

os.makedirs("data/raw", exist_ok=True)

DATA_INICIO = "2026-04-01"
DATA_FIM = "2026-04-30"


def baixar_endpoint(endpoint_name, params_adicionais=None, usar_datas=False):

    url = f"https://dadosabertos.camara.leg.br/api/v2/{endpoint_name}"
    caminho_arquivo = f"data/raw/{endpoint_name}.json"

    print(f"\n--- Iniciando extração incremental: {endpoint_name} ---")

    # ==========================================
    # 1. CARREGA DADOS EXISTENTES
    # ==========================================

    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            try:
                todos_dados = json.load(f)
            except:
                todos_dados = []
    else:
        todos_dados = []

    # cria set de IDs já existentes
    ids_existentes = set()

    for item in todos_dados:
        if isinstance(item, dict) and "id" in item:
            ids_existentes.add(item["id"])

    pagina = 1

    while True:

        print(f"Baixando {endpoint_name} - Página {pagina}...")

        params = {
            "pagina": pagina,
            "itens": 100
        }

        if usar_datas:
            params["dataInicio"] = DATA_INICIO
            params["dataFim"] = DATA_FIM

        if params_adicionais:
            params.update(params_adicionais)

        try:
            response = requests.get(url, params=params, timeout=30)

            # tratamento erro 504
            if response.status_code == 504:
                print("Erro 504 - tentando novamente...")
                time.sleep(10)
                continue

            if response.status_code != 200:
                print(f"Erro HTTP {response.status_code}")
                break

            dados = response.json()
            registros = dados.get("dados", [])

            if not registros:
                print(f"Fim da paginação: {endpoint_name}")
                break

            # ==========================================
            # 2. FILTRA APENAS NOVOS REGISTROS
            # ==========================================

            novos_registros = []

            for r in registros:
                rid = r.get("id") or r.get("uri")

                if rid not in ids_existentes:
                    novos_registros.append(r)
                    ids_existentes.add(rid)

            todos_dados.extend(novos_registros)

            print(f"+{len(novos_registros)} novos (Total: {len(todos_dados)})")

            pagina += 1
            time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão: {e}")
            time.sleep(5)

        except Exception as e:
            print(f"Erro inesperado: {e}")
            break

    # ==========================================
    # 3. SALVA JSON SEM DUPLICAR
    # ==========================================

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(todos_dados, f, ensure_ascii=False, indent=4)

    print(f"✔ Finalizado {endpoint_name} - Total final: {len(todos_dados)}")


# =========================================================
# EXECUÇÃO DO PIPELINE
# =========================================================

if __name__ == "__main__":

    # DIMENSÕES
    baixar_endpoint(
        "deputados",
        params_adicionais={
            "ordem": "ASC",
            "ordenarPor": "nome"
        }
    )

    baixar_endpoint(
        "partidos",
        params_adicionais={
            "ordem": "ASC",
            "ordenarPor": "sigla"
        }
    )

    # FATOS (COM DATA)
    baixar_endpoint("proposicoes", usar_datas=True)
    baixar_endpoint("votacoes", usar_datas=True)

    print("\n🚀 TODAS AS EXTRAÇÕES FORAM CONCLUÍDAS COM SUCESSO!")