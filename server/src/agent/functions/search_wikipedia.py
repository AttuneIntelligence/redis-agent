import wikipedia
from wikipedia.exceptions import DisambiguationError, PageError

def search_wikipedia(query, 
                     n_results=3):
    max_abstract_len = 3000
    
    ### `n_results` IS IRRELEVANT, AS THIS FUNCTION RETURNS 1 RESULT -- NEEDED FOR STATIC METHOD
    try:
        result = wikipedia.page(query)
        trimmed_summary = result.summary
        if len(trimmed_summary) > max_abstract_len:
            trimmed_summary = f"{trimmed_summary[:max_abstract_len]} ..."
        return [{
            'title': result.title,
            'url': result.url,
            'description': trimmed_summary,
            'source': 'Wikipedia',
            'reference_link': f":orange_book: [{result.title}]({result.url})"
        }]
    except DisambiguationError as e:
        return [{
            'title': f'The search of Wikipedia for "{query}" resulted in a disambiguation error.',
            'description': f'Which of the following entities are you referring to? {e.options}',
            'source': 'Wikipedia'
        }]
    except PageError:
        return [{
            'title': f'The search of Wikipedia for "{query}" resulted in a page error.',
            'description': 'No matching page was found.',
            'source': 'Wikipedia'
        }]
    except Exception as e:
        return [{
            'title': f'The search of Wikipedia for "{query}" resulted in an unexpected error.',
            'description': str(e),
            'source': 'Wikipedia'
        }]