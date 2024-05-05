import psutil
import docker
from typing import TypedDict, List, Dict
from datetime import datetime
from enum import Enum
import urllib.parse


LOG_STRING = "{timestamp} {event} {job_name} {args}"

class LogJob(Enum):
    SCHEDULER = "scheduler"
    MEMCACHED = "memcached"
    BLACKSCHOLES = "blackscholes"
    CANNEAL = "canneal"
    DEDUP = "dedup"
    FERRET = "ferret"
    FREQMINE = "freqmine"
    RADIX = "radix"
    VIPS = "vips"


class SchedulerLogger:
    def __init__(self):
        start_date = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.file = open(f"log{start_date}.txt", "w")
        self._log("start", LogJob.SCHEDULER)

    def _log(self, event: str, job_name: LogJob, args: str = "") -> None:
        self.file.write(
            LOG_STRING.format(timestamp=datetime.now().isoformat(), event=event, job_name=job_name.value,
                              args=args).strip() + "\n")

    def job_start(self, job: LogJob, initial_cores: list[str], initial_threads: int) -> None:
        assert job != LogJob.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("start", job, "["+(",".join(str(i) for i in initial_cores))+"] "+str(initial_threads))

    def job_end(self, job: LogJob) -> None:
        assert job != LogJob.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("end", job)

    def update_cores(self, job: LogJob, cores: list[str]) -> None:
        assert job != LogJob.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("update_cores", job, "["+(",".join(str(i) for i in cores))+"]")

    def job_pause(self, job: LogJob) -> None:
        assert job != LogJob.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("pause", job)

    def job_unpause(self, job: LogJob) -> None:
        assert job != LogJob.SCHEDULER, "You don't have to log SCHEDULER here"

        self._log("unpause", job)

    def custom_event(self, job:LogJob, comment: str):
        self._log("custom", job, urllib.parse.quote_plus(comment))

    def end(self) -> None:
        self._log("end", LogJob.SCHEDULER)
        self.file.flush()
        self.file.close()


class JobParams(TypedDict):
    image: str
    command: List[str]
    detach: bool
    remove: bool
    name: str
    cpuset_cpus: str

jobs: Dict[str, JobParams] = {
    'blacksholes': {
        'image': 'anakli/cca:parsec_blackscholes',
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'blackscholes', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'blacksholes',
        'cpuset_cpus': '0'
    },
    'radix': {
        'image': "anakli/cca:splash2x_radix",
        'command': ['./run', '-a', 'run', '-S', 'splash2x', '-p', 'radix', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'radix',
        'cpuset_cpus': '0'
    },
    'canneal': {
        'image': "anakli/cca:parsec_canneal",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'canneal', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'canneal',
        'cpuset_cpus': '0'
    },
    'vips': {
        'image': "anakli/cca:parsec_vips",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'vips', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'vips',
        'cpuset_cpus': '0'
    },
    'freqmine': {
        'image': "anakli/cca:parsec_freqmine",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'freqmine', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'freqmine',
        'cpuset_cpus': '0'
    },
    'dedup': {
        'image': "anakli/cca:parsec_dedup",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'dedup', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'dedup',
        'cpuset_cpus': '0'
    },
    'ferret': {
        'image': "anakli/cca:parsec_ferret",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'ferret', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'ferret',
        'cpuset_cpus': '0'
    }
}

class Job:
    def __init__(self, job: JobParams):
        self.job = job

    def get_job(self) -> JobParams:
        return self.job
    
    def set_threads(self, num_threads: int):
        self.job['command'].insert(1, '-t')
        self.job['command'].insert(2, str(num_threads))
        self.job['command'][-1] = str(2 * num_threads)

    def set_cpus(self, cpus: List[int]):
        self.job['cpuset_cpus'] = ','.join(map(str, cpus))

    def set_completed(self):
        self.job['completed'] = True

class Controller:
    def __init__(self, jobs: Dict[str, JobParams], logger: SchedulerLogger):
        self.logger = logger
        self.completed_jobs = 0
        self.running_jobs: List[JobParams] = []
        self.jobs = jobs
        self.client = docker.from_env()

    def get_cpu_load(self):
        return psutil.cpu_percent()
    
    def run_job(self, job_name: str):
        job = self.jobs[job_name]
        self.client.containers.run(**job)
        self.running_jobs.append(job)
        # TODO job logging
        self.logger.job_start(LogJob[job_name], job['cpuset_cpus'], job['command'])

    def update_job_cpus(self, container_name: str, cpus: List[int]):
        container = self.client.containers.get(container_name)
        container.update(cpuset_cpus=','.join(map(str, cpus)))
        self.logger.update_cores(LogJob[container_name], list(map(str, cpus)))

    def set_job_completed(self, job_name: str):
        self.completed_jobs += 1
        self.running_jobs = [job for job in self.running_jobs if job['name'] != job_name]  
        self.jobs.pop(job_name)
        self.logger.job_end(LogJob[job_name])

    def pause_container(self, container_name: str):
        container = self.client.containers.get(container_name)
        container.pause()
        self.logger.job_pause(LogJob[container_name])

    def unpause_container(self, container_name: str):
        container = self.client.containers.get(container_name)
        container.unpause()
        self.logger.job_unpause(LogJob[container_name])

    def get_all_container_cpu_utilization(self) -> Dict[str, float]:
        container_cpu_utilization = {}
        try:
            for container in self.client.containers.list():
                container_name = container.name
                cpu_utilization = self.get_container_cpu_utilization(container_name)
                container_cpu_utilization[container_name] = cpu_utilization
        except Exception as e:
            print(f"Error retrieving CPU utilization for containers: {e}")
        return container_cpu_utilization

    def get_container_cpu_utilization(self, container_name: str) -> float:
        try:
            container_stats = self.client.containers.get(container_name).stats(stream=False)
            cpu_stats = container_stats['cpu_stats']
            precpu_stats = container_stats['precpu_stats']

            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']

            if system_delta > 0 and cpu_delta > 0:
                cpu_utilization_percentage = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100.0
                return round(cpu_utilization_percentage, 2)
            else:
                return 0.0
        except docker.errors.NotFound:
            return 0.0
        except Exception as e:
            print(f"Error retrieving CPU utilization for container {container_name}: {e}")
            return 0.0
        
logger = SchedulerLogger()
controller = Controller(jobs, logger)

logger.custom_event(LogJob.SCHEDULER, "Controller started")

while controller.completed_jobs != 7:
    for job_name in jobs.keys():
        controller.run_job(job_name)

logger.end()