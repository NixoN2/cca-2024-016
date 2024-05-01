$interference_directory = "./parsec-interference"
$interference_file_names = @()
$benchmark_directory = "./parsec-benchmarks/part2a"
$benchmarks_file_names = @()
$logs_directory = "./part2a-logs"

# Check if the directory exists
if (Test-Path $interference_directory -PathType Container) {
    # Get all files in the directory
    $files = Get-ChildItem $interference_directory -File

    # Loop through each file and add its name to the array
    foreach ($file in $files) {
        $interference_file_names += $file.Name
    }
} else {
    Write-Output "Directory '$interference_directory' not found."
}

# Check if the directory exists
if (Test-Path $benchmark_directory -PathType Container) {
    # Get all files in the directory
    $files = Get-ChildItem $benchmark_directory -File

    # Loop through each file and add its name to the array
    foreach ($file in $files) {
        $benchmarks_file_names += $file.Name
    }
} else {
    Write-Output "Directory '$benchmark_directory' not found."
}

if (!(Test-Path $logs_directory -PathType Container)) {
    New-Item -ItemType Directory -Path $logs_directory | Out-Null
}

# Iterate through interference files
foreach ($interference_file in $interference_file_names) {
    Write-Output "Processing file: $interference_file"
    
    # Iterate through benchmark files
    foreach ($benchmark_file in $benchmarks_file_names) {
        $interference_name = $interference_file -replace '\.yaml$'
        $job_name = $benchmark_file -replace '\.yaml$'
        $logs_file = "${logs_directory}/logs_${interference_name}_${job_name}.txt"
        
        if (-not (Test-Path -Path $logs_file)) {
            Write-Output "Processing file: $benchmark_file"
            
            # Run kubectl create for parsec_interference file
            kubectl create -f ./parsec-interference/$interference_file
            
            # Wait for 30 seconds
            Start-Sleep -Seconds 30
            
            # Run kubectl create for benchmark file
            kubectl create -f ./parsec-benchmarks/part2a/$benchmark_file
            
            # Wait for 90 seconds
            Start-Sleep -Seconds 300
            
            # Save the output of kubectl logs to a file
            kubectl logs $(kubectl get pods --selector=job-name=$job_name --output=jsonpath='{.items[*].metadata.name}') > $logs_file
            
            # Delete all jobs and pods
            kubectl delete jobs --all
            kubectl delete pods --all
        } else {
            Write-Output "Skipping file: $benchmark_file"
        }
    }
}

foreach ($benchmark_file in $benchmarks_file_names) {
    $job_name = $benchmark_file -replace '\.yaml$'
    $logs_file = "${logs_directory}/logs_${job_name}_no_interference.txt"
    if (-not (Test-Path -Path $logs_file)) {
        Write-Output "Processing file: $benchmark_file"
        
        # Run kubectl create for benchmark file
        kubectl create -f ./parsec-benchmarks/part2a/$benchmark_file
        
        # Wait for 90 seconds
        Start-Sleep -Seconds 300
        
        # Save the output of kubectl logs to a file
        kubectl logs $(kubectl get pods --selector=job-name=$job_name --output=jsonpath='{.items[*].metadata.name}') > $logs_file
        
        # Delete all jobs and pods
        kubectl delete jobs --all
        kubectl delete pods --all
    } else {
        Write-Output "Skipping file: $benchmark_file"
    }
}