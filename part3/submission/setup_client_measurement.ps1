$podsOutput = kubectl get pods -o wide
Write-Host $podsOutput

# Regular expression pattern to extract the IP address
$pattern = '(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'

# Match IP address using the pattern
$memcachedIP = [regex]::Match($podsOutput, $pattern).Value

# Output the extracted IP address
Write-Host "Retrieved memcached IP:" $memcachedIP

$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"


$clientMeasure = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(client-measure-)\S+') {
        $matches[0]
    }
}

Write-Host "client-measure:" $clientMeasure

$clientAgentAIP = ""
$clientAgentBIP = ""

# Parse the output to extract internal IPs of client-agent-a and client-agent-b
$nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(client-agent-a-\S+)\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+\.\d+\.\d+\.\d+)\s+\S+\s+\S+\s+') {
        $clientAgentAIP = $matches[2]
    }
    elseif ($_ -match '^(client-agent-b-\S+)\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+\.\d+\.\d+\.\d+)\s+\S+\s+\S+\s+') {
        $clientAgentBIP = $matches[2]
    }
}

Write-Host "Retrieved client agent a IP:" $clientAgentAIP
Write-Host "Retrieved client agent b IP:" $clientAgentBIP

$remoteCommandMeasure= @"
cd memcache-perf-dynamic;
./mcperf -s $memcachedIP --loadonly;
./mcperf -s $memcachedIP -a $clientAgentAIP -a $clientAgentBIP --noload -T 6 -C 4 -D 4 -Q 1000 -c 4 -t 10 --scan 30000:30500:5;
"@

$gcloudCommandMeasure = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$clientMeasure --zone europe-west3-a --command "$remoteCommandMeasure"
"@

$outputFilePath = "mcperf.txt"

Invoke-Expression -Command $gcloudCommandMeasure | Out-File -FilePath $outputFilePath


