from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import os
import json 
from pyalex import config, Works

app = Flask(__name__)

# OpenAlex configuration
config.max_retries = 0
config.retry_backoff_factor = 0.1
config.retry_http_codes = [429, 500, 503]
config.email = "goring@wisc.edu"

def get_publications(limit=1, offset=0):
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
        articletitle = publication.get('articletitle', '')
        authors = publication.get('author', [])
        if doi:
            doi_set.append({'doi': doi, 'authors': authors, 'publicationid': pubid, 'articletitle': articletitle  })
    
    return doi_set

def get_openalex_authors(doi):
    """
    Fetches authorship information for a publication from OpenAlex given a DOI.
    Always returns a tuple (authorships, title) for consistency.
    """
    try:
        full_doi = f"https://doi.org/{doi}"
        alex_result = Works()[full_doi]
        authorships = [i.get('author') for i in alex_result.get('authorships', [])]
        title = alex_result.get('title', 'N/A')  # Default to 'N/A' if no title is found
        return authorships, title
    except Exception as e:
        print(f"Error retrieving authors for DOI {doi}: {e}")
        # Return empty authorships and 'N/A' as placeholders in case of an error
        return [], "N/A"


def pages_to_skip():
    """
    Combines the publication IDs from both 'verified.json' and 'problematic.json',
    removes any duplicates, and sorts the list in ascending order numerically.
    :return: A sorted list of unique publication IDs.
    """
    pub_ids = []

    # Define file names
    file_names = ['verified.json', 'problematic.json']

    # Load publication IDs from both files
    for file_name in file_names:
        if os.path.exists(file_name):
            with open(file_name, 'r') as file:
                data = json.load(file)
                # Append the 'Publication ID' from each item in the JSON data
                pub_ids.extend([item['Publication ID'] for item in data])

    # Remove duplicates, convert to integers, and sort the list numerically
    return sorted(set(int(pub_id) for pub_id in pub_ids))

def get_next_valid_page(current_page, direction, limit=1, skip=None):
    """
    Helper function to find the next or previous valid page with a DOI.
    :param current_page: The current page number
    :param direction: Direction to move ("next" or "prev")
    :param limit: Number of publications to fetch per page
    :param skip: List of pages to skip based on publicationid
    :return: Next valid page number
    """
    if skip is None:
        skip = []

    # Update the current page based on direction
    if direction == 'next':
        current_page += 1
    elif direction == 'prev' and current_page > 1:
        current_page -= 1

    publications = get_publications(limit=limit, offset=(current_page - 1) * limit)

    # Check if the current page contains a DOI or is in the skip list by publication ID
    if not any(pub['doi'] for pub in publications) or any(pub['publicationid'] in skip for pub in publications):
        print(f"Skipping page {current_page}, direction: {direction}")
        return get_next_valid_page(current_page, direction, limit, skip)  # Recursively find next valid page
    
    return current_page

@app.route('/')
def welcome():
    # Determine the first valid page dynamically
    skip = pages_to_skip()
    first_valid_page = get_next_valid_page(0, 'next', skip=skip)  # Start at 0 to find the first valid page
    return render_template('welcome.html', first_page=first_valid_page)



@app.route('/index')
def index():
    # Get the page number from the query parameters (default to 1)
    page = int(request.args.get('page', 1))
    limit = 1  # only one DOI per page
    offset = (page - 1) * limit  # calculating the offset

    # Fetching Neotoma publication data
    publications = get_publications(limit=limit, offset=offset)
    publications_with_comparisons = []

    # For each Neotoma publication, get OpenAlex authors and prepare data for display
    for pub in publications:
        doi = pub.get('doi')
        neotoma_authors = pub.get("authors", [])
        openalex_authors, openalex_title = get_openalex_authors(doi)
        publications_with_comparisons.append({
            'doi': doi,
            'articletitle': pub.get('articletitle'), 
            'neotoma_authors': [(i.get('familyname', '') or '') + ',' + (i.get('givennames', '') or '') for i in neotoma_authors],
            'openalex_authors': openalex_authors,
            'openalex_title': openalex_title,
            'publicationid': pub.get('publicationid')
        })

    # Get the list of pages to skip based on publication IDs
    skip = pages_to_skip()

    # Get next and previous valid pages using the skip list
    next_page = get_next_valid_page(page, 'next', skip=skip)
    prev_page = get_next_valid_page(page, 'prev', skip=skip)

    return render_template('index.html', 
                           publications=publications_with_comparisons, 
                           next_page=next_page, 
                           prev_page=prev_page, 
                           current_page=page)




@app.route('/save-doi')
def save_doi():
    action = request.args.get('action')
    doi = request.args.get('doi')
    publication_id = request.args.get('publicationid')
    authors = request.args.get('authors')
    articletitle = request.args.get('articletitle')
    reason = request.args.get('reason')  # Get the reason from the request
    orcids = request.args.get('orcid')  # Get ORCID from the request

    if action in ["verify", "problematic"] and doi:
        file_name = 'verified.json' if action == "verify" else 'problematic.json'
        try:
            # Create a dictionary for the data to save
            data = {
                "Publication ID": publication_id,
                "Title": articletitle,
                "DOI": doi,
                "Authors": authors,
                "Reason": reason,  # Save the reason to the file
                "ORCIDs": orcids  # Save the ORCIDs to the file
            }

            # Read existing data, or start with an empty list if the file is empty or malformed
            try:
                if os.path.exists(file_name):
                    with open(file_name, 'r') as file:
                        existing_data = json.load(file)
                else:
                    existing_data = []
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []

            # Append the new data
            existing_data.append(data)

            # Write back the updated data to the file
            with open(file_name, 'w') as file:
                json.dump(existing_data, file, indent=4)

            return 'DOI saved successfully!'
        except Exception as e:
            return f'Error: {str(e)}'
    return 'Missing parameters!'

if __name__ == "__main__":
    app.run(debug=True)
