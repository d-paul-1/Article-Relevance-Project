from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import os
from pyalex import config, Works

app = Flask(__name__)

# OpenAlex configuration
config.max_retries = 0
config.retry_backoff_factor = 0.1
config.retry_http_codes = [429, 500, 503]
config.email = "goring@wisc.edu"

# Ensure 'verified.txt' and 'problematic.txt' exist
verified_file = "verified.txt"
problematic_file = "problematic.txt"

for file in [verified_file, problematic_file]:
    if not os.path.exists(file):
        open(file, 'w').close()


def get_publications(limit=1, offset=0):  # Default to 1 publication per page
    """
    Fetches DOI and author data from the Neotoma database.
    """
    url = 'https://api.neotomadb.org/v2.0/data/publications'
    response = requests.get(url, params={'limit': limit, 'offset': offset})
    
    if response.status_code == 200:
        pub_data = response.json().get('data', {}).get('result', [])
    else:
        return []

    doi_set = []
    for item in pub_data:
        publication = item.get('publication', {})
        doi = publication.get('doi')
        pubid = publication.get('publicationid', '')
        authors = publication.get('author', [])  # Assuming author data is available here
        if doi:
            doi_set.append({'doi': doi, 'authors': authors, 'publicationid': pubid})
    
    return doi_set


def get_openalex_authors(doi):
    """
    Fetches authorship information for a publication from OpenAlex given a DOI.
    """
    try:
        full_doi = f"https://doi.org/{doi}"
        alex_result = Works()[full_doi]
        authorships = [i.get('author') for i in alex_result.get('authorships', [])]
        return authorships
    except Exception as e:
        print(f"Error retrieving authors for DOI {doi}: {e}")
        return ["Error retrieving authors"]


@app.route('/')
def index():
    # Get the page number from the query parameters (default to 1)
    page = int(request.args.get('page', 1))
    limit = 1 # only one DOI per page
    offset = (page - 1) * limit  # calculating the offset

    # fetching Neotoma publication data
    publications = get_publications(limit=limit, offset=offset)
    publications_with_comparisons = []

    # for each Neotoma publication, get OpenAlex authors and prepare data for display
    for pub in publications:
        doi = pub.get('doi')
        neotoma_authors = pub.get("authors", [])
        openalex_authors = get_openalex_authors(doi)
        publications_with_comparisons.append({
            'doi': doi,
            'neotoma_authors': [(i.get('familyname', '') or '') + ',' + (i.get('givennames', '') or '') for i in neotoma_authors],
            'openalex_authors': openalex_authors,
            'publicationid': pub.get('publicationid')
        })

    # Determine if next/previous page is available
    next_page = page + 1
    prev_page = page - 1 if page > 1 else 1


    # rendering data in index.html
    return render_template('index.html', publications= publications_with_comparisons, next_page=next_page, prev_page=prev_page, current_page=page)

@app.route('/save-doi')
def save_doi():
    # getting the action, DOI, and puboication ID from the query parameters
    action = request.args.get('action')
    doi = request.args.get('doi')
    publication_id= request.args.get('publicationid')
    authors = request.args.get('authors')

     # saving the characteristcs intto its respected text file
    if action == "verify" and doi:
        try:
            with open('verified.txt', 'a') as file:
                file.write(f"\nPublication ID: {publication_id}\nDOI: {doi}\nAuthors: {authors}\n")
            return 'DOI saved successfully!'
        except Exception as e:
            return f'Error: {str(e)}'
        
    elif action == "problematic" and doi:
        try:
            with open('problematic.txt', 'a') as file:
                file.write(f"\nPublication ID: {publication_id}\nDOI: {doi}\nAuthors: {authors}\n")
        except Exception as e:
            return f'Error: {str(e)}' 
    else:
        return 'Missing parameters!'
    

if __name__ == "__main__":
    app.run(debug=True)
