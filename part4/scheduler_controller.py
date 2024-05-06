import psutil
import docker
from typing import TypedDict, List, Dict, Optional
from datetime import datetime
import time
import urllib.parse


LOG_STRING = "{timestamp} {event} {job_name} {args}"

class SchedulerLogger:
    def __init__(self):
        start_date = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.file = open(f"log{start_date}.txt", "w")
        self._log("start", "scheduler")

    def _log(self, event: str, job_name: str, args: str = "") -> None:
        self.file.write(
            LOG_STRING.format(timestamp=datetime.now().isoformat(), event=event, job_name=job_name,
                              args=args).strip() + "\n")

    def job_start(self, job: str, initial_cores: list[str], initial_threads: int) -> None:
        assert job != "scheduler", "You don't have to log SCHEDULER here"

        self._log("start", job, "["+(",".join(str(i) for i in initial_cores))+"] "+str(initial_threads))

    def job_end(self, job: str) -> None:
        assert job != "scheduler", "You don't have to log SCHEDULER here"

        self._log("end", job)

    def update_cores(self, job: str, cores: list[str]) -> None:
        assert job != "scheduler", "You don't have to log SCHEDULER here"

        self._log("update_cores", job, "["+(",".join(str(i) for i in cores))+"]")

    def job_pause(self, job: str) -> None:
        assert job != "scheduler", "You don't have to log SCHEDULER here"

        self._log("pause", job)

    def job_unpause(self, job: str) -> None:
        assert job != "scheduler", "You don't have to log SCHEDULER here"

        self._log("unpause", job)

    def custom_event(self, job: str, comment: str):
        self._log("custom", job, urllib.parse.quote_plus(comment))

    def end(self) -> None:
        self._log("end", "scheduler")
        self.file.flush()
        self.file.close()


class JobParams(TypedDict):
    image: str
    command: List[str]
    detach: bool
    remove: bool
    name: str
    cpuset_cpus: str
    weight: int

jobs: Dict[str, JobParams] = {
    'blacksholes': {
        'image': 'anakli/cca:parsec_blackscholes',
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'blackscholes', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'blacksholes',
        'cpuset_cpus': '0',
        'weight': 2
    },
    'radix': {
        'image': "anakli/cca:splash2x_radix",
        'command': ['./run', '-a', 'run', '-S', 'splash2x', '-p', 'radix', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'radix',
        'cpuset_cpus': '0',
        'weight': 1
    },
    'canneal': {
        'image': "anakli/cca:parsec_canneal",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'canneal', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'canneal',
        'cpuset_cpus': '0',
        'weight': 1
    },
    'vips': {
        'image': "anakli/cca:parsec_vips",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'vips', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'vips',
        'cpuset_cpus': '0',
        'weight': 2
    },
    'freqmine': {
        'image': "anakli/cca:parsec_freqmine",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'freqmine', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'freqmine',
        'cpuset_cpus': '0',
        'weight': 3
    },
    'dedup': {
        'image': "anakli/cca:parsec_dedup",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'dedup', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'dedup',
        'cpuset_cpus': '0',
        'weight': 2
    },
    'ferret': {
        'image': "anakli/cca:parsec_ferret",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'ferret', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'ferret',
        'cpuset_cpus': '0',
        'weight': 3
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

    def build_docker_job(self):
        return {
            'image': self.job['image'],
            'command': self.job['command'],
            'detach': self.job['detach'],
            'remove': self.job['remove'],
            'name': self.job['name'],
            'cpuset_cpus': self.job['cpuset_cpus'],
        }

    def set_completed(self):
        self.job['completed'] = True

class Controller:
    def __init__(self, jobs: Dict[str, JobParams], logger: SchedulerLogger):
        self.logger = logger
        self.completed_jobs = 0
        self.running_jobs: List[JobParams] = []
        self.jobs = jobs
        self.client = docker.from_env()
        self.jobs_to_run = []

    def set_jobs_to_run(self, job_names: List[str]):
        self.jobs_to_run = job_names

    def check_jobs(self):
        containers = self.client.containers.list()

        for job in self.running_jobs:
            job_name = job['name']
            job_found = False
            for container in containers:
                if container.name == job_name:
                    job_found = True
                    break
            if not job_found:
                self.set_job_completed(job_name)

        for container in containers:
            print(f"Name: {container.name}")
            print(f"Status: {container.status}")
            print("--------------")

    def get_cpu_load(self):
        return psutil.cpu_percent()
    
    def run_job(self, job_name: str, cpuset_cpus: List[int] | None = None, threads: int = 1):
        job = self.jobs[job_name]
        parsed_job = Job(job)
        if cpuset_cpus:
            parsed_job.set_cpus(cpuset_cpus)
        if threads != 1:
            parsed_job.set_threads(threads)
        self.client.containers.run(**parsed_job.build_docker_job())
        self.running_jobs.append(job)
        self.jobs_to_run = [job_to_run for job_to_run in self.jobs_to_run if job_to_run != job_name]
        self.logger.job_start(job_name, job['cpuset_cpus'], job['command'])
        print("Job " + job_name + " is running")

    def update_job_cpus(self, container_name: str, cpus: List[int]):
        container = self.client.containers.get(container_name)
        container.update(cpuset_cpus=','.join(map(str, cpus)))
        self.logger.update_cores(container_name, list(map(str, cpus)))

    def set_job_completed(self, job_name: str):
        self.completed_jobs += 1
        self.running_jobs = [job for job in self.running_jobs if job['name'] != job_name]  
        self.jobs.pop(job_name)
        self.logger.job_end(job_name)
        print(job_name + " finished")

    def pause_container(self, container_name: str):
        container = self.client.containers.get(container_name)
        container.pause()
        self.logger.job_pause(container_name)

    def unpause_container(self, container_name: str):
        container = self.client.containers.get(container_name)
        container.unpause()
        self.logger.job_unpause(container_name)

    def get_job_with_lowest_weight(self) -> Optional[JobParams]:
        filtered_jobs = [job for job_name, job in self.jobs.items() if job_name in self.jobs_to_run]
        if not filtered_jobs:
            return None

        return min(filtered_jobs, key=lambda job: job['weight'])
    
    def get_job_with_highest_weight(self) -> Optional[JobParams]:
        filtered_jobs = [job for job_name, job in self.jobs.items() if job_name in self.jobs_to_run]
        if not filtered_jobs:
            return None

        return max(filtered_jobs, key=lambda job: job['weight'])
    
    def evaluate_scheduling_policy(self):
        if len(self.jobs_to_run) == 0 or not self.jobs_to_run:
            raise RuntimeError("You need to set job names to run using set_jobs_to_run")
        
        jobs_to_complete = len(self.jobs_to_run)
        while self.completed_jobs != jobs_to_complete:
            if len(self.running_jobs) < 2:
                easy_job = self.get_job_with_lowest_weight()
                if easy_job:
                    self.run_job(easy_job.get('name'), [1], 2)
                hard_job = self.get_job_with_highest_weight()
                if hard_job:
                    self.run_job(hard_job.get('name'), [2,3], 4)

            self.check_jobs()
            print(controller.get_cpu_load())
            time.sleep(5)
        
logger = SchedulerLogger()
controller = Controller(jobs, logger)

controller.set_jobs_to_run(["canneal", "radix", "blacksholes", "ferret", "dedup", "vips", "freqmine"])

controller.evaluate_scheduling_policy()

logger.end()