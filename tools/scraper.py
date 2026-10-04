from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
import os
from tavily import TavilyClient
from dotenv import load_dotenv
from rich import print
load_dotenv()



@tool
def web_scrape(url : str) -> str:
    """Scrape and return clean tect content from a given URL for deeper reading."""

    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:3000]
    except Exception as e:
        return f"Could not scrape URL : {str(e)}"