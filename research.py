import os
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import time
import sys

# Load the Claude API key from the environment variable.
CLAUDE_API_KEY = os.environ.get("CLAUDE_API")
if not CLAUDE_API_KEY:
    raise Exception("CLAUDE_API key not set in environment variable 'CLAUDE_API'.")

def scrape_page(url, selector=None):
    """
    Fetch the content of a URL and extract text.
    If a CSS selector is provided, extract only matching elements;
    otherwise, extract text from paragraph and heading tags.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/90.0.4430.93 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        if selector:
            elements = soup.select(selector)
        else:
            elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        texts = [el.get_text(strip=True) for el in elements if el.get_text(strip=True)]
        return "\n".join(texts)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def combined_scrape(query, num_urls=3, min_length=100, selector=None):
    """
    For a given query, use Google Search to obtain several URLs,
    scrape each URL’s content (optionally via a CSS selector), and combine the texts.
    Only include content longer than min_length.
    """
    combined_text = ""
    urls = []
    for url in search(query, num_results=num_urls):
        urls.append(url)
    print(f"URLs found for query '{query}': {urls}")
    for url in urls:
        text = scrape_page(url, selector=selector)
        if len(text) >= min_length:
            combined_text += f"--- Content from {url} ---\n{text}\n\n"
        else:
            print(f"Not enough content from {url} (length={len(text)}).")
        time.sleep(1)
    return combined_text if combined_text else "No content found."

def generate_search_queries(section, topic, api_key):
    """
    Uses the Claude API to generate 3 distinct search queries for a section.
    """
    prompt = (
        f"Generate 3 unique and distinct search queries to gather diverse and detailed information on {topic} "
        f"for the research paper section '{section}'. Each query should focus on a different angle or aspect "
        "that would be useful for a comprehensive research paper. Return each query on a separate line."
    )
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 300,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        content = ""
        if "content" in result:
            content_val = result["content"]
            if isinstance(content_val, list):
                content = "\n".join(item.get("text", "") for item in content_val if isinstance(item, dict))
            elif isinstance(content_val, str):
                content = content_val.strip()
        elif "messages" in result and result["messages"]:
            content_val = result["messages"][0].get("content", "")
            if isinstance(content_val, list):
                content = "\n".join(item.get("text", "") for item in content_val if isinstance(item, dict))
            elif isinstance(content_val, str):
                content = content_val.strip()
        queries = [line.strip() for line in content.splitlines() if line.strip()]
        print(f"Generated queries for '{section}': {queries}")
        return queries
    except Exception as e:
        print(f"Error generating search queries for {section}: {e}")
        return [f"{topic} {section}"]

def format_text_with_ai(text, api_key):
    """
    Sends the provided text to the Claude API to remove HTML/formatting and combine
    the content into a detailed, descriptive narrative in academic style.
    The prompt instructs Claude to produce a narrative summary appropriate for a research paper.
    """
    prompt = (
        "Please transform the following text into a detailed, narrative summary in an academic style, "
        "as if writing a section of a research paper. Do not simply produce bullet points; instead, "
        "craft full sentences with coherent paragraphs, integrating the information into a descriptive "
        "and formal narrative. Remove any HTML or formatting tags, and ensure the output is comprehensive.\n\n"
        + text
    )
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 1500,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()
        formatted_text = ""
        if "content" in result:
            content_val = result["content"]
            if isinstance(content_val, list):
                formatted_text = " ".join(item.get("text", "") for item in content_val if isinstance(item, dict))
            elif isinstance(content_val, str):
                formatted_text = content_val.strip()
        elif "messages" in result and result["messages"]:
            content_val = result["messages"][0].get("content", "")
            if isinstance(content_val, list):
                formatted_text = " ".join(item.get("text", "") for item in content_val if isinstance(item, dict))
            elif isinstance(content_val, str):
                formatted_text = content_val.strip()
        return formatted_text if formatted_text else text
    except Exception as e:
        print(f"Error during AI formatting: {e}")
        return text

def ensure_length_limit(text, limit, api_key):
    """
    If the text exceeds the specified character limit, use Claude to rewrite and expand it into a descriptive summary
    in research paper style while keeping the final output under the limit.
    """
    if len(text) <= limit:
        return text
    prompt = (
        f"Please rewrite and elaborate on the following text into a detailed, narrative summary in academic style "
        f"appropriate for a research paper. Ensure that the final output is no longer than {limit} characters. "
        "Do not simply truncate the text; generate a cohesive and descriptive summary that captures the essence "
        "of the original content in full paragraphs.\n\n" + text
    )
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 1500,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        result = response.json()
        summarized_text = ""
        if "content" in result:
            content_val = result["content"]
            if isinstance(content_val, list):
                summarized_text = " ".join(item.get("text", "") for item in content_val if isinstance(item, dict))
            elif isinstance(content_val, str):
                summarized_text = content_val.strip()
        elif "messages" in result and result["messages"]:
            content_val = result["messages"][0].get("content", "")
            if isinstance(content_val, list):
                summarized_text = " ".join(item.get("text", "") for item in content_val if isinstance(item, dict))
            elif isinstance(content_val, str):
                summarized_text = content_val.strip()
        if len(summarized_text) > limit:
            summarized_text = summarized_text[:limit] + " [Content truncated]"
        return summarized_text
    except Exception as e:
        print(f"Error during summarization for length limit: {e}")
        return text[:limit] + " [Content truncated]"

def main():
    # Accept a research prompt from the user.
    if len(sys.argv) > 1:
        research_prompt = " ".join(sys.argv[1:])
    else:
        research_prompt = input("Enter your research prompt: ").strip()
    print(f"Research prompt: {research_prompt}")

    # Define sections for the research paper.
    sections = {
        "Introduction": "Provide an overview and background information on the topic.",
        "Literature Review": "Summarize existing research, key studies, and findings.",
        "Methodology": "Detail the methods, techniques, and tools used in the research.",
        "Results": "Describe the data, findings, and analysis.",
        "Discussion": "Interpret the results, discuss implications, and compare with existing literature.",
        "Conclusion": "Summarize the research, discuss limitations, and suggest future directions."
    }
    
    final_results = {}
    
    # For each section, generate diverse search queries, scrape content, and format it.
    for section, desc in sections.items():
        print(f"\n--- Processing section: {section} ---")
        queries = generate_search_queries(section, research_prompt, CLAUDE_API_KEY)
        aggregated_text = ""
        for q in queries:
            full_query = f"{research_prompt} {q}"
            print(f"Scraping for query: '{full_query}'")
            aggregated_text += combined_scrape(full_query, num_urls=3)
            aggregated_text += "\n"
            time.sleep(1)
        print(f"Aggregated raw content length for {section}: {len(aggregated_text)}")
        formatted_section = format_text_with_ai(aggregated_text, CLAUDE_API_KEY)
        # Ensure each section's output does not exceed 50,000 characters.
        limited_section = ensure_length_limit(formatted_section, 50000, CLAUDE_API_KEY)
        final_results[section] = limited_section
        time.sleep(2)
    
    # Combine all sections into a single research paper.
    research_paper = ""
    for section, content in final_results.items():
        research_paper += f"{section}:\n{content}\n\n" + "="*80 + "\n\n"
    
    output_filename = "resrach_paper_beta_1.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(research_paper)
    
    print(f"\nResearch paper generated and stored in '{output_filename}'.")

if __name__ == "__main__":
    main()