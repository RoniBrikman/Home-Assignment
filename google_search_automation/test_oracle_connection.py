import cx_Oracle
import os

def get_oracle_connection():
    dsn = cx_Oracle.makedsn(
        os.getenv('ORACLE_HOST', 'localhost'),
        int(os.getenv('ORACLE_PORT', '1521')),
        service_name=os.getenv('ORACLE_DBNAME', 'xe')
    )
    return cx_Oracle.connect(
        user=os.getenv('ORACLE_USER', 'system'),
        password=os.getenv('ORACLE_PASSWORD', 'Roni2108'),
        dsn=dsn
    )

def test_oracle_connection():
    try:
        connection = get_oracle_connection()
        cursor = connection.cursor()
        insert_query = "INSERT INTO test_results (test_name, status, details) VALUES (:1, :2, :3)"
        cursor.execute(insert_query, ("test_oracle_connection", "PASSED", "Oracle connection test successful"))
        connection.commit()
        cursor.close()
        connection.close()
        print("Oracle connection test successful and data inserted.")
    except Exception as e:
        print(f"Failed to connect to Oracle or insert data: {str(e)}")

if __name__ == "__main__":
    test_oracle_connection()
