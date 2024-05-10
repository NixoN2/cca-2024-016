import pandas as pd
import re
import os

script_dir = os.getcwd()
data_dir = os.path.join(script_dir, "..", "runs")

run_data = {}
pattern = r"Job:\s+(\S+)\s+Job time:\s+(\d+:\d+:\d+)"

print("Extracting Execution Times...")

for i in range(3):
    run_identifier = f"{i+1}"
    run_dir = os.path.join(data_dir, f"{i+1}", "time.txt")
    
    with open(run_dir, "r", encoding='utf-16') as file:
        content = file.read()

    matches = re.findall(pattern, content)

    job_times = {}
    for match in matches:
        job_name = match[0]
        job_name = job_name[7:]
        time = match[1]
        job_times[job_name] = time
    
    run_data[run_identifier] = job_times

print("Analysing Execution Times...")
time_df = pd.DataFrame(run_data)
time_df = time_df.apply(pd.to_timedelta).map(lambda x: x.total_seconds())
total_row = pd.DataFrame(time_df.sum(axis=0)).T
total_row.index=['total time']
time_df = pd.concat([time_df, total_row])
time_df['mean'] = time_df.mean(axis=1)
time_df['std_dev'] = time_df.std(axis=1, ddof=2)

print("Exporting Analysed Data...")
time_df.to_csv("execution_times.csv")
print("Script Run Successfully")