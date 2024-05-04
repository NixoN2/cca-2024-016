$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"

$memcacheServer = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(memcache-server-)\S+') {
        $matches[0]
    }
}

$memcacheServerIP = ($nodesOutput -split "`n" | Where-Object { $_ -match '^(memcache-server-)\S+' } | ForEach-Object { ($_ -split '\s+')[5] }).Trim()

Write-Host "memcache-server:" $memcacheServer
Write-Host "memcache-server ip:" $memcacheServerIP


$remoteCommand = @"
sudo -S usermod -aG docker ubuntu;
"@


# Define the gcloud command to SSH into the memcache server and execute remote commands
$gcloudCommand = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$memcacheServer --zone europe-west3-a --command "$remoteCommand"
"@

Invoke-Expression -Command $gcloudCommand

