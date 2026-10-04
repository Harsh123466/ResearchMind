from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()



# llm = ChatGroq(
#     model="openai/gpt-oss-120b",
#     temperature=0.2,
#     max_tokens=900
# )
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=0.2,
    max_output_tokens=6000
)



# Critic Prompt
critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a sharp and constructive research critic. Be honest and specific."
    ),
    (
        "human",
        """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""
    ),
])


# Critic Chain
critic_chain = critic_prompt | llm | StrOutputParser()  # LCEL (LangChain Expression Language) : it as a pipeline