# Get the node name from the script parameter
$nameParameter = $args[0]

# Get the list of nodes
$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"


# Parse the output to extract node names starting with the provided parameter
$clientNode = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match "^($nameParameter-)\S+") {
        $matches[0]
    }
}

$remoteCommand = @"
ps;
pkill -f mcperf;
"@


$gcloudCommand = @"
        gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$clientNode --zone europe-west3-a --command "$remoteCommand"
"@

# Output the matching nodes
if ($clientNode) {
    Write-Host "$nameParameter nodes:" $clientNode

    # Execute the gcloud ssh command
    Invoke-Expression -Command $gcloudCommand
} else {
    Write-Host "No matching nodes found for parameter: $nameParameter"
}
