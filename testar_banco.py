import os
import psycopg2
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Pega a URL de conexão que você salvou
db_uri = os.getenv("DB_URI")

print("Tentando conectar ao Supabase...")

try:
    # Tenta estabelecer a conexão
    connection = psycopg2.connect(db_uri)
    cursor = connection.cursor()
    
    # Executa um comando simples para testar
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    
    print("\n🚀 CONEXÃO REALIZADA COM SUCESSO NO SUPABASE!")
    print(f"Versão do banco de dados: {db_version[0]}\n")
    
    # Fecha o teste
    cursor.close()
    connection.close()

except Exception as error:
    print("\n❌ ERRO AO CONECTAR NO BANCO DE DADOS:")
    print(error)