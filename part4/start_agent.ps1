$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"

$nodeName = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(client-agent-)\S+') {
        $matches[0]
    }
}

$remoteCommand = @"
cd memcache-perf-dynamic;
./mcperf -T 16 -A;
"@

$gcloudCommand = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$nodeName --zone europe-west3-a --command "$remoteCommand"
"@

Invoke-Expression -Command $gcloudCommand