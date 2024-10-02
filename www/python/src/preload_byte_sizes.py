import requests
import pandas as pd
from tqdm import tqdm
import json

# Load TSV data
df = pd.read_csv("data/talk_pages_with_importance_and_qids.tsv", sep="\t")

# Extract titles and QIDs
titles = df["title"].tolist()
qids = df["qid"].tolist()

# Function to fetch article sizes using MediaWiki API
def fetch_article_sizes(titles, chunk_size=50):
    api_url = "https://en.wikipedia.org/w/api.php"
    qid_to_size = {}

    print(f"Fetching article sizes for {len(titles)} articles in chunks of {chunk_size}.")
    
    for i in tqdm(range(0, len(titles), chunk_size), desc="Fetching from Wikipedia API"):
        title_chunk = titles[i : i + chunk_size]
        titles_str = "|".join(title_chunk)

        params = {
            "action": "query",
            "titles": titles_str,
            "prop": "revisions",
            "rvprop": "size",
            "format": "json"
        }

        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if "revisions" in page_info:
                    title = page_info.get("title", "")
                    size = page_info["revisions"][0].get("size", 0)
                    qid = df[df["title"] == title]["qid"].values[0]
                    qid_to_size[qid] = size
                else:
                    print(f"Article not found for title: {page_info.get('title', '')}")
                    
        except requests.RequestException as e:
            print(f"Error fetching data for chunk {i // chunk_size + 1}: {e}")
            continue

    return qid_to_size

# Fetch the byte sizes for all articles
qid_to_size = fetch_article_sizes(titles)

# Save the results to a file (JSON or CSV)
output_file = "qid_to_byte_sizes.json"
with open(output_file, "w") as f:
    json.dump(qid_to_size, f)

print(f"Preloaded byte sizes saved to {output_file}")
