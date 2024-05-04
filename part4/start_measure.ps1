$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"

# Extracting the internal IP of the memcache-server
$memcacheServerIP = ($nodesOutput -split "`n" | Where-Object { $_ -match '^(memcache-server-)\S+' } | ForEach-Object { ($_ -split '\s+')[5] }).Trim()

Write-Host "memcache-server internal IP:" $memcacheServerIP

$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"


$clientMeasure = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(client-measure-)\S+') {
        $matches[0]
    }
}

Write-Host "client-measure:" $clientMeasure

$clientAgentIP = ""

$nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(client-agent-\S+)\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+\.\d+\.\d+\.\d+)\s+\S+\s+\S+\s+') {
        $clientAgentIP = $matches[2]
    }
}

Write-Host "Retrieved client agent IP:" $clientAgentIP

$remoteCommandMeasure= @"
cd memcache-perf-dynamic;
./mcperf -s $memcacheServerIP --loadonly;
./mcperf -s $memcacheServerIP -a $clientAgentIP --noload -T 16 -C 4 -D 4 -Q 1000 -c 4 -t 10 --qps_interval 2 --qps_min 5000 --qps_max 100000;
"@

$gcloudCommandMeasure = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$clientMeasure --zone europe-west3-a --command "$remoteCommandMeasure"
"@

$outputFilePath = "mcperf.txt"

Invoke-Expression -Command $gcloudCommandMeasure | Out-File -FilePath $outputFilePath


