import os
import distro
import platform
import subprocess
import random
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def connection_status(driver):
    if wait_for_element_exists(driver, By.XPATH, "//*[text()='Connected']"):
        logging.info("Status: Connected!")
    elif wait_for_element_exists(driver, By.XPATH, "//*[text()='Disconnected']"):
        logging.warning("Status: Disconnected!")
    else:
        logging.warning("Status: Unknown!")

def check_active_element(driver):
    try:
        wait_for_element(driver, By.XPATH, "//*[text()='Activated']")
        driver.find_element(By.XPATH, "//*[text()='Activated']")
        logging.info("Extension is activated!")
    except NoSuchElementException:
        logging.error("Failed to find 'Activated' element. Extension activation failed.")

def wait_for_element_exists(driver, by, value, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        return True
    except TimeoutException:
        return False

def wait_for_element(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        return element
    except TimeoutException as e:
        logging.error(f"Error waiting for element {value}: {e}")
        raise

def set_local_storage_item(driver, key, value):
    driver.execute_script(f"localStorage.setItem('{key}', '{value}');")
    result = driver.execute_script(f"return localStorage.getItem('{key}');")
    return result

def add_cookie_to_local_storage(driver, cookie_value):
    keys = ['np_webapp_token', 'np_token']
    for key in keys:
        result = set_local_storage_item(driver, key, cookie_value)
        logging.info(f"Added {key} with value {result[:8]}...{result[-8:]} to local storage.")
    logging.info("!!!!! Your token can be used to login for 7 days !!!!!")

def get_chromedriver_version():
    try:
        result = subprocess.run(['chromedriver', '--version'], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        logging.error(f"Could not get ChromeDriver version: {e}")
        return "Unknown version"

def get_os_info():
    try:
        os_info = {
            'System': platform.system(),
            'Version': platform.version()
        }
        
        if os_info['System'] == 'Linux':
            os_info.update({
                'System': distro.name(pretty=True),
                'Version': distro.version(pretty=True, best=True)
            })
        return os_info
    except Exception as e:
        logging.error(f"Could not get OS information: {e}")
        return "Unknown OS"

def run():
    setup_logging()
    
    branch = ''
    version = '1.0.10' + branch
    secUntilRestart = 60
    logging.info(f"Started the script {version}")

    try:
        os_info = get_os_info()
        logging.info(f'OS Info: {os_info}')
        
        # Read variables from the OS env
        cookie = os.getenv('NP_COOKIE')
        extension_id = os.getenv('EXTENSION_ID')
        extension_url = os.getenv('EXTENSION_URL')
        git_username = os.getenv('GIT_USERNAME')
        git_repo = os.getenv('GIT_REPO')
        extensions_dir = 'extensions'

        # Check if credentials are provided
        if not cookie:
            logging.error('No cookie provided. Please set the NP_COOKIE environment variable.')
            return  # Exit the script if credentials are not provided
        
        os.makedirs(extensions_dir, exist_ok=True)
        extension_dir = os.path.join(extensions_dir, extension_id)
        os.makedirs(extension_dir, exist_ok=True)
        
        if os.path.exists(git_repo):
            subprocess.run(["rm", "-rf", git_repo], check=True)
        logging.info(f'Using {git_username}/{git_repo} to download the extension CRX file from the Chrome Web Store...')
        subprocess.run(["git", "clone", f"https://github.com/{git_username}/{git_repo}.git"], check=True)
        subprocess.run(["chmod", "+x", f"./{git_repo}/crx-dl.py"], check=True)
        crx_file_path = os.path.join(extension_dir, f"{extension_id}.crx")
        os.makedirs(extension_dir, exist_ok=True)
        subprocess.run(["python3", f"./{git_repo}/crx-dl.py", f"-o={crx_file_path}", extension_id], check=True)

        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0")

        chrome_options.add_extension(crx_file_path)

        # Initialize the WebDriver
        chromedriver_version = get_chromedriver_version()
        logging.info(f'Using {chromedriver_version}')
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        logging.error(f'An error occurred: {e}')
        logging.error(f'Restarting in 60 seconds...')
        time.sleep(secUntilRestart)
        run()

    try:
        # NodePass checks for width less than 1024p
        driver.set_window_size(1024, driver.get_window_size()['height'])

        # Navigate to a webpage
        logging.info(f'Navigating to {extension_url} website...')
        driver.get(extension_url)
        time.sleep(random.randint(3,7))

        add_cookie_to_local_storage(driver, cookie)

        # Check successful login
        while not wait_for_element_exists(driver, By.XPATH, "//*[text()='Dashboard']"):
            logging.info(f'Refreshing in {secUntilRestart} seconds to check login (If stuck, verify your token)...')
            driver.get(extension_url)

        logging.info('Logged in successfully!')

        time.sleep(random.randint(10,50))
        logging.info('Accessing extension settings page...')
        driver.get(f'chrome-extension://{extension_id}/index.html')
        time.sleep(random.randint(3,7))

        # Refresh until the "Login" button disappears
        while wait_for_element_exists(driver, By.XPATH, "//*[text()='Login']"):
            logging.info('Clicking the extension login button...')
            login = driver.find_element(By.XPATH, "//*[text()='Login']")
            login.click()
            time.sleep(10)
            # Refresh the page
            driver.refresh()

        # Check for the "Activated" element
        check_active_element(driver)

        # Get handles for all windows
        all_windows = driver.window_handles

        # Get the handle of the active window
        active_window = driver.current_window_handle

        # Close all windows except the active one
        for window in all_windows:
            if window != active_window:
                driver.switch_to.window(window)
                driver.close()

        # Switch back to the active window
        driver.switch_to.window(active_window)

        connection_status(driver)
    except Exception as e:
        logging.error(f'An error occurred: {e}')
        logging.error(f'Restarting in {secUntilRestart} seconds...')
        driver.quit()
        time.sleep(secUntilRestart)
        run()

    while True:
        try:
            time.sleep(3600)
            driver.refresh()
            connection_status(driver)
        except KeyboardInterrupt:
            logging.info('Stopping the script...')
            driver.quit()
            break

run()
