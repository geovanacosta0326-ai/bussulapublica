# 🏛️ Radar Legislativo — Pipeline de Inteligência Legislativa com IA

> Projeto Integrador — Pós Tech Engenharia de Dados  
> Pipeline ETL automatizado sobre dados abertos da Câmara dos Deputados, com classificação temática via IA e alertas automáticos por e-mail.

---

## 📌 O Problema

A consultoria fictícia **Bússola Pública** vendia relatórios de inteligência legislativa a R$ 15 mil/mês por cliente — produzidos manualmente por dois analistas que liam o site da Câmara o dia inteiro. O processo não escalava:

- Sem base de dados centralizada (tudo em planilhas pessoais)
- Sem histórico organizado
- Classificação de temas inconsistente entre analistas
- Alertas dependiam da memória humana
- Nenhum indicador medido sistematicamente

---

## 💡 A Solução

Um pipeline completo de **ETL automatizado com IA** que:

1. **Extrai** dados da API pública da Câmara dos Deputados
2. **Transforma e carrega** no banco PostgreSQL (Supabase)
3. **Classifica** proposições por tema via API da Anthropic (Claude Haiku)
4. **Automatiza** via workflows n8n (carga incremental + envio de e-mail semanal)

---

## 🏗️ Arquitetura do Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Câmara dos Deputados                  │
│     /deputados  /partidos  /proposicoes  /votacoes  /despesas    │
└───────────────────────────┬─────────────────────────────────────┘
                            │  HTTP (requests)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTRAÇÃO  (Python)                            │
