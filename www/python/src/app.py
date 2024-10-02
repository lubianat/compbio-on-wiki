from flask import Flask, render_template, request
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd
import json

app = Flask(__name__)

# Load TSV data into a DataFrame
df = pd.read_csv("data/talk_pages_with_importance_and_qids.tsv", sep="\t")

# Load preloaded byte sizes from JSON file
with open("data/qid_to_byte_sizes.json", "r") as f:
    qid_to_size = json.load(f)


# Function to query missing articles using SPARQL in chunks
def query_missing_articles_in_chunks(qids, language_code, chunk_size=300):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    # add user agent
    sparql.addCustomHttpHeader("User-Agent", "Mozilla/5.0")
    all_missing_articles = []

    for i in range(0, len(qids), chunk_size):
        qid_chunk = qids[i : i + chunk_size]
        qid_list = " ".join([f"wd:{qid}" for qid in qid_chunk])

        query = f"""
        SELECT ?item ?itemLabel ?en_link WHERE {{
          VALUES ?item {{{qid_list}}}
          FILTER(NOT EXISTS {{
            ?article schema:about ?item ;
                     schema:inLanguage "{language_code}" .
          }})
        ?en_link schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/>; schema:inLanguage "en" . 
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        ?en_link schema:name ?title
        }}
        """

        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        for result in results["results"]["bindings"]:
            qid = result["item"]["value"].split("/")[-1]
            size = qid_to_size.get(qid, "unknown")  # Use preloaded size if available, else 'unknown'

            all_missing_articles.append(
                {
                    "title": result["itemLabel"]["value"],
                    "en_link": result["en_link"]["value"],
                    "qid": qid,
                    "size": size  # Add the size from the preloaded data
                }
            )

    return all_missing_articles


@app.route("/", methods=["GET", "POST"])
def index():
    missing_articles = []
    selected_language = None

    if request.method == "POST":
        selected_language = request.form.get("language")
        # Classify QIDs by importance
        qids_by_importance = {
            "top": df[df["importance"] == "top"]["qid"].tolist(),
            "high": df[df["importance"] == "high"]["qid"].tolist(),
            "mid": df[df["importance"] == "mid"]["qid"].tolist(),
            "low": df[df["importance"] == "low"]["qid"].tolist(),
        }

        # Query for missing articles in the selected language in chunks
        missing_articles = {
            importance: query_missing_articles_in_chunks(qids, selected_language)
            for importance, qids in qids_by_importance.items()
        }

        # Remove qids = "nan"
        missing_articles = {
            importance: [article for article in articles if article["qid"] != "nan"]
            for importance, articles in missing_articles.items()
        }

    return render_template(
        "index.html",
        missing_articles=missing_articles,
        selected_language=selected_language,
    )


if __name__ == "__main__":
    app.run(debug=True)
