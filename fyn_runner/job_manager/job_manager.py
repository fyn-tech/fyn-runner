# Copyright (C) 2025 Fyn-Runner Authors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program. If not,
#  see <https://www.gnu.org/licenses/>.

import time
from queue import PriorityQueue, Empty
from pathlib import Path
from threading import Thread

from fyn_api_client.models.patched_job_info_runner_request import PatchedJobInfoRunnerRequest
from fyn_api_client.models.status_enum import StatusEnum

import fyn_runner.job_manager.job_activity_tracking as jat
from fyn_runner.job_manager.job_activity_tracking import ActiveJobTracker, ActivityState
from fyn_runner.job_manager.job import Job


class JobManager:

    def __init__(self, server_proxy, file_manager, logger, configuration):

        # injected objects
        self.job_api = server_proxy.create_job_manager_api()
        self.server_proxy = server_proxy
        self.file_manager = file_manager
        self.logger = logger

        # Job queues
        self._pending_queue: PriorityQueue = PriorityQueue()
        self._job_activity_tracker : ActiveJobTracker = ActiveJobTracker()
        self._observer_threads : dict[Thread] = {}

        # State data
        self._is_running = True
        self._max_cpu_usage = configuration.max_cpu
        self._max_concurrent_jobs = configuration.max_concurrent_jobs
        self._max_main_loop_count = configuration.max_main_loop_count

        # Initialse manager
        self._fetch_jobs()

    # Init
    def _fetch_jobs(self):
        self.logger.info("Fetching jobs")

        api_response = None
        try:
            api_response = self.job_api.job_manager_runner_list()
        except Exception as e:
            self.logger.error("Exception when calling JobManagerApi: %s\n" % e)

        if api_response is not None:
            for job in api_response:
                if jat.job_status_to_activity_status(job.status) == ActivityState.PENDING:
                    self._pending_queue.put((job.priority, job))
                else:
                    self._job_activity_tracker.add_job(job)

            total_jobs = self._job_activity_tracker.get_job_count()
            total_jobs['queued'] = self._pending_queue.qsize()
            total_jobs['total'] = self._pending_queue.qsize() + total_jobs.pop('total') # places at back
            self.logger.info(f"Loaded: {total_jobs}")    
        else:
            self.logger.info("No jobs found")

    # attach
    def _attached_job_listener(self):
        self.logger.warning("Attach job listener not implemented, wip")
        pass

    # ----------------------------------------------------------------------------------------------
    #  Job Methods 
    # ----------------------------------------------------------------------------------------------

    def main(self):
        loop_count = 0
        while self._is_running:
            self.logger.debug("New tick")   
            self._cleanup_finished_threads()
            try:
                no_active_jobs = self._job_activity_tracker.get_job_count()['active']
                if no_active_jobs < self._max_concurrent_jobs:
                    try:
                        # Get next job to launch
                        _, job_info = self._pending_queue.get(timeout=30)
                        self._launch_new_job(job_info)
                                                
                    except Empty:
                        self.logger.debug("No pending jobs, waiting...")        
                else:
                    # At capacity - wait for jobs to complete
                    self.logger.debug(f"At capacity, number of active jobs: {no_active_jobs}")
                    time.sleep(5)

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(5)

            # check if we need to leave the main loop
            loop_count += 1
            if loop_count >= self._max_main_loop_count:
                self.logger.info(f"Reach max main loop count {loop_count}, exiting main loop.")
                self._is_running = False            
            

    # Launch Job
    def _launch_new_job(self, job_info):
        
        self.logger.info(f"Launching new job {job_info.id}")
        thread = None
        try:
            job = Job(job_info, self.server_proxy, Path(""), self.logger, 
                      self._job_activity_tracker)
            thread = Thread(target=job.launch)     
            thread.start()
            
            self._observer_threads[job_info.id] = thread
            self._pending_queue.task_done()
        # Launch new job
        except Exception as e:
            self.logger.error(f"Failed to launch new job: {e}")   

            # Clean up thread if created but not started
            if thread and job_info.id in self._observer_threads:
                del self._observer_threads[job_info.id]

            # Ensure server re-queues
            try: 
                jir = PatchedJobInfoRunnerRequest(status=StatusEnum.QD)
                job_info.status = StatusEnum.QD
                self.job_api.job_manager_runner_partial_update(job_info.id, 
                                                               patched_job_info_request=jir)
            
                # re-add
                self._pending_queue.put((job_info.priority, job_info)) 
                self._pending_queue.task_done() 

                # if the error occoured after its status was changed it must be removed.
                if self._job_activity_tracker.is_tracked(job_info.id):
                    self._job_activity_tracker.remove_job(job_info.id)
            except:
                self.logger.error(f"Job manager failed to reset job {self.job.id} with: {e}")

    def _cleanup_finished_threads(self):

        finished_job_ids = []
        
        for job_id, thread in self._observer_threads.items():
            if not thread.is_alive():
                finished_job_ids.append(job_id)
        
        for job_id in finished_job_ids:
            self.logger.debug(f"Cleaning up finished thread for job {job_id}")
            del self._observer_threads[job_id]
        
        if finished_job_ids:
            self.logger.info(f"Cleaned up {len(finished_job_ids)} finished threads")
    # Terminate Job


     


