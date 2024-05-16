$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"

$nodeName = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(client-agent-)\S+') {
        $matches[0]
    }
}

Write-Host "Node:" $nodeName

$remoteCommand = @"
sudo sh -c 'echo deb-src http://europe-west3.gce.archive.ubuntu.com/ubuntu/ jammy main restricted >> /etc/apt/sources.list';
sudo apt-get update;
sudo apt-get install libevent-dev libzmq3-dev git make g++ --yes;
sudo apt-get build-dep memcached --yes;
git clone https://github.com/eth-easl/memcache-perf-dynamic.git;
cd memcache-perf-dynamic;
make
"@

$gcloudCommand = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$nodeName --zone europe-west3-a --command "$remoteCommand"
"@

Invoke-Expression -Command $gcloudCommand