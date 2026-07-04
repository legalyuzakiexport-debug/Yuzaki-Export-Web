import mysql.connector
import os

def DB_Ligar():
    # Usamos variáveis de ambiente para manter suas credenciais em segurança
    # No Render, você irá configurar estas variáveis na aba 'Environment'
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'yuzakiexport-yuzakiexport.f.aivencloud.com'),
        user=os.environ.get('DB_USER', 'avnadmin'),
        password=os.environ.get('DB_PASS', 'AVNS_3kpi-odCKjKGUoh6FwK'),
        database=os.environ.get('DB_NAME', 'defaultdb'),
        port=os.environ.get('DB_PORT', '22991'),
        # Configuração de SSL para o Aiven
        ssl_ca=os.environ.get('SSL_CA_PATH'), # Opcional: Se precisar do caminho do certificado .pem
        ssl_mode='REQUIRED' 
    )
