import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class GroupsIOScraper:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://groups.io"
        self.login_url = f"{self.base_url}/login"
        
    def login_with_requests(self, email, password):
        """Attempt to login using requests library"""
        try:
            # Get the login page first to obtain CSRF token
            response = self.session.get(self.login_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract CSRF token
            csrf_token = soup.find('input', {'name': 'csrf'})['value']
            monocle_token = soup.find('input', {'name': 'monocle'})['value']
            
            # Prepare login data
            login_data = {
                'email': email,
                'password': password,
                'csrf': csrf_token,
                'monocle': monocle_token,
                'timezone': 'America/New_York'
            }
            
            # Attempt login
            response = self.session.post(self.login_url, data=login_data)
            
            # Check if login was successful
            if response.url != self.login_url:  # Usually redirects after successful login
                print("Login successful using requests!")
                return True
            else:
                print("Login failed using requests, trying Selenium...")
                return False
                
        except Exception as e:
            print(f"Error during requests login: {str(e)}")
            return False
            
    def login_with_selenium(self, email, password):
        """Attempt to login using Selenium"""
        try:
            # Initialize Chrome driver
            driver = webdriver.Chrome()
            driver.get(self.login_url)
            
            # Wait for email field and enter credentials
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_field.send_keys(email)
            
            # Find and fill password field
            password_field = driver.find_element(By.ID, "password")
            password_field.send_keys(password)
            
            # Click login button
            login_button = driver.find_element(By.ID, "loginbutton")
            login_button.click()
            
            # Wait for redirect or new element that indicates successful login
            time.sleep(3)  # Give it some time to process
            
            # Check if login was successful (you might want to adjust this check)
            if driver.current_url != self.login_url:
                print("Login successful using Selenium!")
                return driver
            else:
                print("Login failed using Selenium")
                driver.quit()
                return None
                
        except Exception as e:
            print(f"Error during Selenium login: {str(e)}")
            if 'driver' in locals():
                driver.quit()
            return None

def main():
    # Initialize scraper
    scraper = GroupsIOScraper()
    
    # Login credentials
    email = "allan.ascencio@gmail.com"
    password = "Sah%b5BGn9TBgia"
    
    # Try requests first
    if not scraper.login_with_requests(email, password):
        # If requests fails, try Selenium
        driver = scraper.login_with_selenium(email, password)
        if driver:
            print("Successfully logged in!")
            # Keep the browser window open for visual inspection
            input("Press Enter to close the browser...")
            driver.quit()
        else:
            print("All login attempts failed.")

if __name__ == "__main__":
    main()