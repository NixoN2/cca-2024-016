$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"

$memcacheServer = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(memcache-server-)\S+') {
        $matches[0]
    }
}

Write-Host "memcache-server:" $memcacheServer

$remoteCommand = @"
ls;
cat log20240506_181920.txt;
"@


# Define the gcloud command to SSH into the memcache server and execute remote commands
$gcloudCommand = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$memcacheServer --zone europe-west3-a --command "$remoteCommand"
"@

$output = Invoke-Expression -Command $gcloudCommand

Write-Host $output