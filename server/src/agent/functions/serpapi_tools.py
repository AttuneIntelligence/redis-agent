from serpapi import GoogleSearch
import os

########################################################
### FUNCTION COLLECTION TO QUERY WEB THROUGH SERPAPI ###
########################################################

def search_internet(query,
                    site=None,
                    engine="duckduckgo",
                    n_results=3,
                    emoji=None):
    ### DEFINE INPUT QUERY
    if site:
        query = f"{query} site:{site}"
    
    ### UTILIZE SERPAPI FOR SEARCH
    params = {
        "q": query,
        "engine": engine,
        "api_key": os.getenv("SERPAPI_API_KEY")
    }
    search = GoogleSearch(params)
    search_results = search.get_dict()

    ### PARSE RESULTS TO STRING
    final_results = []
    try:
        if len(search_results['organic_results']) != 0:
            for i in search_results['organic_results'][:n_results]:
                ### DEFINE TITLE
                title = i.get('title', None)
                if not title:
                    continue
                    
                ### DEFINE LINK
                url = i.get('link', None)
                if url:
                    if emoji:
                        link_ref = f"{emoji} [{title}]({url})"
                    else:
                        link_ref = f"&#127760; [{title}]({url})"
                else:
                    link_ref = title
                    
                response = {
                    'title': i.get('title', ''),
                    'url': i.get('link', ''),
                    'description': i.get('snippet', ''),
                    'source': i.get('source', ''),
                    'reference_link': link_ref
                }
                final_results.append(response)
        return final_results
    except:
        return "NA"

### DEFINE SEARCH OF SPECIFIC WEBSITES ###
##########################################
def search_neurips(query, n_results=3):
    return search_internet(query, site="proceedings.neurips.cc")
    
def search_github(query, n_results=3, emoji='&#128008;'):
    github_query = f"{query} repository"
    return search_internet(query, site="github.com", emoji=emoji)

### US PATENT AND TRADEMARK OFFICE ###
def search_us_patent_office(query, n_results=3):
    ### UTILIZE SERPAPI FOR SEARCH OF USPTO
    params = {
        "q": query,
        "engine": "google_patents",
        "api_key": os.getenv("SERPAPI_API_KEY")
    }
    search = GoogleSearch(params)
    search_results = search.get_dict()

    ### PARSE RESULTS TO STRING
    final_results = []
    try:
        if len(search_results['organic_results']) != 0:
            for i in search_results['organic_results'][:n_results]:
                ### DEFINE TITLE
                title = i.get('title', None)
                if not title:
                    continue
                    
                ### DEFINE LINK
                url = i.get('pdf', None)
                if url:
                    link_ref = f"&#128197; [{title}]({url})"
                else:
                    link_ref = title
                    
                response = {
                    'title': title,
                    'url': i.get('pdf', ''),
                    'description': i.get('snippet', ''),
                    'patent_number': i.get('publication_number', ''),
                    'inventor': i.get('inventor', ''),
                    'date_filed': i.get('filing_date', ''),
                    'source': 'US Patent Office',
                    'reference_link': link_ref
                }
                final_results.append(response)
        return final_results
    except:
        return "NA"

### SEARCH GOOGLE SCHOLAR
def search_academic_scholars(query, n_results=3):
    ### DEFINE DISTINCT ENGINE FOR GOOGLE SCHOLAR
    params = {
        "q": query,
        "engine": "google_scholar",
        "api_key": os.getenv("SERPAPI_API_KEY"),
        "num": n_results
    }
    search = GoogleSearch(params)
    results = search.get_dict()

    ### EXTRACT SCHOLARLY DATA
    try:
        data = []
        if not results.get('profiles', {}).get('authors'):
            return "NA"
        else:
            for i in results['profiles']['authors'][:n_results]:
                ### DEFINE TITLE
                title = i.get('title', None)
                if not title:
                    continue
                    
                ### DEFINE LINK
                url = i.get('link', None)
                if url:
                    link_ref = f":mens: [{title}]({url})"
                else:
                    link_ref = title
                    
                response = {
                    'name': title,
                    'affiliation': i.get('affiliations', ''),
                    'n_cited_by': i.get('cited_by', ''),
                    'url': i.get('link', ''),
                    'scholar_id': i.get('author_id', ''),
                    'source': 'Google Scholar',
                    'reference_link': link_ref
                }
                data.append(response)
        return data
    except Exception as e:
        print(f"Error! {e}")
        return "NA"


