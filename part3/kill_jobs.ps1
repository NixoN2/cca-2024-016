$jobNames = kubectl get jobs -o=jsonpath='{.items[*].metadata.name}'

# Split the job names into an array
$jobNamesArray = $jobNames -split '\s+'

# Iterate over each job name
foreach ($jobName in $jobNamesArray) {
    # Delete pods associated with the current job
    kubectl delete pods -l job-name=$jobName

    # Delete the job itself
    kubectl delete job $jobName
}