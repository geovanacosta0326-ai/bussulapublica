"""
=============================================================================
classificar_temas.py
=============================================================================
Objetivo:
    Classificar automaticamente o tema de proposições legislativas que ainda
    não possuem tema definido, utilizando similaridade de cosseno entre
    embeddings vetoriais.

Estratégia (k-NN semântico):
    1. Para cada proposição SEM tema, busca as K proposições COM tema
       que possuem embedding mais próximo (menor distância de cosseno).
    2. O tema mais frequente entre os K vizinhos é atribuído à proposição.
    3. Apenas atribui o tema se a similaridade máxima atingir um limiar
       mínimo de confiança (LIMIAR_SIMILARIDADE), evitando classificações
       ruins em casos muito distantes semanticamente.

Dependências:
    - PostgreSQL com pgvector instalado e coluna `embedding` populada.
      Execute gerar_embeddings.py antes deste script.
    - Ollama rodando localmente com nomic-embed-text disponível.
    - Variável DB_URI definida no .env.

Uso:
    python classificar_temas.py

Parâmetros ajustáveis (seção de configuração abaixo):
    K_VIZINHOS          — quantos vizinhos considerar no voto (padrão: 3)
    LIMIAR_SIMILARIDADE — similaridade mínima para aceitar classificação (padrão: 0.75)
    MODO_SIMULACAO      — se True, apenas exibe o que seria feito sem salvar no banco

Autor: Radar Legislativo
=============================================================================
"""

import pandas as pd
from sqlalchemy import create_engine, text
from collections import Counter
import requests
import os
from dotenv import load_dotenv

# ── Configuração ──────────────────────────────────────────────────────────────
load_dotenv()
engine = create_engine(os.getenv("DB_URI"))

K_VIZINHOS          = 5      # Número de vizinhos mais próximos usados no voto
LIMIAR_SIMILARIDADE = 0.69   # Similaridade mínima (0 a 1) para aceitar o tema
MODO_SIMULACAO      = False  # True = só exibe, não salva no banco


# ── Funções auxiliares ────────────────────────────────────────────────────────

def get_embedding(texto: str) -> list[float]:
    """
    Gera o embedding de um texto via modelo nomic-embed-text no Ollama local.

    Args:
        texto: Texto a ser vetorizado (ementa da proposição).

    Returns:
        Lista de floats representando o vetor semântico do texto.
    """
    resposta = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": texto}
    )
    return resposta.json()["embedding"]


def buscar_vizinhos(vetor: list[float], k: int) -> pd.DataFrame:
    """
    Busca as K proposições com tema mais similares ao vetor fornecido,
    usando distância de cosseno via operador <=> do pgvector.

    Similaridade de cosseno = 1 - distância de cosseno.
    Quanto mais próximo de 1, mais similar semanticamente.

    Nota: o cast para vector é feito via CAST() e não com ::vector pois
    o SQLAlchemy interpreta os dois pontos como parâmetro nomeado.

    Args:
        vetor: Embedding da proposição sem tema.
        k:     Número de vizinhos a retornar.

    Returns:
        DataFrame com colunas: tema, similaridade.
    """
    query = text("""
        SELECT
            tema,
            1 - (embedding <=> CAST(:vetor AS vector)) AS similaridade
        FROM fato_proposicoes
        WHERE tema IS NOT NULL
          AND tema <> ''
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:vetor AS vector)
        LIMIT :k
    """)

    with engine.connect() as conn:
        resultado = conn.execute(query, {"vetor": str(vetor), "k": k})
        return pd.DataFrame(resultado.fetchall(), columns=["tema", "similaridade"])


def votar_tema(vizinhos: pd.DataFrame) -> tuple[str, float]:
    """
    Determina o tema vencedor por votação ponderada pela similaridade.

    Cada vizinho vota com peso igual à sua similaridade de cosseno,
    garantindo que vizinhos mais próximos tenham mais influência.

    Args:
        vizinhos: DataFrame com colunas tema e similaridade.

    Returns:
        Tupla (tema_vencedor, similaridade_maxima).
    """
    # Agrupa por tema somando as similaridades como peso de cada voto
    votos = vizinhos.groupby("tema")["similaridade"].sum()
    tema_vencedor = votos.idxmax()
    similaridade_max = vizinhos["similaridade"].max()
    return tema_vencedor, similaridade_max


# ── Execução principal ────────────────────────────────────────────────────────

# Busca todas as proposições sem tema que já possuem embedding gerado.
# Proposições sem embedding ou com "Sem ementa" são ignoradas:
# - sem embedding: rode gerar_embeddings.py antes
# - "Sem ementa": não há conteúdo semântico para comparar
df_pendentes = pd.read_sql("""
    SELECT id, ementa
    FROM fato_proposicoes
    WHERE (tema IS NULL OR tema = '')
      AND embedding IS NOT NULL
      AND ementa IS NOT NULL
      AND ementa <> 'Sem ementa'
""", engine)

total = len(df_pendentes)
print(f"Proposições sem tema para classificar: {total}")

if total == 0:
    print("Nenhuma proposição pendente. Encerrando.")
    exit()

if MODO_SIMULACAO:
    print("⚠️  MODO SIMULAÇÃO ativado — nenhuma alteração será salva no banco.\n")

# Contadores para o relatório final
classificadas  = 0
ignoradas      = 0
erros          = 0

for i, linha in df_pendentes.iterrows():
    try:
        # Gera o embedding da ementa da proposição sem tema
        vetor = get_embedding(linha["ementa"])

        # Busca os K vizinhos mais próximos que já têm tema
        vizinhos = buscar_vizinhos(vetor, K_VIZINHOS)

        if vizinhos.empty:
            print(f"  ⚠  ID {linha['id']}: nenhum vizinho com tema encontrado. Pulando.")
            ignoradas += 1
            continue

        # Determina o tema por votação ponderada
        tema_sugerido, similaridade = votar_tema(vizinhos)

        # Aplica o limiar de confiança — rejeita classificações incertas
        if similaridade < LIMIAR_SIMILARIDADE:
            print(f"  ⚠  ID {linha['id']}: similaridade {similaridade:.2f} abaixo do limiar "
                  f"({LIMIAR_SIMILARIDADE}). Tema '{tema_sugerido}' rejeitado.")
            ignoradas += 1
            continue

        print(f"  ✓ ID {linha['id']} → tema: '{tema_sugerido}' "
              f"(similaridade: {similaridade:.2f})")

        # Salva o tema no banco, a menos que esteja em modo simulação
        if not MODO_SIMULACAO:
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE fato_proposicoes SET tema = :tema WHERE id = :id"),
                    {"tema": tema_sugerido, "id": linha["id"]}
                )

        classificadas += 1

    except Exception as e:
        print(f"  ✗ Erro no ID {linha['id']}: {e}")
        erros += 1

# ── Relatório final ───────────────────────────────────────────────────────────
print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Relatório de classificação
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total processado : {total}
  Classificadas    : {classificadas}
  Ignoradas        : {ignoradas}  (similaridade abaixo do limiar)
  Erros            : {erros}
  Modo simulação   : {'SIM' if MODO_SIMULACAO else 'NÃO'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")