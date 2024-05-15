import psutil
import docker
from typing import TypedDict, List, Dict, Optional
from datetime import datetime
import time
import urllib.parse
import subprocess
from enum import Enum
import time

LOG_STRING = "{timestamp} {event} {job_name} {args}"

class SchedulerLogger:
    def __init__(self):
        start_date = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.file = open(f"log{start_date}.txt", "w")
        self._log("start", "scheduler")
        self.job_start("memcached", [0], 2)

    def _log(self, event: str, job_name: str, args: str = "") -> None:
        if job_name == "vips-job":
            job_name = "vips"
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
        'cpuset_cpus': '2,3',
        'weight': 2
    },
    'radix': {
        'image': "anakli/cca:splash2x_radix",
        'command': ['./run', '-a', 'run', '-S', 'splash2x', '-p', 'radix', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'radix',
        'cpuset_cpus': '2,3',
        'weight': 1
    },
    'canneal': {
        'image': "anakli/cca:parsec_canneal",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'canneal', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'canneal',
        'cpuset_cpus': '2,3',
        'weight': 1
    },
    'vips-job': {
        'image': "anakli/cca:parsec_vips",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'vips', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'vips-job',
        'cpuset_cpus': '2,3',
        'weight': 2
    },
    'freqmine': {
        'image': "anakli/cca:parsec_freqmine",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'freqmine', '-i', 'native', '-n', '4'],
        'detach': True,
        'remove': True,
        'name': 'freqmine',
        'cpuset_cpus': '2,3',
        'weight': 3
    },
    'dedup': {
        'image': "anakli/cca:parsec_dedup",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'dedup', '-i', 'native', '-n', '1'],
        'detach': True,
        'remove': True,
        'name': 'dedup',
        'cpuset_cpus': '2,3',
        'weight': 2
    },
    'ferret': {
        'image': "anakli/cca:parsec_ferret",
        'command': ['./run', '-a', 'run', '-S', 'parsec', '-p', 'ferret', '-i', 'native', '-n', '4'],
        'detach': True,
        'remove': True,
        'name': 'ferret',
        'cpuset_cpus': '2,3',
        'weight': 3
    }
}

class Job:
    def __init__(self, job: JobParams):
        self.job = job

    def get_job(self) -> JobParams:
        return self.job
    
    def get_name(self) -> str:
        return self.job['name']
    
    def equals_cpuset_cpus(self, cpuset_cpus: List[int]):
        cpuset_cpus = ','.join(map(str, cpuset_cpus))
        return self.job['cpuset_cpus'] == cpuset_cpus
    
    def set_threads(self, num_threads: int):
        self.job['command'].insert(1, '-t')
        self.job['command'].insert(2, str(num_threads))
        self.job['command'][-1] = str(num_threads)

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

class Load(Enum):
    HIGH = 1,
    LOW = 2

