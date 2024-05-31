
import concurrent.futures
import requests
import json
import pandas as pd
from ratelimiter import RateLimiter
import json
import os
import requests
import pandas as pd
import regex as re
import json
import pandas as pd

# json of tv ids
file_path = r'tv_series_ids_05_25_2024.json'

json_objects = []

with open(file_path, 'r', encoding='utf-8') as file:
    for line in file:
        try:
            json_object = json.loads(line.strip())
            json_objects.append(json_object)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON on line: {line.strip()}")
            print(f"Error message: {e}")


tvname_df_dict = {'id': [], 'original_name': [], 'popularity': []}

# iterate over the list of dictionaries
for obj in json_objects:
    tvname_df_dict['id'].append(obj['id'])
    tvname_df_dict['original_name'].append(obj['original_name'])
    tvname_df_dict['popularity'].append(obj['popularity'])

tvname_df = pd.DataFrame(tvname_df_dict)


url = "https://api.themoviedb.org/3/authentication"
API_KEY = os.getenv("API_KEY")

headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get(url, headers=headers)

print(response.text)

def tv_credits_API(id):

    # url endpoint
    url = f"https://api.themoviedb.org/3/tv/{id}/aggregate_credits"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    response = requests.get(url, headers=headers)

    return(response.text)



main_data = []
director_lookup_data = []
composer_lookup_data = []



patterncomposer = re.compile(r'\b(.*composer.*|.*music.*|.*Music.*|.*Composer.*)\b', re.IGNORECASE)
patterndirector = re.compile(r'\b(.*director.*|.*director.*)\b', re.IGNORECASE)


main_data = []
main_data_full = {}
director_lookup_data = []
composer_lookup_data = []


def fetch_tv_credits(tv_id): # get request to api
    url = f"https://api.themoviedb.org/3/tv/{tv_id}/aggregate_credits"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    response = requests.get(url, headers=headers)
    return tv_id, response.text

def process_tv_credits(tv_id, tv_credits): # processing the json data that is recieved from the api
    composers = []
    directors = []
    composerroles = {}

    dict_object = json.loads(tv_credits)
    crew_members = dict_object.get('crew', [])

    for crew_member in crew_members: # loops over every member of the crew and appends them to the list of composers/directors if they happen to be one.
        if 'jobs' in crew_member and isinstance(crew_member['jobs'], list):
            for job in crew_member['jobs']:
                if 'job' in job:
                    job_title = job['job']
                    if patterncomposer.search(job_title):
                        composer_id = crew_member['id']
                        composername = crew_member['name']
                        composerroles[composer_id] = job_title
                        composers.append(composer_id)
                        composer_lookup_data.append({'composer_id': composer_id, 'composer_name': composername})
                    if patterndirector.search(job_title):
                        director_id = crew_member['id']
                        directors.append(director_id)
                        director_lookup_data.append({'director_id': director_id, 'director_name': crew_member['name']})

    main_data.append({
        'tv_id': tv_id,
        'composers': composers,
        'directors': directors,
        'composer_roles': composerroles
    })

    main_data_full[tv_id] = dict_object


def fetch_and_process_all_tv_credits(tv_ids): # querying the api in parllel, with rate limiting. this is necessary as the slow part of the script is waiting for the api to respond. the actual computation is very fast.
    rate_limiter = RateLimiter(max_calls=5, period=1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_tv_id = {}
        for tv_id in tv_ids:
            if int(tv_id) % 500 == 0:
              print(f"processing TV id: {tv_id}")
            with rate_limiter:
                future = executor.submit(fetch_tv_credits, tv_id)
                future_to_tv_id[future] = tv_id

        for future in concurrent.futures.as_completed(future_to_tv_id):
            tv_id = future_to_tv_id[future]
            try:
                tv_id, tv_credits = future.result()
                process_tv_credits(tv_id, tv_credits)
            except Exception as exc:
                print(f"TV ID {tv_id} generated an exception: {exc}")


fetch_and_process_all_tv_credits(tvname_df['id'])


main_df = pd.DataFrame(main_data)
directorname_lookup = pd.DataFrame(director_lookup_data).drop_duplicates(subset=['director_id'])
composername_lookup = pd.DataFrame(composer_lookup_data).drop_duplicates(subset=['composer_id'])


print("Main DataFrame:")
print(main_df.head())

print("\nDirector Name Lookup DataFrame:")
print(directorname_lookup)

print("\nComposer Name Lookup DataFrame:")
print(composername_lookup)

main_df.to_csv("main_df.csv", index = False)
directorname_lookup.to_csv("directorname_lookup.csv", index = False)
composername_lookup.to_csv("composername_lookup.csv", index = False)


with open('result.json', 'w') as fp:
    json.dump(main_data_full, fp) # some backup data in case the main results dont work