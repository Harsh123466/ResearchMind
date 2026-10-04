from graph.workflow import graph


# Get Topic
topic = input("\nEnter research topic: ")


# Initial State
initial_state = {
    "topic": topic,
    "search_results": "",
    "scraped_content": "",
    "report": "",
    "feedback": "",
    "score": 0,
    "revision_count": 0
}


# Run Research Graph
print("\n" + "=" * 60)
print("MULTI-AGENT RESEARCH SYSTEM STARTED")
print("=" * 60)

final_state = graph.invoke(initial_state)



# Final Report
print("\n" + "=" * 60)
print("FINAL RESEARCH REPORT")
print("=" * 60)

print(final_state["report"])


# Final Critic Score
print("\n" + "=" * 60)
print("FINAL CRITIC FEEDBACK")
print("=" * 60)

print(final_state["feedback"])

print(f"\nFinal Score: {final_state['score']}/10")
