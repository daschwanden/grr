#!/usr/bin/env python
"""A module with foreman rules methods of the Spanner backend."""

from typing import Sequence

from grr_response_core.lib import rdfvalue
from grr_response_proto import jobs_pb2
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class ForemanRulesMixin:
  """A Spanner database mixin with implementation of foreman rules."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteForemanRule(self, rule: jobs_pb2.ForemanCondition) -> None:
    """Writes a foreman rule to the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def RemoveForemanRule(self, hunt_id: str) -> None:
    """Removes a foreman rule from the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAllForemanRules(self) -> Sequence[jobs_pb2.ForemanCondition]:
    """Reads all foreman rules from the database."""
    result = []

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def RemoveExpiredForemanRules(self) -> None:
    """Removes all expired foreman rules from the database."""

