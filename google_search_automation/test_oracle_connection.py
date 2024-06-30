import cx_Oracle
import os

def get_oracle_connection():
    dsn_tns = cx_Oracle.makedsn(
        os.getenv('ORACLE_HOST', 'localhost'), 
        os.getenv('ORACLE_PORT', '1521'), 
        service_name=os.getenv('ORACLE_SERVICE_NAME', 'orcl')
    )
    connection = cx_Oracle.connect(
        user=os.getenv('ORACLE_USER', 'your_username'), 
        password=os.getenv('ORACLE_PASSWORD', 'your_password'), 
        dsn=dsn_tns
    )
    return connection

try:
    conn = get_oracle_connection()
    print("Connection successful")
    conn.close()
except cx_Oracle.DatabaseError as e:
    print(f"Failed to connect to Oracle database: {e}")
