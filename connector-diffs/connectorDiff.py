import json
import requests
import pandas as pd
import os
import jmespath
import sys
import base64

# when fetching report for "as" lower_environment is always "as"
lower_environment = 'alpha'
higher_environment = 'staging'
team_name = "#is-hydra-team"
github_connector_teams_jmespath = "team"

regions = {
    "alpha": "https://api.es-uswest-alpha-0.aws-uswa.cloudelements.app/v3/element/elements",
    "staging": "https://api.es-euwest-stage-0.aws-euws.cloudelements.app/v3/element/elements",
    "prod": "https://api.es-eunorth-prod-0.aws-eunp.cloudelements.app/v3/element/elements"
}

access_token = os.environ.get('GITHUB_TOKEN')

headers = {
    'Authorization': f'token {access_token}',
    'Accept': 'application/vnd.github.v3+json',
    'X-GitHub-Api-Version': '2022-11-28'
}

github_commit_resp_jmespath = 'commits[*].commit.message'

# Function to read a JSON file and return the content
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def get_environment_elements_config(environment_name):
    url = regions[environment_name]
    response = requests.get(url)
    if response.status_code == 200:
        json_data = response.json()
        # Write the JSON data to a file
        with open('connector-details-' + environment_name + '.json', 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
    else:
        print(f"Error: {response.status_code}, Region: {environment_name}")

def get_environment_data_json(environment_name):
    get_environment_elements_config(environment_name)
    json_array = read_json_file('connector-details-' + environment_name + '.json')
    return [item for item in json_array if item['key'] in matching_values]

def get_as_environment_data_json():
    json_array = read_json_file('connector-details-as.json')
    return [item for item in json_array if item['key'] in matching_values]

def get_changes_file(key, lower_env_ver, higher_env_var):
    url = f'https://api.github.com/repos/cloud-elements/periodic-{key}/compare/{key}@{higher_env_var}...{key}@{lower_env_ver}'
    response = requests.get(url, headers=headers)
    file_name = f'{key}-{higher_env_var}...{lower_env_ver}.json'

    if response.status_code == 200:
        json_data = jmespath.search(github_commit_resp_jmespath, response.json())

        # Write the JSON data to a file
        with open('output/'+file_name, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
        print(f"Completed processing connector: {key}")
    else:
        print(f"Error: {response.status_code}, key: {key}")
        # print(response.text)
    return file_name
    


def compare_environments(lower_environment_name, higher_environment_name):
    if(lower_environment_name == 'as'):
        return as_compare_environments(higher_environment_name)

    lower_environment_objects = get_environment_data_json(lower_environment_name)
    higher_environment_objects = get_environment_data_json(higher_environment_name)

    lower_higher_differences = []
    # Compare the two datasets
    for lower_environment in lower_environment_objects:
        for higher_environment in higher_environment_objects:
            lower_env_ver = lower_environment['latestVersion']
            higher_env_var = higher_environment['latestVersion']
            lower_env_key = lower_environment['key']
            if lower_env_key == higher_environment['key']:
                # Check if latestVersion or hasHttpRequest are different
                if lower_env_ver != higher_env_var or lower_environment['hasHttpRequest'] != higher_environment['hasHttpRequest']:
                    changes_file = get_changes_file(lower_env_key, lower_env_ver, higher_env_var)
                    lower_higher_differences.append({
                        'key': lower_env_key,
                        lower_environment_name + '-version': lower_env_ver,
                        lower_environment_name + '-hasHttpRequest': lower_environment['hasHttpRequest'],
                        higher_environment_name + '-version': higher_env_var,
                        higher_environment_name + '-hasHttpRequest': higher_environment['hasHttpRequest'],
                        'changes' : f'<a href="{changes_file}">{changes_file}</a>'
                    })
    return lower_higher_differences

def as_compare_environments(higher_environment_name):
    as_environment_objects = get_as_environment_data_json()
    higher_environment_objects = get_environment_data_json(higher_environment_name)

    lower_higher_differences = []
    # Compare the two datasets
    for as_environment in as_environment_objects:
        for higher_environment in higher_environment_objects:
            as_env_ver = as_environment['latestVersion']
            higher_env_var = higher_environment['latestVersion']
            as_env_key = as_environment['key']
            if as_env_key == higher_environment['key']:
                # Check if latestVersion or hasHttpRequest are different
                if as_env_ver != higher_env_var: 
                    changes_file = get_changes_file(as_env_key, as_env_ver, higher_env_var)
                    lower_higher_differences.append({
                        'key': as_env_key,
                        'as-version': as_env_ver,
                        higher_environment_name + '-version': higher_env_var,
                        'changes' : f'<a href="{changes_file}">{changes_file}</a>'
                    })
    return lower_higher_differences

def get_team_wise_connectors_json():
    url = 'https://api.github.com/repos/cloud-elements/spartacus2.0/contents/spartacus/src/scripts/connectors_team_mappings.json'
    
    response = requests.get(url, headers=headers)
    file_name = 'connectors_team_mappings.json'

    if response.status_code == 200:
        # Decode the base64 string
        decoded_bytes = base64.b64decode(jmespath.search('content',response.json()))
        # Convert bytes to string
        decoded_content = decoded_bytes.decode('utf-8')
        json_data = extract_team_info(json.loads(decoded_content))
        # Write the JSON data to a file
        with open(file_name, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
        print(f"Completed fetching file: {file_name}")
    else:
        print(f"Failed fetching {file_name}")
        print(response.text)
        sys.exit()
    return read_json_file(file_name)


# Function to extract object for a given team
def extract_team_info(data):
    result = []
    for key, value in data.items():
        if isinstance(value, dict):  # Check if the value is a dictionary
            # Execute JMESPath query on each dictionary
            team = jmespath.search(github_connector_teams_jmespath, value)
            if team == team_name:
                result.append(key)  # Append the first matched result
    return result


def delete_files_in_folder(folder_path):
    try:
        # Iterate through the files in the specified folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            # Check if it's a file (not a directory)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f'Error: {e}')
    print("Completed cleaning the output folder")

delete_files_in_folder("output/")

# result = get_team_wise_connectors_json(data, team_name)

def github_authenticate():
    token = os.environ.get('GITHUB_TOKEN')
    url = 'https://api.github.com/user'

    headers = {
        'Authorization': f'Bearer {token}'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("Autheticated Successfully")
    else:
        print(f"Error: {response}")
        sys.exit()


github_authenticate()

matching_values = get_team_wise_connectors_json()

# lower_higher_differences = as_compare_environments(higher_environment)
lower_higher_differences = compare_environments(lower_environment, higher_environment)

# Convert differences to a DataFrame
df = pd.DataFrame(lower_higher_differences)

difference_html = df.to_html(escape=False, index=False)

results_file = f'output/connector-diff-{lower_environment}-{higher_environment}.html'
with open(results_file, 'w') as f:
    f.write(difference_html)
print (f"Finished generation of {results_file}")
    
# Print the DataFrame with headers
# print(df.to_string(index=False))
