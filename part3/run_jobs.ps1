# Set the path to the folder containing YAML files
$yamlFolderPath = "./jobs"

# Get all YAML files in the folder
$yamlFiles = Get-ChildItem -Path $yamlFolderPath -Filter "*.yaml"

# Iterate through each YAML file
foreach ($yamlFile in $yamlFiles) {
    kubectl create -f $yamlFile.FullName
    $job_name = $yamlFile -replace '.yaml'

    # Wait for the job to complete
    $jobCompleted = $false
    Write-Host $job_name
    $podInfo = kubectl get pods --selector=job-name=$job_name --output=jsonpath='{.items[*].metadata.name}'
    while (-not $jobCompleted) {
        # Check if "[PARSEC] Done" is present in the logs
        $logsContent = kubectl logs $podInfo
        if ($logsContent -match "\[PARSEC\] Done") {
            $jobCompleted = $true
        } else {
            Start-Sleep -Seconds 10  # Wait for 10 seconds before checking again
            Write-Output "Not ready. Sleeping for 10 seconds"
        }
    }

    # Delete the job
    kubectl delete jobs $jobName

    # Delete all pods associated with the job
    kubectl delete pods --selector=job-name=$jobName
}
