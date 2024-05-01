$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"

# Parse the output to extract node names starting with client-agent-a-, client-agent-b-, and client-measure-
$clientAgentA = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(client-agent-a-)\S+') {
        $matches[0]
    }
}

Write-Host "client-agent-a:" $clientAgentA


$remoteCommandA = @"
cd memcache-perf-dynamic;
./mcperf -T 2 -A;
"@

$gcloudCommandA = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$clientAgentA --zone europe-west3-a --command "$remoteCommandA"
"@

Invoke-Expression -Command $gcloudCommandA


