from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.scraper import web_scrape
from dotenv import load_dotenv

load_dotenv()


# llm = ChatGroq(
#     model="openai/gpt-oss-120b",
#     temperature=0,
#     max_tokens=900
# )
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=0.7,
    max_output_tokens=6000
)


reader_agent = create_agent(
    model=llm,
    tools=[web_scrape]
)