"""
Example usage of PromptTrace.
Run this to populate some sample data, then launch the dashboard.
"""

import random
import time
from prompttrace import trace, log_call, dashboard


# ─── Example 1: Using the @trace decorator ───────────────────
@trace(experiment="sentiment-analysis", model="gpt-4o", tags=["prod", "v1"])
def analyze_sentiment(prompt, temperature=0.3):
    """Simulate an LLM call for sentiment analysis."""
    time.sleep(random.uniform(0.1, 0.5))  # simulate latency
    sentiments = ["positive", "negative", "neutral", "mixed"]
    return random.choice(sentiments)


# ─── Example 2: With eval function ───────────────────────────
def eval_summary(prompt, output):
    """Simple eval: score the output length and keyword presence."""
    return {
        "length_score": min(len(output) / 100, 1.0),
        "has_keywords": 1.0 if any(k in output.lower() for k in ["summary", "key", "main"]) else 0.0,
    }


@trace(experiment="summarizer", model="claude-3-sonnet", eval_fn=eval_summary)
def summarize(prompt, max_tokens=200):
    """Simulate a summarization call."""
    time.sleep(random.uniform(0.2, 0.8))
    summaries = [
        "The key findings indicate a strong correlation between variables A and B. Summary of main points suggests further research is needed.",
        "Main takeaway: revenue grew 15% YoY. The summary highlights three critical factors.",
        "In summary, the document outlines a comprehensive strategy for market expansion.",
        "Analysis complete. No significant key trends detected in the dataset.",
    ]
    return random.choice(summaries)


# ─── Example 3: Using log_call manually ──────────────────────
def manual_logging_example():
    """Show how to log calls without the decorator."""
    log_call(
        prompt="Translate the following to French: Hello, how are you?",
        output="Bonjour, comment allez-vous?",
        experiment="translation",
        model="gpt-4o-mini",
        generation_params={"temperature": 0.2, "max_tokens": 100},
        latency_ms=234.5,
        token_count_input=15,
        token_count_output=8,
        tags=["translation", "french"],
    )


# ─── Example 4: Returning a dict with metadata ───────────────
@trace(experiment="qa-bot", model="claude-3-opus")
def answer_question(prompt, temperature=0.7):
    """Return a dict with output + metadata."""
    time.sleep(random.uniform(0.3, 1.0))
    return {
        "output": "The capital of France is Paris. It has been the capital since the 10th century.",
        "token_count_input": 12,
        "token_count_output": 18,
    }


if __name__ == "__main__":
    print("\n🔬 Generating sample traces...\n")

    # Run multiple calls to populate data
    prompts_sentiment = [
        "Analyze the sentiment of: 'I love this product, it changed my life!'",
        "Analyze the sentiment of: 'Terrible experience, would not recommend.'",
        "Analyze the sentiment of: 'The product is okay, nothing special.'",
        "What is the overall sentiment? 'Great quality but too expensive for what you get.'",
    ]

    prompts_summary = [
        "Summarize the following quarterly report for the board meeting...",
        "Please provide a concise summary of this research paper on climate change...",
        "Create an executive summary of the customer feedback data...",
        "Summarize the key points from today's team standup notes...",
    ]

    for _ in range(5):
        for p in prompts_sentiment:
            analyze_sentiment(p, temperature=random.choice([0.1, 0.3, 0.5, 0.7]))

        for p in prompts_summary:
            summarize(p, max_tokens=random.choice([100, 200, 500]))

    manual_logging_example()

    for _ in range(3):
        answer_question("What is the capital of France?", temperature=0.5)
        answer_question("Explain quantum computing in simple terms.", temperature=0.8)

    print("\n✅ Done! Launching dashboard...\n")
    dashboard()