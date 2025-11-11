import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Carrega o .env
load_dotenv()

# Lê a URL de conexão
db_url = os.getenv("DATABASE_URL")

print(f"Tentando conectar em: {db_url}")

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute("SELECT NOW();")
        print("✅ Conexão bem-sucedida! Resposta do servidor:")
        for row in result:
            print(row)
except Exception as e:
    print("❌ Erro ao conectar:")
    print(e)
