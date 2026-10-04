from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
import os
from tavily import TavilyClient
from dotenv import load_dotenv
from rich import print
load_dotenv()


tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool
def web_search(query : str) -> str:
    """Search the web for recent and reliable information on a topic. Returns Titles, URLs and Snippets."""

    result = tavily.search(query=query, max_results=5)

    out = []

    for r in result['results']:
        out.append(
            f"Title: {r['title']}\n URL: {r['url']}\n Snippet: {r['content'][:300]}\n"
        )

    return "\n-----\n".join(out)