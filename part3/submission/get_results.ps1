kubectl get pods -o json | Out-File -Encoding utf8 results.json
python get_time.py ./results.json