import mysql.connector
import os

def DB_Ligar():
    # Caminho absoluto para o arquivo de certificado na pasta raiz do projeto
    ca_path = os.path.join(os.getcwd(), 'ca.pem')
    
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASS'),
        database=os.environ.get('DB_NAME'),
        port=os.environ.get('DB_PORT'),
        ssl_ca=ca_path,           # Aponta para o seu certificado ca.pem
        ssl_verify_cert=True,     # Exige a validação do certificado (seguro)
        ssl_verify_identity=False # Aiven não precisa verificar o hostname do certificado
    )
