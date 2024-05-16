$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"

# Parse the output to extract node names starting with client-agent-a-, client-agent-b-, and client-measure-
$nodeNames = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(client-agent-a-|client-agent-b-|client-measure-)\S+') {
        $matches[0]
    }
}



foreach ($nodeName in $nodeNames) {
    Write-Host "Running commands for node: $nodeName"

    # Define the SSH command to execute the remote commands
    $remoteCommand = @"
sudo sh -c 'echo deb-src http://europe-west3.gce.archive.ubuntu.com/ubuntu/ jammy main restricted >> /etc/apt/sources.list';
sudo apt-get update;
sudo apt-get install libevent-dev libzmq3-dev git make g++ --yes;
sudo apt-get build-dep memcached --yes;
git clone https://github.com/eth-easl/memcache-perf-dynamic.git;
cd memcache-perf-dynamic;
make
"@

    # Build and execute the gcloud command
    $gcloudCommand = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$nodeName --zone europe-west3-a --command "$remoteCommand"
"@

    Invoke-Expression -Command $gcloudCommand
}