│   extract.py          → proposições, votações, deputados,        │
│   extract_despesa.py  → despesas por deputado (mês anterior)     │
│                                                                  │
│   Saída: data/raw/*.json  |  data/raw/despesas/ANO_MES/*.json    │
└───────────────────────────┬─────────────────────────────────────┘
                            │  pd.json_normalize()
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               TRANSFORMAÇÃO & CARGA  (Pandas + SQLAlchemy)       │
│   transform_load.py         → dim_deputados, dim_partidos,       │
│                               fato_proposicoes, fato_votacoes    │
│   transform_load_despesa.py → fato_despesas                      │
│                                                                  │
│   Tratamentos:                                                    │
│   • ementa nula/vazia → "Sem ementa"                             │
│   • ano = 0 ou nulo   → extrai de dataApresentacao               │
│   • deduplicação por (id, data) antes de inserir                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │  SQLAlchemy → Supabase (PostgreSQL)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BANCO DE DADOS — Supabase                    │
│                                                                  │
│   Dimensões          Fatos                                       │
│   ├── dim_deputados  ├── fato_proposicoes  (+ coluna: tema)      │
│   └── dim_partidos   ├── fato_votacoes                           │
│                      └── fato_despesas                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┴──────────────┐
              ▼                            ▼
┌──────────────────────┐     ┌─────────────────────────────────┐
│  CLASSIFICAÇÃO IA    │     │  AUTOMAÇÃO — n8n Workflows       │
│  (n8n + Claude Haiku)│     │                                  │
│                      │     │  • Carga_ClassificaTema.json     │
│  Temas:              │     │    Carga incremental semanal +   │
│  • Agribusiness      │     │    classificação temática via IA  │
│  • Educação          │     │                                  │
│  • Saúde             │     │  • EnvioEmail.json               │
│  • Segurança Pública │     │    E-mail semanal com as 5       │
│  • Economia          │     │    proposições mais recentes      │
│  • Infraestrutura    │     │    por tema                      │
│  • Meio Ambiente     │     │                                  │
│  • Tecnologia        │     │  Trigger: Schedule (semanal)     │
│  • Outros            │     │  Banco: Supabase REST API        │
└──────────────────────┘     └─────────────────────────────────┘
```

---

## 🗂️ Modelo de Dados

### Dimensões

**`dim_deputados`**
| Coluna | Tipo | Descrição |
|---|---|---|
| id | text (PK) | Identificador único do deputado |
| nome | text | Nome completo |
| siglaPartido | text | Sigla do partido |
| siglaUf | text | Estado (UF) |
| idLegislatura | integer | Número da legislatura |
| urlFoto | text | URL da foto oficial |

**`dim_partidos`**
| Coluna | Tipo | Descrição |
|---|---|---|
| id | text (PK) | Identificador único do partido |
| sigla | text | Sigla do partido |
| nome | text | Nome completo |
| uri | text | URI da API |

### Fatos

**`fato_proposicoes`**
| Coluna | Tipo | Descrição |
|---|---|---|
| id | integer (PK) | Identificador único |
| uri | text | URI da API |
| siglaTipo | text | Tipo da proposição (PL, PEC, etc.) |
| codTipo | integer | Código do tipo |
| numero | integer | Número da proposição |
| ano | integer | Ano (extraído de dataApresentacao quando nulo/zero) |
| ementa | text | Texto da ementa ("Sem ementa" quando ausente) |
| dataApresentacao | date | Data de apresentação |
| **tema** | **text** | **Classificação temática via IA** |

**`fato_votacoes`**
| Coluna | Tipo | Descrição |
|---|---|---|
| id | text (PK) | Identificador único |
| data | date | Data da votação |
| dataHoraRegistro | timestamp | Data e hora do registro |
| siglaOrgao | text | Órgão responsável |
| descricao | text | Descrição da votação |
| aprovacao | integer | 1 = aprovada, 0 = reprovada |
| proposicaoObjeto | text | Proposição votada |

**`fato_despesas`**
| Coluna | Tipo | Descrição |
|---|---|---|
| coddocumento | text (PK) | Código único do documento |
| deputado_id | integer (FK) | Referência ao deputado |
| dataDocumento | date | Data do gasto |
| tipoDespesa | text | Categoria do gasto |
| fornecedor | text | Nome do fornecedor |
| valorDocumento | numeric | Valor declarado |
| valorLiquido | numeric | Valor líquido |
| mes | integer | Mês de referência |
| ano | integer | Ano de referência |

---

## 📁 Estrutura do Repositório

```
radar-legislativo/
│
├── extract.py                  # Extração: deputados, partidos, proposições, votações
├── extract_despesa.py          # Extração: despesas por deputado (mês anterior)
├── transform_load.py           # Carga: dimensões + fatos principais
├── transform_load_despesa.py   # Carga: fato_despesas
│
├── workflows/
│   ├── Carga_ClassificaTema.json   # n8n: carga incremental + classificação IA
│   └── EnvioEmail.json             # n8n: e-mail semanal com resumo legislativo
│
├── data/
│   └── raw/                    # JSONs brutos extraídos da API (ignorado pelo git)
│
├── .env.example                # Variáveis de ambiente necessárias
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Como Rodar

### 1. Pré-requisitos

```bash
git clone https://github.com/seu-usuario/radar-legislativo.git
cd radar-legislativo
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Copie o arquivo de exemplo e preencha com suas credenciais:

```bash
cp .env.example .env
```

```env
# .env
DB_URI=postgresql://usuario:senha@host:5432/postgres
```

> ⚠️ **Nunca suba o `.env` para o GitHub.** Ele já está no `.gitignore`.

### 3. Executar a extração

```bash
# Extrai deputados, partidos, proposições e votações
python extract.py

# Extrai despesas do mês anterior para todos os deputados
python extract_despesa.py
```

### 4. Carregar no banco

```bash
# Carrega dimensões e fatos principais
python transform_load.py

# Carrega despesas
python transform_load_despesa.py
```

### 5. Importar workflows no n8n

1. Abra o n8n
2. Importe os arquivos da pasta `workflows/`
3. Configure as credenciais de Supabase e Anthropic dentro do n8n
4. Ative os workflows

---

## 🤖 Camada de IA — Classificação Temática

Cada proposição com `tema = NULL` passa pelo seguinte fluxo no n8n:

1. **Busca Sem Tema** — consulta o Supabase via REST e retorna até 500 proposições sem tema
2. **Prepara Classificação** — sanitiza a ementa (remove aspas, quebras de linha)
3. **Verifica ementa** — proposições com `"Sem ementa"` são **puladas** (sem custo de API)
4. **HTTP Classifica** — envia a ementa para `claude-haiku-4-5` com o prompt:

```
Classifique esta ementa em uma das categorias:
Agribusiness, Educação, Saúde, Segurança Pública, Economia,
Infraestrutura, Meio Ambiente, Tecnologia ou Outros.
Responda APENAS com a palavra da categoria.

Ementa: {ementa}
```

5. **Atualizar Tema** — grava o tema retornado na coluna `tema` da proposição

**Decisão de design:** Claude Haiku foi escolhido por custo/latência: `max_tokens: 50` (resposta de 1 palavra), ideal para classificação em escala.

---

## 🔄 Workflows n8n

### `Carga_ClassificaTema.json`
- **Trigger:** semanal (Schedule)
- **O que faz:** busca a última data de proposição no banco → calcula janela de 15 dias → pagina a API da Câmara → faz upsert no Supabase → classifica proposições sem tema via Claude Haiku
- **Deduplicação:** upsert por `id`, sem risco de duplicar ao rodar mais de uma vez

### `EnvioEmail.json`
- **Trigger:** semanal
- **O que faz:** consulta as proposições mais recentes por tema e envia um e-mail formatado com resumo legislativo da semana

---

## 🛠️ Decisões Técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Banco de dados | Supabase (PostgreSQL) | Plano gratuito, painel web, REST API nativa, fácil de compartilhar |
| Modelo de IA | Claude Haiku (`claude-haiku-4-5`) | Menor custo, baixa latência, suficiente para classificação simples |
| Deduplicação | Chave `(id, data)` + set em memória | Evita duplicatas mesmo rodando o script múltiplas vezes |
| Paginação incremental | Filtra por `dataApresentacao` / `data` | Só busca novos registros, economizando chamadas à API |
| Ementa ausente | Substitui por `"Sem ementa"` e pula IA | Evita custo desnecessário de API em registros sem conteúdo |
| Ano ausente/zero | Extrai de `dataApresentacao` | Campo `ano` vinha como `0` da API em alguns casos |

---

## 📦 Requirements

```
requests
pandas
sqlalchemy
psycopg2-binary
python-dotenv
```

---

## 🔗 Links Úteis

- [API da Câmara dos Deputados](https://dadosabertos.camara.leg.br/swagger/api.html)
- [Supabase](https://supabase.com)
- [n8n](https://n8n.io)
- [Anthropic API](https://docs.anthropic.com)
