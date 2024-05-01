$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"

$clientAgentB = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(client-agent-b-)\S+') {
        $matches[0]
    }
}

Write-Host "client-agent-b:" $clientAgentB

$remoteCommandB = @"
cd memcache-perf-dynamic;
./mcperf -T 4 -A;
"@

$gcloudCommandB = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$clientAgentB --zone europe-west3-a --command "$remoteCommandB"
"@

Invoke-Expression -Command $gcloudCommandB
