$nodesOutput = kubectl get nodes -o wide
$sshKeyFile = "$env:USERPROFILE\.ssh\cloud-computing"
$threads = 2

$memcacheServer = $nodesOutput -split "`n" | ForEach-Object {
    if ($_ -match '^(memcache-server-)\S+') {
        $matches[0]
    }
}

$memcacheServerIP = ($nodesOutput -split "`n" | Where-Object { $_ -match '^(memcache-server-)\S+' } | ForEach-Object { ($_ -split '\s+')[5] }).Trim()

Write-Host "memcache-server:" $memcacheServer
Write-Host "memcache-server ip:" $memcacheServerIP


$remoteCommand = @"
sudo apt update;
sudo apt install -y python3;
sudo apt install -y docker.io;
sudo -S usermod -aG docker ubuntu;
sudo apt install -y memcached libmemcached-tools;
sudo systemctl status memcached;
sudo sed -i 's/-m\s\S*/-m 1024/' /etc/memcached.conf;
sudo sed -i 's/-l\s\S*/-l $memcacheServerIP/' /etc/memcached.conf;
echo '-t $threads' | sudo tee -a /etc/memcached.conf;
cat /etc/memcached.conf;
sudo systemctl restart memcached;
sudo systemctl status memcached;
"@


# Define the gcloud command to SSH into the memcache server and execute remote commands
$gcloudCommand = @"
gcloud compute ssh --ssh-key-file $sshKeyFile ubuntu@$memcacheServer --zone europe-west3-a --command "$remoteCommand"
"@

Invoke-Expression -Command $gcloudCommand

