import cx_Oracle
import psycopg2
from playwright.sync_api import sync_playwright
from time import sleep
import pytest
import requests
import logging
import re
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def normalize_title(title):
    # Remove all non-letter characters and convert to lowercase
    return re.sub(r'[^a-zA-Z\s]', '', title).lower()

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        yield browser
        browser.close()

@pytest.fixture(scope="session")
def page_with_results(browser):
    context = browser.new_context(locale="en-US", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    page = context.new_page()

    logger.info("Navigating to Google and setting the language to English")
    page.goto("https://www.google.com?hl=en")
    page.wait_for_load_state('networkidle')  # Wait for the network to be idle

    logger.info("Taking a screenshot for debugging")
    page.screenshot(path="before_search_input.png")

    logger.info("Using specific selectors to find the search input field")
    search_input = page.query_selector('textarea[name="q"], input[title="Search"], input[aria-label="Search"], input[type="text"], input[class="gLFyf gsfi"]')

    assert search_input is not None, "Search input not found!"
    logger.info("Search input field found")

    logger.info("Performing a search for 'Domino's'")
    search_input.fill("Domino's")
    search_input.press('Enter')

    logger.info("Waiting for search results to load")
    page.wait_for_load_state('networkidle')

    logger.info("Handling location prompt if it appears")
    try:
        page.click('text="Not now"', timeout=5000)
        logger.info("Location prompt dismissed.")
    except Exception as e:
        logger.info("Location prompt did not appear.")

    yield page
    context.close()

def get_postgres_connection():
    return psycopg2.connect(
        dbname=os.getenv('POSTGRES_DBNAME', 'postgres'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'Roni2108'),
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', '5432'))
    )

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

def save_test_result(test_name, status, details):
    db_save_mode = int(os.getenv('DB_SAVE_MODE', '0'))  # 0 = PostgreSQL, 1 = Oracle, 2 = Both

    if db_save_mode not in [0, 1, 2]:
        raise ValueError("Unsupported DB_SAVE_MODE value. Use 0 (PostgreSQL), 1 (Oracle), or 2 (Both).")

    if db_save_mode == 0 or db_save_mode == 2:
        logger.info("Saving result to PostgreSQL")
        connection = get_postgres_connection()
        try:
            cursor = connection.cursor()
            insert_query = "INSERT INTO test_results (test_name, status, details) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (test_name, status, details))
            connection.commit()
            cursor.close()
            logger.info("Result saved to PostgreSQL successfully")
        except Exception as e:
            connection.rollback()
            logger.error(f"Failed to save result to PostgreSQL: {str(e)}")
            raise e
        finally:
            connection.close()

    if db_save_mode == 1 or db_save_mode == 2:
        logger.info("Saving result to Oracle")
        connection = get_oracle_connection()
        try:
            cursor = connection.cursor()
            insert_query = "INSERT INTO test_results (test_name, status, details) VALUES (:1, :2, :3)"
            cursor.execute(insert_query, (test_name, status, details))
            connection.commit()
            cursor.close()
            logger.info("Result saved to Oracle successfully")
        except Exception as e:
            connection.rollback()
            logger.error(f"Failed to save result to Oracle: {str(e)}")
            raise e
        finally:
            connection.close()

def test_google_search_sponsored(page_with_results):
    test_name = 'test_google_search_sponsored'
    try:
        logger.info("Running test_google_search_sponsored")
        page = page_with_results

        logger.info("Asserting that there is at least one sponsored result")
        page.wait_for_selector('div[data-text-ad="1"]', timeout=60000)  # Increase timeout to 60 seconds
        sponsored_results = page.query_selector_all('div[data-text-ad="1"]')
        assert len(sponsored_results) > 0, "No sponsored results found!"
        logger.info(f"Found {len(sponsored_results)} sponsored results")

        logger.info("Clicking on the first sponsored result and copying the URL")
        sponsored_results[0].click()
        page.wait_for_load_state('load')
        sponsored_url = page.url

        logger.info(f"Sponsored URL: {sponsored_url}")

        # Save the URL to a file for later use
        with open("sponsored_url.txt", "w") as f:
            f.write(sponsored_url)

        assert sponsored_url is not None, "No sponsored URL found!"
        logger.info("Sponsored URL found successfully")
        
        save_test_result(test_name, 'PASSED', 'Sponsored URL found and saved successfully.')
    except Exception as e:
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise

def test_api_call_to_sponsored_url():
    test_name = 'test_api_call_to_sponsored_url'
    try:
        with open("sponsored_url.txt", "r") as f:
            sponsored_url = f.read().strip()

        logger.info("Running test_api_call_to_sponsored_url")
        logger.info(f"Performing an API call to the URL: {sponsored_url}")
        response = requests.get(sponsored_url)
        logger.info(f"Received response with status code: {response.status_code}")
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
        logger.info("API call to the sponsored URL was successful with status code 200")
        
        save_test_result(test_name, 'PASSED', 'API call to the sponsored URL was successful.')
    except Exception as e:
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise

def test_check_dominos_in_response():
    test_name = 'test_check_dominos_in_response'
    try:
        with open("sponsored_url.txt", "r") as f:
            sponsored_url = f.read().strip()

        logger.info("Running test_check_dominos_in_response")
        logger.info(f"Performing an API call to the URL: {sponsored_url}")
        response = requests.get(sponsored_url)
        logger.info("Checking if 'Domino's' or 'Dominos' is present in the response content")
        assert "Domino's" in response.text or "Dominos" in response.text, "Response does not contain 'Domino's' or 'Dominos'"
        logger.info("'Domino's' or 'Dominos' is present in the response content")
        
        save_test_result(test_name, 'PASSED', "'Domino's' or 'Dominos' is present in the response content.")
    except Exception as e:
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise

def test_youtube_videos_count(page_with_results):
    test_name = 'test_youtube_videos_count'
    try:
        page = page_with_results
        logger.info("Running test_youtube_videos_count")

        logger.info("Navigating to the 'Videos' tab")
        page.click('text="Videos"')
        page.wait_for_load_state('networkidle')

        logger.info("Asserting that there are at least two results from youtube.com on the first page")
        youtube_results = [result for result in page.query_selector_all('a[href*="youtube.com/watch"]') if 'youtube.com' in result.get_attribute('href')]
        assert len(youtube_results) >= 2, f"Expected at least 2 YouTube results, but found {len(youtube_results)}"
        logger.info(f"Found {len(youtube_results)} YouTube results on the first page of the 'Videos' tab")
        
        save_test_result(test_name, 'PASSED', f"Found {len(youtube_results)} YouTube results.")
    except Exception as e:
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise

def test_youtube_videos_relevance(page_with_results):
    test_name = 'test_youtube_videos_relevance'
    try:
        page = page_with_results
        logger.info("Running test_youtube_videos_relevance")

        logger.info("Navigating to the 'Videos' tab")
        page.click('text="Videos"')
        page.wait_for_load_state('networkidle')

        logger.info("Asserting that the videos are related to the search term 'Domino's' or 'Dominos'")
        youtube_results = page.query_selector_all('a[href*="youtube.com/watch"]')
        
        assert len(youtube_results) > 0, "No YouTube results found"
        logger.info(f"Found {len(youtube_results)} YouTube results on the first page of the 'Videos' tab")
        
        for result in youtube_results:
            # Narrow down to the element that likely contains the title
            title_element = result.query_selector('h3, span[aria-label], div[aria-label]')  # Adjust as necessary to target the title
            if title_element:
                title = title_element.inner_text().strip()
                normalized_title = normalize_title(title)
                logger.info(f"Video title: {title}")
                assert "dominos" in normalized_title, f"Video title does not contain 'Domino's' or 'Dominos': {title}"

        logger.info("All video titles contain 'Dominos'")
        save_test_result(test_name, 'PASSED', "All video titles contain 'Dominos'.")
    except Exception as e:
        logger.error(f"Test {test_name} failed: {str(e)}")
        save_test_result(test_name, 'FAILED', str(e))
        raise
