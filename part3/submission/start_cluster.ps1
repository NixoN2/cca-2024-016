kops create secret --name part3.k8s.local sshpublickey admin -i $env:USERPROFILE\.ssh\cloud-computing.pub

kops create -f part3.yaml
kops update cluster --name part3.k8s.local --yes --admin

kops validate cluster --wait 10m
