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

import itertools
import time
from queue import PriorityQueue, Empty
from threading import Thread

from fyn_api_client.models.patched_job_info_runner_request import PatchedJobInfoRunnerRequest
from fyn_api_client.models.status_enum import StatusEnum

import fyn_runner.job_management.job_activity_tracking as jat
from fyn_runner.job_management.job_activity_tracking import ActiveJobTracker, ActivityState
from fyn_runner.job_management.job import Job


class JobManager:
    """Orchestrates job execution pipeline with concurrent processing and resource management.

    The JobManager handles the complete lifecycle of job processing from queue management to
    execution coordination. It maintains a priority queue for pending jobs and manages concurrent
    execution within configured resource limits. Jobs are executed in separate threads while the
    manager tracks their progress and handles thread and queue related cleanup.

    The manager implements a main processing loop that:
    1. Fetches pending jobs from the backend on startup
    2. Launches jobs when resource capacity is available
    3. Monitors running jobs and cleans up completed threads
    4. Handles errors by re-queuing failed jobs

    Note:
        The main() method runs a blocking loop that should be executed in its own thread.
        Job execution is limited by max_concurrent_jobs configuration to prevent resource
        exhaustion.

    Warning:
        Failed job launches are automatically re-queued, which could lead to infinite retry loops if
        jobs consistently fail during launch.

    Todo:
        - Implement WebSocket listeners for real-time job updates
        - Add CPU usage monitoring and throttling
        - Add comprehensive error recovery strategies
        - Properly report statuses
    """

    def __init__(self, server_proxy, file_manager, logger, configuration):
        """Initialize the job manager with required dependencies and configuration.

        Sets up job queues, activity tracking, and fetches existing jobs from the backend.
        Configuration parameters control resource limits and execution behaviour.

        Args:
            server_proxy: Proxy for backend API communication.
            file_manager: Manager for local file operations.
            logger: Logger instance for recording manager events.
            configuration: Configuration object containing max_cpu, max_concurrent_jobs,
                and max_main_loop_count settings.
        """

        # injected objects
        self.job_api = server_proxy.create_job_manager_api()
        self.server_proxy = server_proxy
        self.file_manager = file_manager
        self.logger = logger

        # Job queues
        self._counter = itertools.count()  # used to prevent job equality checking
        self._pending_queue: PriorityQueue = PriorityQueue()
        self._job_activity_tracker: ActiveJobTracker = ActiveJobTracker()
        self._observer_threads: dict[Thread] = {}

        # State data
        self._is_running = True
        self._max_cpu_usage = configuration.max_cpu
        self._max_concurrent_jobs = configuration.max_concurrent_jobs
        self._max_main_loop_count = configuration.max_main_loop_count

        # Initialse manager
        self._attached_job_listener()
        self._fetch_jobs()

    def _fetch_jobs(self):
        """Fetch existing jobs from backend and organize them by status.

        Retrieves all jobs assigned to this runner and places them in appropriate
        collections: pending jobs go to the priority queue, while active/completed
        jobs are added to the activity tracker.

        Raises:
            Exception: If the backend API call fails, logs error but continues execution.
        """
        self.logger.info("Fetching jobs")

        api_response = None
        try:
            api_response = self.job_api.job_manager_runner_list()
        except Exception as e:
            self.logger.error(f"Exception when calling JobManagerApi: {e}")

        if api_response is not None:
            for job in api_response:
                if jat.job_status_to_activity_status(job.status) == ActivityState.PENDING:
                    self._pending_queue.put((job.priority, next(self._counter), job))
                else:
                    self._job_activity_tracker.add_job(job)

            total_jobs = self._job_activity_tracker.get_job_count()
            total_jobs['queued'] = self._pending_queue.qsize()
            total_jobs['total'] = self._pending_queue.qsize(
            ) + total_jobs.pop('total')  # places at back
            self.logger.info(f"Loaded: {total_jobs}")
        else:
            self.logger.info("No jobs found")

    def _attached_job_listener(self):
        """Attach WebSocket listeners for real-time job commands.

        Added a listener for new jobs and supplies the call back fetch_and_add to the observer.
        """

        self.logger.debug("Attach job listener not implemented, wip")

        self.server_proxy.register_observer("new_job", self.fetch_and_add)

    def fetch_and_add(self, job_ws):
        """Callback function for receiving new job requests from the backend.

        Args:
            job_ws: The JSON websocket message from the backend, must contain the job_id key.
        """
        try:
            if 'job_id' not in job_ws:
                self.logger.error(f"WebSocket message missing 'job_id' key: {job_ws}")
                return
            job_id = job_ws['job_id']

            try:
                job_info = self.job_api.job_manager_users_retrieve(id=job_id)
            except Exception as e:
                self.logger.error(f"Failed to retrieve job {job_id} from API: {e}")
                return

            self._pending_queue.put((job_info.priority, next(self._counter), job_info))
            self.logger.info(f"Successfully queued new job {job_id} from WebSocket")

        except Exception as e:
            self.logger.error(f"Unexpected error in fetch_and_add callback: {e}")

    # ----------------------------------------------------------------------------------------------
    #  Job Methods
    # ----------------------------------------------------------------------------------------------

    def main(self):
        """Main processing loop that manages job execution and resource allocation.

        Continuously processes the job queue, launching new jobs when capacity allows and cleaning
        up completed executions. The loop respects concurrent job limits and handles errors
        gracefully by re-queuing failed jobs.

        The loop terminates when max_main_loop_count is reached or _is_running is set to False. Each
        iteration includes capacity checking, job launching, and thread cleanup.

        Note:
            This method blocks until the loop terminates and should be run in its own
            thread of non-blocking operation are desired.
        """
        loop_count = 0
        while self._is_running:
            self.logger.debug("New tick")
            self._cleanup_finished_threads()
            try:
                no_active_jobs = len(self._job_activity_tracker.get_active_jobs())
                if no_active_jobs < self._max_concurrent_jobs:
                    try:
                        # Get next job to launch
                        _, _, job_info = self._pending_queue.get(timeout=30)
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

    def _launch_new_job(self, job_info):
        """Launch a new job in a separate thread with error handling and recovery.

        Creates a Job instance and starts it in a dedicated thread. If launch fails, the job is
        automatically re-queued for retry and any partial state is cleaned up.

        Args:
            job_info: JobInfoRunner object containing job configuration and metadata.

        Note:
            Failed launches result in the job being reset to QUEUED status and re-added to the
            pending queue. Thread cleanup is handled automatically on failure.
        """

        self.logger.info(f"Launching new job {job_info.id}")
        thread = None
        print("HERE")
        try:
            job = Job(job_info, self.server_proxy, self.file_manager, self.logger,
                      self._job_activity_tracker)
            thread = Thread(target=job.launch)
            thread.start()
            self._observer_threads[job_info.id] = thread
            self._pending_queue.task_done()

        except Exception as e:
            print("HERE")
            self.logger.error(f"Failed to launch new job: {e}")

            self._pending_queue.task_done()  # must clear the queue (it is done) -> re-adds below.

            # Clean up thread if created but not started
            if thread and job_info.id in self._observer_threads:
                del self._observer_threads[job_info.id]

            # Ensure server re-queues
            try:
                print("HERE")
                jir = PatchedJobInfoRunnerRequest(status=StatusEnum.QD)
                job_info.status = StatusEnum.QD
                self.job_api.job_manager_runner_partial_update(job_info.id,
                                                               patched_job_info_request=jir)

                # re-add
                next(self._counter)
                print("HERE1")

                self._pending_queue.put((job_info.priority, next(self._counter), job_info))

                print("HERE12")
                # if the error occoured after its status was changed it must be removed.
                if self._job_activity_tracker.is_tracked(job_info.id):
                    self._job_activity_tracker.remove_job(job_info.id)
            except Exception:
                self.logger.error(f"Job manager failed to reset job {job_info.id} with: {e}")

    def _cleanup_finished_threads(self):
        """Clean up completed job threads to prevent resource leaks.

        Identifies threads that have finished execution and removes them from the observer thread
        collection. This prevents accumulation of dead threads and keeps the thread tracking
        accurate.

        Note:
            Only removes threads from tracking - the Job objects themselves handle their own cleanup
            through the activity tracker.
        """

        finished_job_ids = []

        for job_id, thread in self._observer_threads.items():
            if not thread.is_alive():
                finished_job_ids.append(job_id)

        for job_id in finished_job_ids:
            self.logger.debug(f"Cleaning up finished thread for job {job_id}")
            del self._observer_threads[job_id]

        if finished_job_ids:
            self.logger.info(f"Cleaned up {len(finished_job_ids)} finished threads")
