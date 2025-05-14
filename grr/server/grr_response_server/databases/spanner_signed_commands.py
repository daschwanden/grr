#!/usr/bin/env python
"""A module with signed command methods of the Spanner database implementation."""

from typing import Sequence

from grr_response_core.lib.util import iterator
from grr_response_proto import signed_commands_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class SignedCommandsMixin:
  """A Spanner database mixin with implementation of signed command methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteSignedCommands(
      self,
      signed_commands: Sequence[signed_commands_pb2.SignedCommand],
  ) -> None:
    """Writes a signed command to the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadSignedCommand(
      self,
      id_: str,
      operating_system: signed_commands_pb2.SignedCommand.OS,
  ) -> signed_commands_pb2.SignedCommand:
    """Reads signed command from the database."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadSignedCommands(
      self,
  ) -> Sequence[signed_commands_pb2.SignedCommand]:
    """Reads signed command from the database."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteAllSignedCommands(
      self,
  ) -> None:
    """Deletes all signed command from the database."""

