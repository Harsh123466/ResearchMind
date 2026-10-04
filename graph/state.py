from typing import TypedDict


class ResearchState(TypedDict):

    topic: str
    search_results: str
    scraped_content: str
    report: str
    feedback: str
    score: int
    revision_count: int