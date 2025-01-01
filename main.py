# import requests
# from bs4 import BeautifulSoup

# def scrape_groups_io_topics():
#     url = "https://groups.io/topics"
    
#     # 1. Request the web page
#     response = requests.get(url)
#     if not response.ok:
#         print(f"Failed to retrieve the page. Status code: {response.status_code}")
#         return
    
#     # 2. Parse HTML with BeautifulSoup
#     soup = BeautifulSoup(response.text, 'html.parser')
    
#     print(soup)

# if __name__ == "__main__":
#     scrape_groups_io_topics()

import requests
from bs4 import BeautifulSoup

def scrape_groups_io_topics(username, password):
    # 1. Create a requests session
    session = requests.Session()
    
    # 2. Get the login page to fetch CSRF token (and possibly other hidden fields)
    login_page_url = "https://groups.io/login"
    r = session.get(login_page_url)
    
    if not r.ok:
        print("Could not get the login page.")
        return
    
    # Parse out the CSRF token (or any other needed hidden input)
    soup_login = BeautifulSoup(r.text, 'html.parser')
    csrf_input = soup_login.find('input', {'name': 'csrf'})
    if not csrf_input:
        print("Could not find CSRF token on login page.")
        return
    csrf_token = csrf_input.get('value', '')
    
    # 3. Prepare the payload for login
    #    Make sure these names match the actual HTML 'name' attributes in the <form>.
    payload = {
        'email': username,
        'password': password,
        'csrf': csrf_token,
        # if there's a redirect field:
        'r': 'https://groups.io/topics',
        # or any other hidden fields, e.g. 'timezone', etc.
        # 'timezone': ...
    }
    
    # 4. Submit the login form
    post_url = "https://groups.io/login"
    r_post = session.post(post_url, data=payload)
    
    if not r_post.ok:
        print("Login form POST failed.")
        return
    
    # Optional: Check if login was successful by looking for something on the page or in cookies
    # For instance, if the page does NOT have 'Please Log In' text, or if a certain cookie is present:
    if "Please Log In" in r_post.text:
        print("Login may have failed; still seeing the login page text.")
        # You can decide whether to continue or not
        # return

    # 5. Now we are logged in (hopefully). Let's fetch the /topics page:
    topics_url = "https://groups.io/topics"
    topics_response = session.get(topics_url)
    if not topics_response.ok:
        print("Could not get the topics page.")
        return

    # 6. Parse the real topics page
    soup_topics = BeautifulSoup(topics_response.text, 'html.parser')

    # 7. Locate the table with class="table table-condensed table-fixed"
    posts_table = soup_topics.find("table", class_="table table-condensed table-fixed")
    if not posts_table:
        print("Could not find the posts table. It may be that you still aren't authenticated, or the HTML changed.")
        return

    # 8. Extract each row of posts
    #    Typically, you'd see <tr> rows for the listings, but the actual structure may vary.
    rows = posts_table.find_all("tr")
    for row in rows:
        # Example: maybe the post title is in <td><span><a>...
        link_tag = row.find('a')
        if link_tag:
            title = link_tag.get_text(strip=True)
            href = link_tag['href'] if link_tag.has_attr('href') else None

            print("Post Title:", title)
            print("Post URL:", href)
            print("-------")

# Example usage:
if __name__ == "__main__":
    # Replace with your real Groups.io credentials
    scrape_groups_io_topics("allan.ascencio@gmail.com", "Sah%b5BGn9TBgia")
