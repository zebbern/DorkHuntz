import random
import requests
from bs4 import BeautifulSoup
from config import USER_AGENTS

def scrape_page(url):
    """
    Fetch the page using a random User-Agent (and optionally a proxy if set in main)
    and return its <title> and meta description.
    If a 429 status is encountered, raise an exception.
    """
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            from __main__ import USE_PROXY, PROXY
        except Exception:
            USE_PROXY, PROXY = False, None
        proxies = {"http": PROXY, "https": PROXY} if USE_PROXY and PROXY else None
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        if response.status_code == 429:
            raise Exception("429 Too Many Requests")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            title = "No Title Found"
            description = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            meta = soup.find("meta", attrs={"name": "description"})
            if meta and meta.get("content"):
                description = meta["content"].strip()
            return title, description
    except Exception as e:
        raise e
    return "No Title Found", ""

def perform_google_dork_search_live(dork, num_results=10, pause=2):
    """
    A generator that yields search results as they are found for the given dork.
    Each result is a dictionary with keys: 'url', 'title', and 'description'.
    """
    try:
        from googlesearch import search
        # Use the 'stop' keyword argument instead of passing num_results as a positional parameter.
        for url in search(dork, stop=num_results, pause=pause):
            title, description = scrape_page(url)
            yield {"url": url, "title": title, "description": description}
    except Exception as e:
        raise e
