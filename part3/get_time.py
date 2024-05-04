import json
import sys
from datetime import datetime

time_format = '%Y-%m-%dT%H:%M:%SZ'

# Ensure that the script is provided with the JSON file path as a command-line argument
if len(sys.argv) < 2:
    print("Usage: python get_time.py <json_file>")
    sys.exit(1)

# Path to the JSON file
json_file_path = sys.argv[1]

json_data = None

try:
    # Open the JSON file with cp1251 encoding
    with open(json_file_path, 'r', encoding='utf-8-sig') as file:
        # Read the content and decode it to Unicode
        content = file.read()
        
        # Load the JSON data
        json_data = json.loads(content)

except FileNotFoundError:
    print(f"File not found: {json_file_path}")
    
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")
    
except Exception as e:
    print(f"Error: {e}")

start_times = []
completion_times = []
for item in json_data['items']:
    name = item['status']['containerStatuses'][0]['name']
    print("Job: ", str(name))
    if str(name) != "memcached":
        try:
            start_time = datetime.strptime(
                    item['status']['containerStatuses'][0]['state']['terminated']['startedAt'],
                    time_format)
            completion_time = datetime.strptime(
                    item['status']['containerStatuses'][0]['state']['terminated']['finishedAt'],
                    time_format)
            print("Job time: ", completion_time - start_time)
            start_times.append(start_time)
            completion_times.append(completion_time)
        except KeyError:
            print("Job {0} has not completed....".format(name))
            sys.exit(0)

if len(start_times) != 7 and len(completion_times) != 7:
    print("You haven't run all the PARSEC jobs. Exiting...")
    sys.exit(0)

print("Total time: {0}".format(max(completion_times) - min(start_times)))
file.close()
