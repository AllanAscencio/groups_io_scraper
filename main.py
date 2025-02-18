import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin

def scrape_groups_io_topics(username, password):
    # Create a requests session
    session = requests.Session()
    
    # Get the login page to fetch the CSRF token
    login_page_url = "https://groups.io/login"
    r = session.get(login_page_url)
    if not r.ok:
        print("Could not get the login page.")
        return
    soup_login = BeautifulSoup(r.text, 'html.parser')
    csrf_input = soup_login.find('input', {'name': 'csrf'})
    if not csrf_input:
        print("Could not find CSRF token on login page.")
        return
    csrf_token = csrf_input.get('value', '')
    
    # Prepare the payload for login
    payload = {
        'email': username,
        'password': password,
        'csrf': csrf_token,
        'r': 'https://groups.io/topics'
    }
    
    # Submit the login form
    post_url = "https://groups.io/login"
    r_post = session.post(post_url, data=payload)
    if not r_post.ok:
        print("Login form POST failed.")
        return
    if "Please Log In" in r_post.text:
        print("Login may have failed; still seeing the login page text.")
    
    # Now scrape topics pages starting from the homepage
    start_url = "https://groups.io/topics"
    posts_data = scrape_topics_pages(session, start_url)
    
    # Save the scraped data to a JSON file
    with open("scraped_posts.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, indent=4, ensure_ascii=False)
    
    print("Scraping complete. Data saved to scraped_posts.json")

def scrape_topics_pages(session, start_url):
    """
    Loop over the topics pages (using pagination) and collect posts.
    """
    posts_data = []
    next_page_url = start_url
    page_counter = 1
    while next_page_url:
        print(f"Scraping topics page {page_counter}: {next_page_url}")
        r = session.get(next_page_url)
        if not r.ok:
            print(f"Failed to load topics page: {next_page_url}")
            break
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find the posts table
        posts_table = soup.find("table", class_="table table-condensed table-fixed")
        if posts_table:
            rows = posts_table.find_all("tr")
            for row in rows:
                link_tag = row.find('a')
                if link_tag:
                    title = link_tag.get_text(strip=True)
                    href = link_tag.get('href', None)
                    if href:
                        post_url = href if href.startswith("http") else urljoin("https://groups.io", href)
                        print("  Scraping post:", title)
                        main_post, comments = scrape_post_details(session, post_url)
                        post_info = {
                            "title": title,
                            "url": post_url,
                            "main_post": main_post,
                            "comments": comments
                        }
                        posts_data.append(post_info)
        else:
            print("No posts table found on this page.")
        
        # Find the pagination area and determine if a next page exists.
        next_page_url = None
        pagination = soup.find("ul", class_="pagination")
        if pagination:
            # Look for an anchor whose href contains 'next='
            next_anchor = pagination.find("a", href=lambda h: h and "next=" in h)
            if next_anchor:
                next_page_url = urljoin("https://groups.io", next_anchor['href'])
        page_counter += 1
    return posts_data

def scrape_post_details(session, post_url):
    """
    Fetch the post page and extract the main post and comments.
    This function looks for all table rows in the table with id "records" that contain a div with class "user-content".
    The first such row is assumed to be the main post.
    """
    response = session.get(post_url)
    if not response.ok:
        print(f"Failed to retrieve post page: {post_url}")
        return None, None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    records_table = soup.find("table", id="records")
    if not records_table:
        print("Could not find the records table on the post page.")
        return None, None
    
    # Collect all rows that have a "user-content" div
    all_rows = records_table.find_all("tr")
    message_rows = [row for row in all_rows if row.find("div", class_="user-content")]
    
    if not message_rows:
        print("No message rows found in the records table.")
        return None, None
    
    main_post = extract_message_text_from_row(message_rows[0])
    comments = []
    for row in message_rows[1:]:
        comment_text = extract_message_text_from_row(row)
        if comment_text:
            comments.append(comment_text)
    
    return main_post, comments

def extract_message_text_from_row(row):
    """
    Extract the text content from a given table row.
    The text is expected to be inside a div with class "user-content".
    """
    content_div = row.find("div", class_="user-content")
    if not content_div:
        return None
    # Remove unwanted elements such as script and style tags.
    for tag in content_div.find_all(["script", "style"]):
        tag.decompose()
    return content_div.get_text(separator="\n", strip=True)

if __name__ == "__main__":
    # Replace with your actual Groups.io credentials
    scrape_groups_io_topics("allan.ascencio@gmail.com", "Sah%b5BGn9TBgia")
