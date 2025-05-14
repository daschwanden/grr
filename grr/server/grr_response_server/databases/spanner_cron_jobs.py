#!/usr/bin/env python
"""A module with cronjobs methods of the Spanner backend."""

import datetime
from typing import Any, Mapping, Optional, Sequence

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils

_UNCHANGED = db.Database.UNCHANGED


class CronJobsMixin:
  """A Spanner database mixin with implementation of cronjobs."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteCronJob(self, cronjob: flows_pb2.CronJob) -> None:
    """Writes a cronjob to the database.

    Args:
      cronjob: A flows_pb2.CronJob object.
    """
    # We currently expect to reuse `created_at` if set.


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadCronJobs(
      self, cronjob_ids: Optional[Sequence[str]] = None
  ) -> Sequence[flows_pb2.CronJob]:
    """Reads all cronjobs from the database.

    Args:
      cronjob_ids: A list of cronjob ids to read. If not set, returns all cron
        jobs in the database.

    Returns:
      A list of flows_pb2.CronJob objects.

    Raises:
      UnknownCronJobError: A cron job for at least one of the given ids
                           does not exist.
    """

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateCronJob(  # pytype: disable=annotation-type-mismatch
      self,
      cronjob_id: str,
      last_run_status: Optional[
          "flows_pb2.CronJobRun.CronJobRunStatus"
      ] = _UNCHANGED,
      last_run_time: Optional[rdfvalue.RDFDatetime] = _UNCHANGED,
      current_run_id: Optional[str] = _UNCHANGED,
      state: Optional[jobs_pb2.AttributedDict] = _UNCHANGED,
      forced_run_requested: Optional[bool] = _UNCHANGED,
  ):
    """Updates run information for an existing cron job.

    Args:
      cronjob_id: The id of the cron job to update.
      last_run_status: A CronJobRunStatus object.
      last_run_time: The last time a run was started for this cron job.
      current_run_id: The id of the currently active run.
      state: The state dict for stateful cron jobs.
      forced_run_requested: A boolean indicating if a forced run is pending for
        this job.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def EnableCronJob(self, cronjob_id: str) -> None:
    """Enables a cronjob.

    Args:
      cronjob_id: The id of the cron job to enable.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DisableCronJob(self, cronjob_id: str) -> None:
    """Deletes a cronjob along with all its runs.

    Args:
      cronjob_id: The id of the cron job to delete.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteCronJob(self, cronjob_id: str) -> None:
    """Deletes a cronjob along with all its runs.

    Args:
      cronjob_id: The id of the cron job to delete.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def LeaseCronJobs(
      self,
      cronjob_ids: Optional[Sequence[str]] = None,
      lease_time: Optional[rdfvalue.Duration] = None,
  ) -> Sequence[flows_pb2.CronJob]:
    """Leases all available cron jobs.

    Args:
      cronjob_ids: A list of cronjob ids that should be leased. If None, all
        available cronjobs will be leased.
      lease_time: rdfvalue.Duration indicating how long the lease should be
        valid.

    Returns:
      A list of cronjobs.CronJob objects that were leased.
    """

    return []

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReturnLeasedCronJobs(self, jobs: Sequence[flows_pb2.CronJob]) -> None:
    """Makes leased cron jobs available for leasing again.

    Args:
      jobs: A list of leased cronjobs.

    Raises:
      ValueError: If not all of the cronjobs are leased.
    """


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteCronJobRun(self, run_object: flows_pb2.CronJobRun) -> None:
    """Stores a cron job run object in the database.

    Args:
      run_object: A flows_pb2.CronJobRun object to store.
    """


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadCronJobRuns(self, job_id: str) -> Sequence[flows_pb2.CronJobRun]:
    """Reads all cron job runs for a given job id.

    Args:
      job_id: Runs will be returned for the job with the given id.

    Returns:
      A list of flows_pb2.CronJobRun objects.
    """

    return []

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadCronJobRun(self, job_id: str, run_id: str) -> flows_pb2.CronJobRun:
    """Reads a single cron job run from the db.

    Args:
      job_id: The job_id of the run to be read.
      run_id: The run_id of the run to be read.

    Returns:
      An flows_pb2.CronJobRun object.
    """

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteOldCronJobRuns(self, cutoff_timestamp: rdfvalue.RDFDatetime) -> int:
    """Deletes cron job runs that are older than cutoff_timestamp.

    Args:
      cutoff_timestamp: This method deletes all runs that were started before
        cutoff_timestamp.

    Returns:
      The number of deleted runs.
    """

    return 0

