import pandas as pd
import re
import os

script_dir = os.getcwd()
data_dir = os.path.join(script_dir, "..", "runs")

columns = ['type', 'avg', 'std', 'min', 'p5', 'p10', 'p50', 'p67', 'p75', 'p80', 'p85', 'p90', 'p95', 'p99', 'p999', 'p9999', 'QPS', 'target', 'ts_start', 'ts_end']
df = pd.DataFrame(columns=columns)

print("Reading Data...")
for i in range(3):
    run_identifier = f"{i+1}"
    run_dir = os.path.join(data_dir, f"{i+1}", "mcperf.txt")

    rows = []
    with open(run_dir, 'r', encoding='utf-16') as file:
        lines = file.readlines()

    clean_lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]

    for line in clean_lines:
        parts = line.split()
        rows.append(parts)

    mcperf_data = pd.DataFrame(rows, columns=columns)
    mcperf_data["type"] = run_identifier

    df = pd.concat([df, mcperf_data])
    del mcperf_data

for col in df.columns:
    if col != 'type':
        df[col] = pd.to_numeric(df[col], errors='coerce')

print("Calculating Violations...")
violations = (df["p95"]>1000).sum()
data_points = len(df)
print(f"Violations : {violations}, data points : {data_points}, => SLO Violation Fraction = {violations/data_points}")
df.to_csv("memcached_latency.csv", index=False)
print("Latency Data Stored successfully...")