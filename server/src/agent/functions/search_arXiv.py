import arxiv

def search_arXiv(query,
                 n_results=3):
    ### GET SEARCH RESULT
    client = arxiv.Client()
    search = arxiv.Search(
      query = query,
      max_results = 9,
      sort_by = arxiv.SortCriterion.SubmittedDate
    )
    results = client.results(search)
    if not results:
        return None
    
    ### COMPILE TO JSON
    all_arxiv_results = []
    for r in results:
        ### GET LINK
        pdf_link = ""
        for link in r.links:
            if link.title == 'pdf':
                pdf_link = link
                break

        ### GET AUTHORS
        authors = []
        for author in r.authors:
            authors.append(author.name)

        ### GET PUBLICATION DATE
        publication_date = ""
        if r.published:
            publication_date = r.published.strftime("%Y-%m-%d")

        if pdf_link:
            arxiv_json = {
                "title": r.title,
                "description": str(r.summary).replace("\n", " "),
                "publication_date": publication_date,
                "authors": authors,
                "link": str(pdf_link)
            }
            all_arxiv_results.append(arxiv_json)

    return all_arxiv_results[:n_results]