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

import threading
from fyn_api_client.models.status_enum import StatusEnum
from enum import Enum

class ActivityState(Enum):
    PENDING = 'pending'
    ACTIVE = 'active'
    COMPLETE = 'complete'

def job_status_to_activity_status(status):
    match (status):
        case StatusEnum.QD:
            return ActivityState.PENDING
        
        case StatusEnum.PR:
            return ActivityState.ACTIVE
        case StatusEnum.FR:
            return ActivityState.ACTIVE
        case StatusEnum.RN:
            return ActivityState.ACTIVE
        case StatusEnum.PD:
            return ActivityState.ACTIVE
        case StatusEnum.CU:
            return ActivityState.ACTIVE
        case StatusEnum.UR:
            return ActivityState.ACTIVE
        
        case StatusEnum.SD:
            return ActivityState.COMPLETE
        case StatusEnum.FD:
            return ActivityState.COMPLETE
        case StatusEnum.FS:
            return ActivityState.COMPLETE
        case StatusEnum.FM:
            return ActivityState.COMPLETE
        case StatusEnum.FO:
            return ActivityState.COMPLETE
        case StatusEnum.FE:
            return ActivityState.COMPLETE
        case _:
            raise ValueError(f"Unknown Status: {status}")

class ActiveJobTracker:
    def __init__(self):
        self._lock = threading.RLock()  
        self._active_jobs = {}    # job_id -> job
        self._completed_jobs = {} # job_id -> job
        
    def add_job(self, job):
        """Add a job to tracking based on its current status"""
        with self._lock:
            status = job_status_to_activity_status(job.status)
            match (status):
                case ActivityState.PENDING:
                    raise RuntimeError(f"Cannot add pending job {job.id} - use queue instead") 
                case ActivityState.ACTIVE:
                    self._active_jobs[job.id] = job
                case ActivityState.COMPLETE:
                    self._completed_jobs[job.id] = job
            
    def update_job_status(self, job_id, new_status):
        """Update a job's status and move between collections if needed"""
        with self._lock:
            is_active = self.is_active(job_id)
            is_complete = self.is_completed(job_id)

            if is_active and is_complete:
                raise RuntimeError(f"Job {job_id} is both active and complete - data corruption!")
                
            if not is_active and not is_complete:
                raise RuntimeError(f"Unknown job {job_id} - cannot update status") 

            new_activity_state = job_status_to_activity_status(new_status)

            if new_activity_state == ActivityState.ACTIVE and is_complete:
                job = self._completed_jobs.pop(job_id)
                job.status = new_status  # Update the job object's status
                self._active_jobs[job_id] = job

            elif new_activity_state == ActivityState.COMPLETE and is_active:
                job = self._active_jobs.pop(job_id)
                job.status = new_status  # Update the job object's status
                self._completed_jobs[job_id] = job
                
            elif is_active and new_activity_state == ActivityState.ACTIVE:
                self._active_jobs[job_id].status = new_status
            elif is_complete and new_activity_state == ActivityState.COMPLETE:
                self._completed_jobs[job_id].status = new_status
                
    def remove_job(self, job_id):
        """Remove job from tracking entirely (for cleanup)"""
        with self._lock:
            removed = False
            if job_id in self._active_jobs:
                del self._active_jobs[job_id]
                removed = True
            if job_id in self._completed_jobs:
                del self._completed_jobs[job_id]
                removed = True
            return removed
        
    def get_active_job_ids(self):
        """Get list of active job IDs"""
        with self._lock:
            return list(self._active_jobs.keys())
                       
    def get_active_jobs(self):
        """Get all currently active jobs"""
        with self._lock:
            return list(self._active_jobs.values())
            
    def is_active(self, job_id):
        """Check if job is currently active"""
        with self._lock:
            return job_id in self._active_jobs
    
    def get_completed_job_ids(self):
        """Get list of completed job IDs"""
        with self._lock:
            return list(self._completed_jobs.keys())
        
    def get_completed_jobs(self):
        """Get all completed jobs"""
        with self._lock:
            return list(self._completed_jobs.values())
        
    def is_completed(self, job_id):
        """Check if job is completed"""
        with self._lock:
            return job_id in self._completed_jobs
            
    def get_job_count(self):
        """Get counts for monitoring"""
        with self._lock:
            return {
                'active': len(self._active_jobs),
                'completed': len(self._completed_jobs),
                'total': len(self._active_jobs) + len(self._completed_jobs)
            }
            
    def is_tracked(self, job_id):
        """Checks if the job is in the data structure."""
        return self.is_active(job_id) or self.is_completed(job_id)