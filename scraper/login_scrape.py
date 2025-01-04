import requests
from bs4 import BeautifulSoup
import time
import argparse
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from login import GroupsIOScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Post:
    """Class to store post data"""
    username: str
    text: str
    footer: Optional[str]
    date: str

@dataclass
class Topic:
    """Class to store topic data"""
    title: str
    url: str
    date: str
    num_responses: int
    posts: List[Post]

class TopicScraper(GroupsIOScraper):
    def __init__(self, email: str, password: str):
        super().__init__()
        self.topics_url = "https://groups.io/g/peds-endo/topics"
        self.email = email
        self.password = password
        self.driver = None

    def login(self, email: str, password: str) -> bool:
        try:
            # Clear any existing cookies
            self.session.cookies.clear()
            
            # First get the login page to get any necessary cookies
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url)
            
            # Extract CSRF token if needed
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrf'})
            csrf_token = csrf_input['value'] if csrf_input else ''
            
            # Prepare login data
            login_data = {
                'email': email,
                'password': password,
                'csrf': csrf_token,
                'remember': '1'  # Stay logged in
            }
            
            # Perform login
            response = self.session.post(login_url, data=login_data, allow_redirects=True)
            
            # Verify login success
            if response.url.endswith('/login') or 'Sign In' in response.text:
                logger.error("Login failed")
                return False
            
            logger.info("Login successful")
            
            # Log cookies without trying to access them directly
            logger.info(f"Session cookies after login: {self.session.cookies.get_dict()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def get_topic_list(self, page: int = 1) -> List[Dict]:
        # Verify we have active session before proceeding
        test_response = self.session.get(f"{self.base_url}/g/peds-endo")
        if 'Sign In' in test_response.text or test_response.url.endswith('/login'):
            logger.error("Session expired or not logged in")
            return []
        
        try:
            url = f"{self.topics_url}?p=Created,,,20,{page},0,0"
            logger.info(f"Fetching URL: {url}")
            
            response = self.session.get(url)
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response URL (after potential redirects): {response.url}")
            
            # Wait for initial page load
            time.sleep(3)
            
            # Check if we're actually logged in
            if "Sign In" in response.text or "Log In" in response.text:
                logger.error("Not logged in - redirected to login page")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Log more details about what we're seeing
            logger.info(f"Page title: {soup.title.text if soup.title else 'No title found'}")
            logger.info(f"Found login form: {'Yes' if soup.find('form', {'id': 'loginform'}) else 'No'}")
            logger.info(f"Found topics table: {'Yes' if soup.find('table', {'id': 'records'}) else 'No'}")
            
            # Save the HTML for debugging
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
                logger.info("Saved HTML to debug_page.html for inspection")
            
            # Find the topics table
            topics_table = soup.find('table', {'id': 'records'})
            if not topics_table:
                logger.error("Could not find topics table in HTML")
                return []
            
            topics = []
            # Process each topic row
            for row in topics_table.find_all('tr'):
                try:
                    # Get the topic link and title
                    topic_link = row.find('a', {'class': 'subject'})
                    if not topic_link:
                        continue
                        
                    # Get the topic metadata
                    attribution = row.find('span', {'class': 'thread-attribution'})
                    if not attribution:
                        continue
                        
                    # Extract date
                    date_span = attribution.find('span', {'title': True})
                    date = date_span['title'] if date_span else None
                    
                    # Get number of responses
                    responses_cell = row.find('td', {'class': 'hidden-xs'})
                    num_responses = int(responses_cell.text.strip()) if responses_cell else 0
                    
                    # Create topic dict
                    topic = {
                        'title': topic_link.text.strip(),
                        'url': topic_link['href'],
                        'date': date,
                        'author': attribution.text.split('Started by')[1].split('@')[0].strip(),
                        'responses': num_responses
                    }
                    topics.append(topic)
                    
                except Exception as e:
                    logger.error(f"Error processing topic row: {str(e)}")
                    continue
                
            return topics
            
        except Exception as e:
            print(f"Error getting topic list: {e}")
            return []

    def get_posts_from_topic(self, topic_url: str) -> List[Post]:
        """Get all posts from a topic"""
        try:
            response = self.session.get(topic_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            posts = []
            for post_div in soup.find_all('div', class_='table-background-color expanded-message'):
                try:
                    # Get username
                    username_elem = post_div.find('u')
                    username = username_elem.text.strip() if username_elem else "Unknown"
                    
                    # Get post content
                    content_div = post_div.find('div', class_='user-content')
                    text = content_div.text.strip() if content_div else ""
                    
                    # Get footer if exists
                    footer = None
                    footer_div = content_div.find('div', id='appendonsend')
                    if footer_div and footer_div.text.strip():
                        footer = footer_div.text.strip()
                        
                    # Get date
                    date_elem = post_div.find('span', title=True)
                    date = date_elem.text.strip() if date_elem else ""
                    
                    posts.append(Post(
                        username=username,
                        text=text,
                        footer=footer,
                        date=date
                    ))
                    
                except Exception as e:
                    logger.error(f"Error parsing post: {str(e)}")
                    continue
                    
            return posts
            
        except Exception as e:
            logger.error(f"Error getting posts from topic: {str(e)}")
            return []

    def scrape_topics(self, max_topics: int = None) -> List[Topic]:
        """Main scraping function"""
        all_topics = []
        page = 1
        topics_scraped = 0
        
        try:
            while True:
                # Get topics from current page
                topics = self.get_topic_list(page)
                if not topics:
                    break
                    
                # Process each topic
                for topic in topics:
                    try:
                        logger.info(f"Scraping topic: {topic['title']}")
                        
                        # Get posts for the topic
                        posts = self.get_posts_from_topic(topic['url'])
                        
                        # Create Topic object
                        topic_obj = Topic(
                            title=topic['title'],
                            url=topic['url'],
                            date=topic['date'],
                            num_responses=topic['responses'],
                            posts=posts
                        )
                        
                        all_topics.append(topic_obj)
                        topics_scraped += 1
                        
                        # Check if we've reached the maximum
                        if max_topics and topics_scraped >= max_topics:
                            return all_topics
                            
                        # Be nice to the server
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error processing topic: {str(e)}")
                        continue
                
                page += 1
                
            return all_topics
            
        except Exception as e:
            logger.error(f"Error in scrape_topics: {str(e)}")
            return all_topics
        
        finally:
            if self.driver:
                self.driver.quit()

def main():
    # Replace with your credentials
    EMAIL = "allan.ascencio@gmail.com"
    PASSWORD = "Sah%b5BGn9TBgia"
    MAX_TOPICS = 10  # Set to None for unlimited
    OUTPUT_FILE = "output.json"
    
    # Initialize scraper
    scraper = TopicScraper(EMAIL, PASSWORD)
    
    # Login
    if not scraper.login(EMAIL, PASSWORD):
        logger.error("Failed to login. Exiting.")
        return
        
    # Scrape topics
    topics = scraper.scrape_topics(MAX_TOPICS)
    
    # Convert to dictionary for JSON serialization
    output_data = []
    for topic in topics:
        topic_dict = {
            'title': topic.title,
            'url': topic.url,
            'date': topic.date,
            'num_responses': topic.num_responses,
            'posts': [{
                'username': post.username,
                'text': post.text,
                'footer': post.footer,
                'date': post.date
            } for post in topic.posts]
        }
        output_data.append(topic_dict)
    
    # Save to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Scraped {len(topics)} topics. Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()