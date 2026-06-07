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
engine = create_engine(DB_URI)

# ==========================================
# CONFIG OLLAMA
# ==========================================
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1"

# ==========================================
# BUSCA PROPOSIÇÕES SEM TEMA
# ==========================================
# Ajustado para buscar na coluna 'tema' que já existe no seu banco
query = """
SELECT id, ementa
FROM fato_proposicoes
WHERE tema IS NULL OR tema = ''
LIMIT 10
"""

df = pd.read_sql(query, engine)
print(f"\n{len(df)} proposições encontradas para classificar.\n")

# ==========================================
# PROCESSAMENTO IA (OLLAMA)
# ==========================================
for index, row in df.iterrows():
    id_proposicao = row["id"]
    ementa = row["ementa"]

    print(f"\nProcessando ID {id_proposicao}")

    # Regra: Se "Sem ementa", pula IA e define tema
    if ementa == "Sem ementa":
        tema = "Sem tema"
        print("⚠️ Ementa vazia, definindo como 'Sem tema'")
    else:
        # Prompt focado APENAS no tema
        prompt = f"""
        Você é um classificador de textos legislativos.
        Classifique o texto em APENAS UM destes temas:
        EDUCAÇÃO, SAÚDE, MEIO AMBIENTE, ENERGIA, TRANSPORTE, DIREITO E JUSTIÇA, ECONOMIA E FINANÇAS, ADMINISTRAÇÃO PÚBLICA, SEGURANÇA, OUTROS.

        Responda APENAS com JSON: {{"tema": "TEMA_ESCOLHIDO"}}

        Texto: {ementa}
        """

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                }
            )
            resposta = response.json()["message"]["content"]
            
            # Extração robusta do JSON
            match = re.search(r"\{.*\}", resposta, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                tema = data.get("tema", "OUTROS")
            else:
                tema = "OUTROS"
        except Exception as e:
            print(f"Erro na IA: {e}")
            tema = "OUTROS"

    # ==========================================
    # UPDATE BANCO (Atualizando a coluna 'tema')
    # ==========================================
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE fato_proposicoes
                SET tema = :tema
                WHERE id = :id
            """),
            {"tema": tema, "id": int(id_proposicao)}
        )
    print(f"✔ Tema '{tema}' salvo para ID {id_proposicao}.")

print("\n🚀 FINALIZADO")