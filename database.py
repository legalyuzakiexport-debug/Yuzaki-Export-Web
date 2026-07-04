import mysql.connector
import os

def DB_Ligar():
    # Esta função lê as variáveis que configuraremos no Render
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASS'),
        database=os.environ.get('DB_NAME'),
        port=os.environ.get('DB_PORT'),
        ssl_disabled=False,       # Garante que o SSL esteja ativado
        ssl_verify_identity=False # Necessário se o certificado for auto-assinado pelo Aiven
    )

# Exemplo de como usar no seu código:
# conexao = DB_Ligar()
# cursor = conexao.cursor()
# ... suas consultas ...
