import cx_Oracle
import os

# Oracle connection details
oracle_config = {
    'dsn': cx_Oracle.makedsn(
        os.getenv('ORACLE_HOST', 'localhost'),
        int(os.getenv('ORACLE_PORT', '1521')),
        service_name=os.getenv('ORACLE_DBNAME', 'xe')
    ),
    'user': os.getenv('ORACLE_USER', 'system'),
    'password': os.getenv('ORACLE_PASSWORD', 'Roni2108')
}

def fetch_last_10_tests_oracle():
    try:
        connection = cx_Oracle.connect(
            user=oracle_config['user'],
            password=oracle_config['password'],
            dsn=oracle_config['dsn']
        )
        cursor = connection.cursor()
        query = """
            SELECT test_name, status, details, test_time
            FROM (
                SELECT test_name, status, details, test_time
                FROM test_results
                ORDER BY test_time DESC
            )
            WHERE ROWNUM <= 10
            ORDER BY test_time ASC;
        """
        cursor.execute(query)
        results = cursor.fetchall()

        print("Last 10 test results from Oracle:")
        for row in results:
            print(f"Test Name: {row[0]}, Status: {row[1]}, Details: {row[2]}, Test Time: {row[3]}")

        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Failed to fetch results from Oracle: {str(e)}")

def fetch_all_tests_oracle():
    try:
        connection = cx_Oracle.connect(
            user=oracle_config['user'],
            password=oracle_config['password'],
            dsn=oracle_config['dsn']
        )
        cursor = connection.cursor()
        query = """
            SELECT test_name, status, details, test_time
            FROM test_results
            ORDER BY test_time;
        """
        cursor.execute(query)
        results = cursor.fetchall()

        print("All test results from Oracle:")
        for row in results:
            print(f"Test Name: {row[0]}, Status: {row[1]}, Details: {row[2]}, Test Time: {row[3]}")

        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Failed to fetch results from Oracle: {str(e)}")

if __name__ == "__main__":
    fetch_last_10_tests_oracle()
    # Uncomment the following line to fetch and print all tests
    # fetch_all_tests_oracle()
