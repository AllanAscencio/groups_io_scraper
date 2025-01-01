# import time
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from bs4 import BeautifulSoup

# def scrape_groups_io_with_selenium(username, password):
#     # 1. Create a Chrome browser instance (NON-HEADLESS)
#     driver = webdriver.Chrome()  # Ensure chromedriver is on your system PATH or provide the executable path.

#     try:
#         # 2. Go to the login page
#         driver.get("https://groups.io/login")
#         time.sleep(2)  # Wait for the page to load

#         # 3. Fill in the login form
#         email_input = driver.find_element(By.ID, "email")
#         password_input = driver.find_element(By.ID, "password")

#         email_input.send_keys(username)
#         password_input.send_keys(password)

#         # 4. Click the Log In button
#         login_button = driver.find_element(By.ID, "loginbutton")
#         login_button.click()

#         # 5. Wait for login to complete
#         time.sleep(3)

#         # 6. Navigate to topics page
#         driver.get("https://groups.io/topics")
#         time.sleep(3)

#         while True:
#             # 7. Retrieve the topic links
#             topics = driver.find_elements(By.CSS_SELECTOR, "table.table.table-condensed.table-fixed tr a")

#             if not topics:
#                 print("No topics found. Are you sure you're logged in?")
#                 return

#             # 8. Iterate through each topic
#             for index, topic in enumerate(topics):
#                 try:
#                     # Re-fetch topics to avoid stale element exception
#                     topics = driver.find_elements(By.CSS_SELECTOR, "table.table.table-condensed.table-fixed tr a")
#                     topic = topics[index]  # Update reference to the current topic

#                     # Extract the topic title and URL
#                     topic_title = topic.text
#                     print(f"Accessing Topic: {topic_title}")

#                     # Click the topic link
#                     topic.click()
#                     time.sleep(2)  # Wait for the topic page to load

#                     # Scrape topic content
#                     page_source = driver.page_source
#                     soup = BeautifulSoup(page_source, "html.parser")

#                     # Example: Extract content from the topic page
#                     content_div = soup.find("div", class_="message")  # Adjust selector as needed
#                     if content_div:
#                         print("Topic Content:", content_div.get_text(strip=True))

#                     # Go back to the topics page
#                     driver.back()
#                     time.sleep(2)

#                 except Exception as e:
#                     print(f"Error accessing topic {index + 1}: {e}")

#             # 9. Check for the "Next" button to navigate to the next page
#             try:
#                 next_button = driver.find_element(By.XPATH, "/html/body/div[4]/div[2]/div[2]/div/div/div[6]/div/div/ul/li[7]/a")
#                 if next_button:
#                     next_button.click()
#                     time.sleep(3)  # Wait for the next page to load
#                 else:
#                     print("No more pages to navigate.")
#                     break
#             except Exception as e:
#                 print("No 'Next' button found or an error occurred:", e)
#                 break

#     finally:
#         # Close the browser
#         print("Closing the browser in 5 seconds...")
#         time.sleep(5)
#         driver.quit()

# # Example usage:
# if __name__ == "__main__":
#     USERNAME = "allan.ascencio@gmail.com"
#     PASSWORD = "Sah%b5BGn9TBgia"
#     scrape_groups_io_with_selenium(USERNAME, PASSWORD)

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def scrape_groups_io_with_selenium(username, password):
    # 1. Create a Chrome browser instance (NON-HEADLESS)
    driver = webdriver.Chrome()  # Ensure chromedriver is on your system PATH or provide the executable path.

    try:
        # 2. Go to the login page
        driver.get("https://groups.io/login")
        time.sleep(2)  # Wait for the page to load

        # 3. Fill in the login form
        email_input = driver.find_element(By.ID, "email")
        password_input = driver.find_element(By.ID, "password")

        email_input.send_keys(username)
        password_input.send_keys(password)

        # 4. Click the Log In button
        login_button = driver.find_element(By.ID, "loginbutton")
        login_button.click()

        # 5. Wait for login to complete
        time.sleep(3)

        # 6. Navigate to topics page
        driver.get("https://groups.io/topics")
        time.sleep(3)

        while True:
            # 7. Retrieve the topic links
            topics = driver.find_elements(By.CSS_SELECTOR, "table.table.table-condensed.table-fixed tr a")

            if not topics:
                print("No topics found. Are you sure you're logged in?")
                return

            # 8. Iterate through each topic
            for index, topic in enumerate(topics):
                try:
                    # Re-fetch topics to avoid stale element exception
                    topics = driver.find_elements(By.CSS_SELECTOR, "table.table.table-condensed.table-fixed tr a")
                    topic = topics[index]  # Update reference to the current topic

                    # Ensure the topic is visible
                    driver.execute_script("arguments[0].scrollIntoView(true);", topic)

                    # Wait until the topic is clickable
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "table.table.table-condensed.table-fixed tr a")))

                    # Extract the topic title and URL
                    topic_title = topic.text
                    print(f"Accessing Topic: {topic_title}")

                    # Click the topic link
                    try:
                        topic.click()
                    except Exception as e:
                        print(f"Retrying click due to: {e}")
                        driver.execute_script("arguments[0].click();", topic)

                    time.sleep(2)  # Wait for the topic page to load

                    # Scrape topic content
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")

                    # Example: Extract content from the topic page
                    content_div = soup.find("div", class_="message")  # Adjust selector as needed
                    if content_div:
                        print("Topic Content:", content_div.get_text(strip=True))

                    # Go back to the topics page
                    driver.back()
                    time.sleep(2)

                except Exception as e:
                    print(f"Error accessing topic {index + 1}: {e}")

            # 9. Check for the "Next" button to navigate to the next page
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "/html/body/div[4]/div[2]/div[2]/div/div/div[6]/div/div/ul/li[7]/a"))
                )
                if next_button:
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    next_button.click()
                    time.sleep(3)  # Wait for the next page to load
                else:
                    print("No more pages to navigate.")
                    break
            except Exception as e:
                print("No 'Next' button found or an error occurred:", e)
                break

    finally:
        # Close the browser
        print("Closing the browser in 5 seconds...")
        time.sleep(5)
        driver.quit()

# Example usage:
if __name__ == "__main__":
    USERNAME = "EMAIL"
    PASSWORD = "PASWORD"
    scrape_groups_io_with_selenium(USERNAME, PASSWORD)
