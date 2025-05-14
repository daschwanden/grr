#!/usr/bin/env python
"""A library with user methods of Spanner database implementation."""

import datetime
import logging
from typing import Optional, Sequence, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import iterator
from grr_response_core.lib.util import random
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import user_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class UsersMixin:
  """A Spanner database mixin with implementation of user methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteGRRUser(
      self,
      username: str,
      email: Optional[str] = None,
      password: Optional[jobs_pb2.Password] = None,
      user_type: Optional["objects_pb2.GRRUser.UserType"] = None,
      canary_mode: Optional[bool] = None,
      ui_mode: Optional["user_pb2.GUISettings.UIMode"] = None,
  ) -> None:
    """Writes user object for a user with a given name."""



  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteGRRUser(self, username: str) -> None:
    """Deletes the user and all related metadata with the given username."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadGRRUser(self, username: str) -> objects_pb2.GRRUser:
    """Reads a user object corresponding to a given name."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadGRRUsers(
      self,
      offset: int = 0,
      count: Optional[int] = None,
  ) -> Sequence[objects_pb2.GRRUser]:
    """Reads GRR users with optional pagination, sorted by username."""

    return []

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountGRRUsers(self) -> int:
    """Returns the total count of GRR users."""

    return 0

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteApprovalRequest(self, request: objects_pb2.ApprovalRequest) -> str:
    """Writes an approval request object."""

    return ""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadApprovalRequest(
      self,
      username: str,
      approval_id: str,
  ) -> objects_pb2.ApprovalRequest:
    """Reads an approval request object with a given id."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadApprovalRequests(
      self,
      username: str,
      typ: "objects_pb2.ApprovalRequest.ApprovalType",
      subject_id: Optional[str] = None,
      include_expired: Optional[bool] = False,
  ) -> Sequence[objects_pb2.ApprovalRequest]:
    """Reads approval requests of a given type for a given user."""
    requests = []

    return requests

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def GrantApproval(
      self,
      requestor_username: str,
      approval_id: str,
      grantor_username: str,
  ) -> None:
    """Grants approval for a given request using given username."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteUserNotification(
      self,
      notification: objects_pb2.UserNotification,
  ) -> None:
    """Writes a notification for a given user."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadUserNotifications(
      self,
      username: str,
      state: Optional["objects_pb2.UserNotification.State"] = None,
      timerange: Optional[
          Tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
  ) -> Sequence[objects_pb2.UserNotification]:
    """Reads notifications scheduled for a user within a given timerange."""

    return []

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateUserNotifications(
      self,
      username: str,
      timestamps: Sequence[rdfvalue.RDFDatetime],
      state: Optional["objects_pb2.UserNotification.State"] = None,
  ):
    """Updates existing user notification objects."""




def RDFDatetime(time: datetime.datetime) -> rdfvalue.RDFDatetime:
  return rdfvalue.RDFDatetime.FromDatetime(time)


_APPROVAL_TYPE_CLIENT = objects_pb2.ApprovalRequest.APPROVAL_TYPE_CLIENT
_APPROVAL_TYPE_HUNT = objects_pb2.ApprovalRequest.APPROVAL_TYPE_HUNT
_APPROVAL_TYPE_CRON_JOB = objects_pb2.ApprovalRequest.APPROVAL_TYPE_CRON_JOB
