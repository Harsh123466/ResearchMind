from graph.state import ResearchState
from tools.web_search import web_search
from tools.scraper import web_scrape
from agents.writer_agent import writer_chain
from agents.critic_agent import critic_chain
import re


# 1. Search Node
def search_node(state: ResearchState):

    print("\n" + "=" * 50)
    print("STEP 1 - SEARCH AGENT IS WORKING...")
    print("=" * 50)

    search_result = web_search.invoke(
        f"Find recent, reliable and detailed information about: {state['topic']}"
    )

    print("\n Search completed.")

    return {"search_results": search_result}


# 2. Reader Node
def reader_node(state: ResearchState):

    print("\n" + "=" * 50)
    print("STEP 2 - READER AGENT IS SCRAPING...")
    print("=" * 50)

    urls = re.findall(r"https?://\S+", state["search_results"])
    if not urls:
        scraped_content = state["search_results"]
    else:
        scraped_content = web_scrape.invoke(urls[0])

    print("\n Reader completed.")

    return {"scraped_content" : scraped_content}


# 3. Writer Node
def writer_node(state: ResearchState):

    print("\n" + "=" * 50)
    print("STEP 3 - WRITER IS WRITING REPORT...")
    print("=" * 50)

    report = writer_chain.invoke({
        "topic": state["topic"],
        "research": state["scraped_content"],
        "feedback": state["feedback"]
    })

    print("\nWriter completed.")

    return {
        "report": report,
        "revision_count": state.get("revision_count", 0) + 1
    }


# 4. Critic Node
def critic_node(state: ResearchState):

    print("\n" + "=" * 50)
    print("STEP 4 - CRITIC IS REVIEWING...")
    print("=" * 50)

    feedback = critic_chain.invoke({
        "report": state["report"]
    })

    print("\nCritic completed.")
    print("\nCritic Feedback:")
    print(feedback)

    # Extract score
    match = re.search(
        r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10",
        feedback
    )

    score = int(float(match.group(1))) if match else 0

    return {
        "feedback": feedback,
        "score": score
    }
