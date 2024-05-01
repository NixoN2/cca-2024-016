# Define directories and arrays
$jobs_directories = @(
    "./parsec-benchmarks/part2b-1",
    "./parsec-benchmarks/part2b-2",
    "./parsec-benchmarks/part2b-4",
    "./parsec-benchmarks/part2b-8"
)
$logs_directory = "./part2b-logs"

if (!(Test-Path $logs_directory -PathType Container)) {
    New-Item -ItemType Directory -Path $logs_directory | Out-Null
    Write-Output "Folder created"
}

# Function to get job file names from a directory and append folder number
function GetJobFileNames($directory) {
    $folderNumber = [regex]::Match($directory, '\d+$').Value
    $fileNames = @()
    if (Test-Path $directory -PathType Container) {
        $files = Get-ChildItem $directory -File
        foreach ($file in $files) {
            $fileNames += $file.Name + "-" + $folderNumber
        }
    } else {
        Write-Output "Directory '$directory' not found."
    }
    return $fileNames
}

# Iterate through each directory, get job file names, and append folder number
$jobs_file_names = foreach ($directory in $jobs_directories) {
    GetJobFileNames $directory
}

foreach ($job_file in $jobs_file_names) {
    # Remove the .yaml extension
    $job_file_name = $job_file -replace '.yaml$'

    # Parse filename to extract job-name and number
    $job_name = $job_file_name -replace '.yaml-(\d+)$'
    $threads = $job_file_name -replace '.*-(\d+)$', '$1'
    
    $logs_file = "${logs_directory}/logs_${job_name}_${threads}.txt"

    if (-not (Test-Path -Path $logs_file)) {
        $job_file_path = ($job_file -replace '-(\d+)$')
        Write-Output ./parsec-benchmarks/part2b-$threads/$job_file_path
        
        # Run kubectl create for benchmark file
        kubectl create -f ./parsec-benchmarks/part2b-$threads/$job_file_path
        
        # Wait for the job to complete
        $jobCompleted = $false
        while (-not $jobCompleted) {
            # Check if [PARSEC] Done is present in the logs
            $logsContent = kubectl logs $(kubectl get pods --selector=job-name=$job_name --output=jsonpath='{.items[*].metadata.name}')
            if ($logsContent -match "\[PARSEC\] Done") {
                $jobCompleted = $true
            } else {
                Start-Sleep -Seconds 10  # Wait for 10 seconds before checking again
                Write-Output "Not ready. Sleeping for 10 seconds"
            }
        }
        
        # Save the output of kubectl logs to a file
        $logsContent > $logs_file
        Write-Output $logs_file "done"

        # Delete all jobs and pods
        kubectl delete jobs --all
        kubectl delete pods --all
    } else {
        Write-Output "Skipping file: $job_file"
    }
}