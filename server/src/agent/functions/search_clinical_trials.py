import requests
import json

def search_clinical_trials(query,
                           n_results=3):
    url = f'https://clinicaltrials.gov/api/v2/studies?query.term={query}'
    response = requests.get(url)
    if response.status_code == 200:
        returned_studies = json.loads(response.text)['studies'][:n_results]
        result = []
        for study in returned_studies:

            ### COMPILE STUDY METADATA
            protocol_section = study['protocolSection']
            id_module = protocol_section['identificationModule']
            description_module = protocol_section['descriptionModule']
            nctId = id_module.get('nctId')
            title = id_module.get('briefTitle')
            description = description_module.get('briefSummary')
            if nctId:
                url = f"https://clinicaltrials.gov/ct2/show/{nctId}"
            else:
                url = None
            result.append({
                'title' title,
                'description': description,
                'link': url
            })
        if result:
            return result
        else:
            return f"No clinical trials were found for the search '{query}'. Try again with a different search or use another tool."
    else:
        return f"Search for clinical trials with the search '{query}' returned with a failure."
