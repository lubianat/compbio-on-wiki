import requests
from pathlib import Path
import re

HERE = Path(__file__).parent.resolve()


def search_talk_pages_with_template():
    url = "https://en.wikipedia.org/w/api.php"

    # Define the initial parameters for the API request
    params = {
        "action": "query",
        "list": "search",
        "srsearch": 'insource:"COMPBIO=yes"',
        "srnamespace": 1,  # Namespace 1 for Talk pages
        "format": "json",
        "srlimit": 500,
    }

    page_info = []

    while True:
        # Send the request to Wikipedia's API
        response = requests.get(url, params=params)

        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            # Extract the search results
            pages = data.get("query", {}).get("search", [])
            for page in pages:
                # Fetch the page title and snippet
                page_title = page["title"].replace("Talk:", "")
                snippet = page["snippet"]

                # Use regex to extract the importance level
                importance_match = re.search(r"COMPBIO-importance=([\w-]+)", snippet)
                importance = (
                    importance_match.group(1) if importance_match else "unknown"
                )

                # Append title and importance to the page_info list
                page_info.append((page_title, importance))

            # Check if there's a continuation parameter
            if "continue" in data:
                params["sroffset"] = data["continue"]["sroffset"]
            else:
                break  # No more pages to retrieve
        else:
            print("Failed to retrieve data from Wikipedia API")
            break

    # Now, let's retrieve the Wikidata QIDs for the titles
    page_info_with_qids = []
    batch_size = 50
    for i in range(0, len(page_info), batch_size):
        batch = page_info[i : i + batch_size]
        titles = [title for title, _ in batch]
        qid_map = get_wikidata_qids(titles)
        for title, importance in batch:
            qid = qid_map.get(title, "N/A")
            page_info_with_qids.append((title, importance, qid))

    # Save the page titles, importances, and QIDs to a TSV file
    file_path = HERE.joinpath("talk_pages_with_importance_and_qids.tsv")
    with file_path.open("w", encoding="utf-8") as f:
        # Write header
        f.write("title\timportance\tqid\n")
        # Write data
        for title, importance, qid in page_info_with_qids:
            f.write(f"{title}\t{importance}\t{qid}\n")

    print(f"Saved {len(page_info_with_qids)} entries to {file_path}")


def get_wikidata_qids(titles):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "pageprops",
        "titles": "|".join(titles),
        "format": "json",
        "ppprop": "wikibase_item",
    }
    response = requests.get(url, params=params)
    qid_map = {}
    if response.status_code == 200:
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            title = page_data.get("title", "")
            qid = page_data.get("pageprops", {}).get("wikibase_item", "N/A")
            title = title.replace("Talk:", "")
            qid_map[title] = qid
    else:
        print(f"Failed to retrieve QIDs from Wikipedia API: {response.status_code}")
    return qid_map


# Run the function to search for pages and retrieve QIDs
search_talk_pages_with_template()