class Controller:
    def __init__(self, jobs: Dict[str, JobParams], logger: SchedulerLogger):
        self.logger = logger
        self.completed_jobs = 0
        self.job = None
        self.jobs = jobs
        self.client = docker.from_env()
        self.jobs_to_run = []
        self.load = Load.LOW
        self.cores = [0]
        self.memcached_pid = self.get_memcached_pid()
        self.set_memcached_cpus(self.cores)
        self.low_load_job_cpus = [1,2,3]
        self.high_load_job_cpus = [2,3]
        self.low_load_memcached_cpus = [0]
        self.high_load_memcached_cpus = [0,1]
        self.threshold = 40
        self.start_time = time.time()
        self.fails = 0
        self.fails_time = time.time()

    def get_memcached_pid(self):
        try:
            output = subprocess.check_output(["pidof", "memcached"])
            pids = output.decode("utf-8").strip().split()
            return int(pids[0])
        except subprocess.CalledProcessError:
            return None
        
    def set_memcached_cpus(self, cpus: List[int]):
        if not self.memcached_pid:
            raise ValueError("Memcached pid is not found")
        process = psutil.Process(self.memcached_pid)
        process.cpu_affinity(cpus)

    def set_load(self, load: Load):
        self.load = load

    def set_cores(self, cores: List[int]):
        self.cores = cores

    def set_jobs_to_run(self, job_names: List[str]):
        self.jobs_to_run = job_names

    def check_jobs(self):
        containers = self.client.containers.list()
        if self.job:
            job_name = self.job.get_name()
            job_found = False
            for container in containers:
                if container.name == job_name:
                    job_found = True
                    break
            if not job_found:
                self.set_job_completed(job_name)
        # try:
        #     for container in containers:
        #         print(f"Name: {container.name}")
        #         print(f"Status: {container.status}")
        #         print(f"Cores: {self.cores}")
        #         print("--------------")
        # except:
        #     return

    def get_cpu_load(self):
        cpu_usage = psutil.cpu_percent(0.5, True)
        # print("cpu usage per core", cpu_usage)
        usage = 0
        for core in self.cores:
            usage += cpu_usage[core]
        # print("total cpu usage on used cores", usage)
        self.logger.custom_event("logger", "memcached cores " + self.get_cores(self.cores))
        return usage
    
    def is_two_cpus_busy(self):
        return len(self.cores) == 2
    
    def is_high_load(self, cpu_usage: float):
        if self.is_two_cpus_busy() and cpu_usage >= self.threshold * 2:
            return True

        if not self.is_two_cpus_busy() and cpu_usage >= self.threshold:
            return True

        return False
    
    def get_free_cpus(self):
        if self.load == Load.HIGH:
            return self.high_load_job_cpus
        return self.low_load_job_cpus
    
    def run_job(self, job_name: str):
        job = self.jobs[job_name]
        parsed_job = Job(job)
        free_cpus = self.get_free_cpus()
        is_heavy_job = job_name == "freqmine" or job_name == "ferret"
        if is_heavy_job:
            parsed_job.set_cpus(self.low_load_job_cpus)
        else:
            parsed_job.set_cpus(free_cpus)
            parsed_job.set_threads(len(free_cpus))
        # parsed_job.set_cpus(free_cpus)
        # parsed_job.set_threads(len(free_cpus))
        self.client.containers.run(**parsed_job.build_docker_job())
        self.job = parsed_job
        self.jobs_to_run = [job_to_run for job_to_run in self.jobs_to_run if job_to_run != job_name]
        if is_heavy_job:
            self.logger.job_start(job_name, [str(cpu) for cpu in free_cpus], 1)
        else:
            self.logger.job_start(job_name, [str(cpu) for cpu in free_cpus], len(free_cpus))
        self.logger.custom_event(job_name, "memcached cores " + self.get_cores(self.cores))
        print("time:", time.time() - self.start_time)
        print("Job " + job_name + " is running with cpus ", free_cpus, " and threads ", len(free_cpus), "freqmine special case (1 thread -n 8)")

    def get_cores(self, cpus: List[int]):
        result = ""
        for i, cpu in enumerate(cpus):
            result += str(cpu)
            if i != len(cpus) - 1:
                result += ", "
        return result
    
    def update_job_cpus(self, container_name: str, cpus: List[int]):
        # if container_name == "ferret" or container_name == "freqmine":
        #     return

        t = time.time()
        if self.fails == 0 and self.load == Load.HIGH:
            self.fails_time = t 
            self.fails = 1


        if self.load == Load.HIGH and t - self.fails_time < 10:
            self.fails += 1

        if self.fails == 2 and t - self.fails_time > 15:
            self.fails = 0

        if self.fails == 2 and len(cpus) == 3:
            return

        try:
            container = self.client.containers.get(container_name)
            container.update(cpuset_cpus=','.join(map(str, cpus)))

            if self.job and (self.job.get_name() == "freqmine" or self.job.get_name() == "ferret"):
                self.job.set_cpus(cpus)
            elif self.job:
                self.job.set_cpus(cpus)
                self.job.set_threads(len(cpus))

            # self.job.set_cpus(cpus)
            # self.job.set_threads(len(cpus))
            self.logger.update_cores(container_name, [str(cpu) for cpu in cpus])
            self.logger.custom_event(container_name, "memcached cores " + self.get_cores(self.cores))
            print("time:", time.time() - self.start_time)
            print("cpu usage:", self.get_cpu_load())
            print("updating cores for", container_name, cpus)
        except:
            return

    def set_job_completed(self, job_name: str):
        self.completed_jobs += 1
        self.job = None 
        self.jobs.pop(job_name)
        self.logger.job_end(job_name)
        self.logger.custom_event(job_name, "memcached cores " + self.get_cores(self.cores))
        print("time:", time.time() - self.start_time)
        print(job_name + " finished")

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
    
    def check_cpu_usage(self):
        cpu_usage = self.get_cpu_load()

        if self.is_high_load(cpu_usage) and self.is_two_cpus_busy():
            return 
        
        if self.is_high_load(cpu_usage) and not self.is_two_cpus_busy():
            self.set_cores(self.high_load_memcached_cpus)
            self.set_memcached_cpus(self.cores)
            self.set_load(Load.HIGH)
            return

        if not self.is_high_load(cpu_usage) and self.is_two_cpus_busy():
            self.set_cores(self.low_load_memcached_cpus)
            self.set_memcached_cpus(self.cores)
            self.set_load(Load.LOW)
            return


    def evaluate_scheduling_policy(self):
        if len(self.jobs_to_run) == 0 or not self.jobs_to_run:
            raise RuntimeError("You need to set job names to run using set_jobs_to_run")
        
        jobs_to_complete = len(self.jobs_to_run)
        while self.completed_jobs != jobs_to_complete:
            self.check_cpu_usage()
            # print(self.load, "is high load", self.load == Load.HIGH)
            if self.job:
                if self.load == Load.HIGH and self.job.equals_cpuset_cpus(self.low_load_job_cpus):
                    self.update_job_cpus(self.job.get_name(), self.high_load_job_cpus)
                    self.check_jobs()
                    time.sleep(0.5)
                    continue

                if self.load == Load.LOW and self.job.equals_cpuset_cpus(self.high_load_job_cpus):
                    self.update_job_cpus(self.job.get_name(), self.low_load_job_cpus)
                    self.check_jobs()
                    time.sleep(0.5)
                    continue
                
            else:
                job_to_complete = None
                if self.load == Load.HIGH:
                    job_to_complete = self.get_job_with_lowest_weight()
                else:
                    job_to_complete = self.get_job_with_highest_weight()
                
                if job_to_complete:
                    self.run_job(job_to_complete['name'])

            self.check_jobs()
            time.sleep(0.5)
        
logger = SchedulerLogger()
controller = Controller(jobs, logger)

controller.set_jobs_to_run(["canneal", "radix", "blacksholes", "dedup", "vips-job", "ferret", "freqmine"])

controller.evaluate_scheduling_policy()

time.sleep(120)

logger.end()