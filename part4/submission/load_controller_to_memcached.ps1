# Define the local file path of scheduler_controller.py
$localFilePath = "./scheduler_controller.py"
$remoteDirectoryPath = "/"
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"
$nodesOutput = kubectl get nodes -o wide

$memcacheServer = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(memcache-server-)\S+') {
        $matches[0]
    }
}

# Use gcloud compute scp to copy the file to the remote machine
$copyCommand = @"
gcloud compute scp --ssh-key-file ${sshKeyFile} ${localFilePath} ubuntu@${memcacheServer}:controller --zone europe-west3-a
"@

Invoke-Expression -Command $copyCommand
