import psutil
import docker

# Get CPU times
cpu_times = psutil.cpu_times()

# Print CPU times
print("CPU Times:")
print("User:", cpu_times.user)
print("System:", cpu_times.system)
print("Idle:", cpu_times.idle)

client = docker.from_env()
