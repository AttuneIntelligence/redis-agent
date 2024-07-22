from pymed import PubMed
import json
import re
import os

def clean_text(input_text):
    cleaned_text = input_text.encode('ascii', 'ignore').decode()
    cleaned_text = bytes(cleaned_text, "utf-8").decode("unicode-escape")
    cleaned_text = re.sub(r'\\(?=")', '', cleaned_text)
    cleaned_text = cleaned_text.replace('\\n', '\n')
    return cleaned_text

def search_pubmed(query,
                  n_results=3):
    ### SETUP PUBMED
    pubmed = PubMed(tool="Redis-Agent", email=os.getenv("PUBMED_EMAIL"))
    pubmed.parameters.update({'api_key': os.getenv("PUBMED_API_KEY")})
    pubmed._rateLimit = 50

    ### API QUERY
    results = pubmed.query(query, max_results=n_results)

    ### COMPILE RESULTS
    pubmed_results = []
    
    for article in results:
        # return article
        article_id = article.pubmed_id
        authors_json = article.authors
        authors = [f"{author['firstname']} {author['lastname']}" for author in authors_json]
        if len(authors) > 3:
            authors = authors[:3]
            authors.append("et. al.")
        try:
            doi = article.doi.split('\n')[0]
        except:
            doi = None
        title = clean_text(article.title)
        # keywords = ""   ### IGNORING KEYWORDS FOR NOW
        # if article.keywords:
        #     keywords_list = [kw for kw in article.keywords if kw]
        #     keywords = '", "'.join(keywords_list)
        publication_date = article.publication_date
        try:
            abstract = clean_text(article.abstract)
            if not abstract:
                continue
            if len(abstract) > 2400:
                abstract = f"{abstract[2400:]} ..."
        except:
            abstract = "No abstract provided."

        paper_result = {
            "title": title,
            "authors": authors,
            "publication_date": str(publication_date),
            "description": abstract,
            "link": doi,
            "source": "Pubmed",
            "reference_link": f"📘 [{title}](https://doi.org/{doi})",
        }
        pubmed_results.append(paper_result)

    if pubmed_results:
        return pubmed_results
    else:
        return "NA"