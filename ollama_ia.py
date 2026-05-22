import os
import json
import re
import pandas as pd
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ==========================================
# CARREGA VARIÁVEIS
# ==========================================

load_dotenv()

DB_URI = os.getenv("DB_URI")

# ==========================================
# CONEXÃO BANCO
# ==========================================

engine = create_engine(DB_URI)

# ==========================================
# CONFIG OLLAMA
# ==========================================

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1"

# ==========================================
# BUSCA PROPOSIÇÕES SEM IA
# ==========================================

query = """
SELECT id, ementa
FROM fato_proposicoes
WHERE resumo_llm IS NULL
LIMIT 10
"""

df = pd.read_sql(query, engine)

print(f"\n{len(df)} proposições encontradas.\n")

# ==========================================
# PROCESSAMENTO IA (OLLAMA)
# ==========================================

for index, row in df.iterrows():

    id_proposicao = row["id"]
    ementa = row["ementa"]

    print(f"\nProcessando ID {id_proposicao}")

    # ==========================================
    # PROMPT COM TEMAS FIXOS
    # ==========================================

    prompt = f"""
Você é um classificador de textos legislativos.

Classifique o texto em APENAS UM destes temas:

EDUCAÇÃO
SAÚDE
MEIO AMBIENTE
ENERGIA
TRANSPORTE
DIREITO E JUSTIÇA
ECONOMIA E FINANÇAS
ADMINISTRAÇÃO PÚBLICA
SEGURANÇA
OUTROS

Responda APENAS com JSON válido:

{{
  "tema": "um dos temas acima",
  "resumo": "resumo curto da proposição em até 2 linhas"
}}

Texto:
{ementa}
"""

    try:
        # ==========================================
        # CHAMADA OLLAMA
        # ==========================================

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
        )

        resposta = response.json()["message"]["content"]

        print("\nRESPOSTA IA:\n", resposta)

        # ==========================================
        # EXTRAÇÃO ROBUSTA DE JSON
        # ==========================================

        try:
            match = re.search(r"\{.*\}", resposta, re.DOTALL)

            if match:
                json_str = match.group(0)
                data = json.loads(json_str)

                tema = data.get("tema", "")
                resumo = data.get("resumo", "")
            else:
                print("⚠ Nenhum JSON encontrado")
                tema = ""
                resumo = ""

        except Exception as e:
            print("Erro ao converter JSON:", e)
            print("Resposta original:", resposta)

            tema = ""
            resumo = ""

        # ==========================================
        # DEBUG FINAL
        # ==========================================

        print("TEMA FINAL:", tema)
        print("RESUMO FINAL:", resumo)

        # ==========================================
        # UPDATE BANCO
        # ==========================================

        with engine.begin() as conn:

            conn.execute(
                text("""
                    UPDATE fato_proposicoes
                    SET tema_llm = :tema,
                        resumo_llm = :resumo
                    WHERE id = :id
                """),
                {
                    "tema": tema,
                    "resumo": resumo,
                    "id": int(id_proposicao)
                }
            )

        print("✔ Salvo no banco.")

    except Exception as e:
        print(f"Erro geral: {e}")

print("\n🚀 FINALIZADO")