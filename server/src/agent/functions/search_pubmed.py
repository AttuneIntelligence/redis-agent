from pymed import PubMed
import json
import re

def clean_text(input_text):
    cleaned_text = input_text.encode('ascii', 'ignore').decode()
    cleaned_text = bytes(cleaned_text, "utf-8").decode("unicode-escape")
    cleaned_text = re.sub(r'\\(?=")', '', cleaned_text)
    cleaned_text = cleaned_text.replace('\\n', '\n')
    return cleaned_text

def search_pubmed(query,
                  n_results=3):
    pubmed = PubMed(tool="Redis-Agent", email="reedbender@attuneintelligence.com")   ### REMOVE HARDCODED EMAIL AUTH
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
        keywords = ""
        if article.keywords:
            keywords_list = [kw for kw in article.keywords if kw]
            keywords = '", "'.join(keywords_list)
        publication_date = article.publication_date
        try:
            abstract = clean_text(article.abstract)
            if len(abstract) > 2400:
                abstract = f"{abstract[2400:]} ..."
        except:
            abstract = "No abstract"

        paper_result = {
            "title": title,
            "authors": authors,
            "keywords": keywords,
            "publication_date": str(publication_date),
            "abstract": abstract,
            "link": doi
        }
        pubmed_results.append(paper_result)

    if pubmed_results:
        return pubmed_results
    else:
        return f"No results were returned for the query '{query}'. Try again with another search or use a different tool."