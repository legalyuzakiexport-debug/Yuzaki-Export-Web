import mysql.connector

def DB_Ligar():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='yuzaki_export'
    )