import psycopg2
import os

# PostgreSQL connection details
postgres_config = {
    'dbname': os.getenv('POSTGRES_DBNAME', 'postgres'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'Roni2108'),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432'))
}

def fetch_last_10_tests_postgres():
    try:
        connection = psycopg2.connect(**postgres_config)
        cursor = connection.cursor()
        query = """
            SELECT test_name, status, details, timestamp
            FROM test_results
            ORDER BY timestamp DESC
            LIMIT 10;
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Reverse the results to print from oldest to newest
        results.reverse()

        print("Last 10 test results from PostgreSQL:")
        for row in results:
            print(f"Test Name: {row[0]}, Status: {row[1]}, Details: {row[2]}, Test Time: {row[3]}")
        
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Failed to fetch results from PostgreSQL: {str(e)}")

def fetch_all_tests_postgres():
    try:
        connection = psycopg2.connect(**postgres_config)
        cursor = connection.cursor()
        query = """
            SELECT test_name, status, details, timestamp
            FROM test_results
            ORDER BY timestamp;
        """
        cursor.execute(query)
        results = cursor.fetchall()

        print("All test results from PostgreSQL:")
        for row in results:
            print(f"Test Name: {row[0]}, Status: {row[1]}, Details: {row[2]}, Test Time: {row[3]}")
        
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Failed to fetch results from PostgreSQL: {str(e)}")

if __name__ == "__main__":
    fetch_last_10_tests_postgres()
    # Uncomment the following line to fetch and print all tests
    # fetch_all_tests_postgres()
