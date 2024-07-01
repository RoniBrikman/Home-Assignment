import cx_Oracle
import psycopg2
from playwright.sync_api import sync_playwright
import pytest
import requests
import logging
import re
import os


# Set environment variables
os.environ['ORACLE_HOST'] = 'DESKTOP-CKAGB2K'
os.environ['ORACLE_PORT'] = '1521'
os.environ['ORACLE_DBNAME'] = 'xe'
os.environ['ORACLE_USER'] = 'system'
os.environ['ORACLE_PASSWORD'] = 'Roni2108'

os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_DBNAME'] = 'postgres'
os.environ['POSTGRES_USER'] = 'postgres'
os.environ['POSTGRES_PASSWORD'] = 'Roni2108'


# Global variables to keep track of dependencies
sponsored_url = None  # This will store the URL of the sponsored result found during the search.
search_performed = False  # This flag indicates whether a search has been performed or not.
youtube_video_links = []  # Store YouTube video links

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def normalize_title(title):
    """
    Input: title (str) - The title to normalize.
    Output: (str) - The normalized title.
    Description: This function removes all non-letter characters from the title and converts it to lowercase.
    """
    return re.sub(r'[^a-zA-Z\s]', '', title).lower()

@pytest.fixture(scope="session")
def browser():
    """
    Input: None
    Output: Browser instance
    Description: Sets up a Playwright browser instance to be used for testing. It launches the browser in headless(True/False) mode and ensures it is closed after the session.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        yield browser
        browser.close()

@pytest.fixture(scope="session")
def page_with_results(browser):
    """
    Input: browser (Browser instance)
    Output: Page instance with search results
    Description: This fixture sets up a Playwright page, navigates to Google, performs a search for 'Domino's', and handles any location prompts.
    """
    context = browser.new_context(locale="en-US", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    page = context.new_page()

    logger.info("Navigating to Google and setting the language to English")
    page.goto("https://www.google.com?hl=en")
    page.wait_for_load_state('networkidle')  

    logger.info("Using specific selectors to find the search input field")
    search_input = page.query_selector('textarea[name="q"], input[title="Search"], input[aria-label="Search"], input[type="text"], input[class="gLFyf gsfi"]')

    assert search_input is not None, "Search input not found!"
    logger.info("Search input field found")

    logger.info("Performing a search for 'Domino's'")
    search_input.fill("Domino's")
    search_input.press('Enter')

    logger.info("Waiting for search results to load")
    page.wait_for_load_state('networkidle')

    # If location prompt appears, it will click "Not now". 
    logger.info("Handling location prompt if it appears")
    try:
        page.click('text="Not now"', timeout=5000)
        logger.info("Location prompt dismissed.")
    except Exception as e:
        logger.info("Location prompt did not appear.")

    yield page
    context.close()

def get_postgres_connection():
    """
    Input: None
    Output: psycopg2 connection object
    Description: Establishes and returns a connection to the PostgreSQL database using environment variables for the configuration.
    """
    return psycopg2.connect( # establishes a connection to the PostgreSQL database.
        dbname=os.getenv('POSTGRES_DBNAME', 'postgres'), # Get the database name from environment variables
        user=os.getenv('POSTGRES_USER', 'postgres'), # Get the user name from environment variables
        password=os.getenv('POSTGRES_PASSWORD', 'Roni2108'), # Get the password from environment variables
        host=os.getenv('POSTGRES_HOST', 'localhost'), # Get the database host from environment variables
        port=int(os.getenv('POSTGRES_PORT', '5432')) # Get the database port from environment variables
    )

def get_oracle_connection():
    """
    Input: None
    Output: cx_Oracle connection object
    Description: Establishes and returns a connection to the Oracle database using environment variables for the configuration.
    """
    dsn = cx_Oracle.makedsn( # establishes a connection to the Oracle database.
        os.getenv('ORACLE_HOST', 'localhost'), # Get the Oracle host from environment variables
        int(os.getenv('ORACLE_PORT', '1521')), # Get the Oracle port from environment variables
        service_name=os.getenv('ORACLE_DBNAME', 'xe') # Get the Oracle service name from environment variables
    )
    return cx_Oracle.connect(
        user=os.getenv('ORACLE_USER', 'system'), # Get the Oracle user name from environment variables
        password=os.getenv('ORACLE_PASSWORD', 'Roni2108'), # Get the Oracle password from environment variables
        dsn=dsn # Use the constructed DSN for the connection
    )



def save_test_result(test_name, status, details):
    """
    Input:
        - test_name: Name of the test (str)
        - status: Status of the test (e.g., 'PASSED', 'FAILED') (str)
        - details: Additional details about the test (str)
    Output: None
    Description: Saves the test result to either PostgreSQL, Oracle, or both, based on the environment variable `DB_SAVE_MODE`.
    """
    # Get the database save mode from environment variables
    db_save_mode = int(os.getenv('DB_SAVE_MODE', '0'))  # 0 = PostgreSQL, 1 = Oracle, 2 = Both

    # Validate the DB_SAVE_MODE value
    if db_save_mode not in [0, 1, 2]:
        raise ValueError("Unsupported DB_SAVE_MODE value. Use 0 (PostgreSQL), 1 (Oracle), or 2 (Both).")

    # Save to PostgreSQL if DB_SAVE_MODE is 0 or 2
    if db_save_mode == 0 or db_save_mode == 2:
        logger.info("Saving result to PostgreSQL")
        try:
            connection = get_postgres_connection() # Establish a PostgreSQL connection
            cursor = connection.cursor()
            # Insert query to save test result to PostgreSQL
            insert_query = """
                INSERT INTO test_results (test_name, status, details, timestamp)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """
            cursor.execute(insert_query, (test_name, status, details))
            connection.commit() # Commit the transaction
            cursor.close()
            connection.close()
            logger.info("Result saved to PostgreSQL successfully")
        except Exception as e:
            logger.error(f"Failed to save result to PostgreSQL: {str(e)}")

    # Save to Oracle if DB_SAVE_MODE is 1 or 2
    if db_save_mode == 1 or db_save_mode == 2:
        logger.info("Saving result to Oracle")
        try:
            connection = get_oracle_connection() # Establish an Oracle connection
            cursor = connection.cursor()
            # Insert query to save test result to Oracle
            # The placeholders :1, :2, and :3 correspond to test_name, status, and details respectively.
            insert_query = """
                INSERT INTO test_results (test_name, status, details, test_time)
                VALUES (:1, :2, :3, SYSTIMESTAMP)
            """
            cursor.execute(insert_query, (test_name, status, details))
            connection.commit() # Commit the transaction
            cursor.close()
            connection.close()
            logger.info("Result saved to Oracle successfully")
        except Exception as e:
            logger.error(f"Failed to save result to Oracle: {str(e)}")


def test_google_search_sponsored(page_with_results):
    """
    Input:
        - page_with_results: Playwright page object with the search results loaded
    Output: None
    Description: Performs a search on Google, identifies the first sponsored result, clicks on it, and saves the URL.
    """
    global sponsored_url, search_performed
    test_name = 'test_google_search_sponsored'
    try:
        logger.info("Running test_google_search_sponsored")
        page = page_with_results
        search_performed = True

        logger.info("Asserting that there is at least one sponsored result")
        try:
            # Wait for the first sponsored result to appear, with a timeout of 60 seconds
            page.wait_for_selector('div[data-text-ad="1"]', timeout=60000) 
        except Exception as e:
            raise AssertionError("No sponsored results found within the timeout period!") from e

        sponsored_results = page.query_selector_all('div[data-text-ad="1"]')
        assert len(sponsored_results) > 0, "No sponsored results found!"
        logger.info(f"Found {len(sponsored_results)} sponsored results")

        logger.info("Clicking on the first sponsored result and copying the URL")
        sponsored_results[0].click() # Click on the first sponsored result
        page.wait_for_load_state('load') # Wait for the new page to load
        sponsored_url = page.url # Save the URL of the sponsored result

        logger.info(f"Sponsored URL: {sponsored_url}")

        # Save the URL to a file for later use
        with open("sponsored_url.txt", "w") as f:
            f.write(sponsored_url)

        # Checkes that at least one url was found
        assert sponsored_url is not None, "No sponsored URL found!"
        logger.info("Sponsored URL found successfully")

        save_test_result(test_name, 'PASSED', 'Sponsored URL found and saved successfully.')
    except Exception as e:
        # Log the error and save the test result as failed
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise

def test_api_call_to_sponsored_url():
    """
    Input: None
    Output: None
    Description: Performs an API call to the saved sponsored URL and verifies the response status code is 200.
    """
    global sponsored_url
    test_name = 'test_api_call_to_sponsored_url'

    # Check if sponsored_url is available
    if not sponsored_url:
        logger.info(f"Skipping {test_name} because no sponsored URL was found in the previous test.")
        pytest.skip(f"Skipping {test_name} because no sponsored URL was found in the previous test.")
    try:
        # Read the saved sponsored URL from the file
        with open("sponsored_url.txt", "r") as f:
            sponsored_url = f.read().strip()

        logger.info("Running test_api_call_to_sponsored_url")
        logger.info(f"Performing an API call to the URL: {sponsored_url}")

        # Perform an API call to the saved URL
        response = requests.get(sponsored_url)
        logger.info(f"Received response with status code: {response.status_code}")

        # Check if the response status code is 200
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
        logger.info("API call to the sponsored URL was successful with status code 200")

        save_test_result(test_name, 'PASSED', 'API call to the sponsored URL was successful.')
    except Exception as e:
        # Log the error and save the test result as failed
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise

def test_check_dominos_in_response():
    """
    Input: None
    Output: None
    Description: Performs an API call to the saved sponsored URL and checks if 'Domino's' or 'Dominos' is present in the response content.
    """
    global sponsored_url
    test_name = 'test_check_dominos_in_response'

    # Check if sponsored_url is available
    if not sponsored_url:
        logger.info(f"Skipping {test_name} because no sponsored URL was found in the previous test.")
        pytest.skip(f"Skipping {test_name} because no sponsored URL was found in the previous test.")
    try:
        # Read the saved sponsored URL from the file
        with open("sponsored_url.txt", "r") as f:
            sponsored_url = f.read().strip()

        logger.info("Running test_check_dominos_in_response")
        logger.info(f"Performing an API call to the URL: {sponsored_url}")

        # Perform an API call to the saved URL
        response = requests.get(sponsored_url)
        logger.info("Checking if 'Domino's' or 'Dominos' is present in the response content")

        # Check if the response content contains 'Domino's' or 'Dominos'
        assert "Domino's" in response.text or "Dominos" in response.text, "Response does not contain 'Domino's' or 'Dominos'"
        logger.info("'Domino's' or 'Dominos' is present in the response content")

        save_test_result(test_name, 'PASSED', "'Domino's' or 'Dominos' is present in the response content.")
    except Exception as e:
        # Log the error and save the test result as failed
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise

def test_youtube_videos_count(page_with_results):
    """
    Input: page_with_results (fixture providing a Playwright page object with search results)
    Output: None
    Description: Navigates to the 'Videos' tab in Google search results and verifies that there are at least two YouTube video links on the first page.
    """
    global search_performed, youtube_video_links
    test_name = 'test_youtube_videos_count'
    try:
        page = page_with_results
        logger.info("Running test_youtube_videos_count")

        # Check if a search has already been performed
        if not search_performed:
            search_performed = True
        else:
            logger.info("Using the previously performed search for 'Domino's'")

        logger.info("Navigating to the 'Videos' tab")
        page.click('text="Videos"')
        page.wait_for_load_state('networkidle')

        logger.info("Asserting that there are at least two results from youtube.com on the first page")
        youtube_results = page.query_selector_all('a[href*="youtube.com/watch"]')

        # Collect the video links
        youtube_video_links = [result.get_attribute('href') for result in youtube_results if 'youtube.com' in result.get_attribute('href')]

        # Assert that there are at least two YouTube video links
        assert len(youtube_video_links) >= 2, f"Expected at least 2 YouTube results, but found {len(youtube_video_links)}"
        logger.info(f"Found {len(youtube_video_links)} YouTube results on the first page of the 'Videos' tab")

        save_test_result(test_name, 'PASSED', f"Found {len(youtube_video_links)} YouTube results.")
    except Exception as e:
        # Log the error and save the test result as failed
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise


def test_youtube_videos_relevance(page_with_results):
    """
    Input: page_with_results (fixture providing a Playwright page object with search results)
    Output: None
    Description: Verifies that the titles of the two YouTube videos found in the previous test are related to the search term 'Domino's' or 'Dominos'.
    """
    global search_performed, youtube_video_links
    test_name = 'test_youtube_videos_relevance'
    try:
        if len(youtube_video_links) < 2:
            logger.info(f"Skipping {test_name} because less than two YouTube video links were found in the previous test.")
            pytest.skip(f"Skipping {test_name} because less than two YouTube video links were found in the previous test.")

        page = page_with_results
        if not search_performed:
            search_performed = True
        else:
            logger.info("Using the previously performed search for 'Domino's'")

        logger.info("Running test_youtube_videos_relevance")

        logger.info("Navigating to the 'Videos' tab")
        page.click('text="Videos"')
        page.wait_for_load_state('networkidle')

        logger.info("Asserting that the videos are related to the search term 'Domino's' or 'Dominos'")

        for video_link in youtube_video_links[:2]:  # Only check the first two videos
            video_element = page.query_selector(f'a[href="{video_link}"]')
            title_element = video_element.query_selector('h3, span[aria-label], div[aria-label]')  # Adjust as necessary to target the title
            if title_element:
                title = title_element.inner_text().strip()
                normalized_title = normalize_title(title)
                logger.info(f"Video title: {title}")
                assert "dominos" in normalized_title, f"Video title does not contain 'Domino's' or 'Dominos': {title}"

        logger.info("First two video titles contain 'Dominos'")
        save_test_result(test_name, 'PASSED', "First two video titles contain 'Dominos'.")
    except Exception as e:
        # Log the error and save the test result as failed
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise
