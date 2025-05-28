"""Spanner-related helpers and other utilities."""

import contextlib
import datetime
import decimal
import re

from typing import Any
from typing import Callable
from typing import Generic
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import TypeVar

from concurrent import futures
from google.cloud import pubsub_v1
from google.cloud import spanner_v1 as spanner_lib
from google.cloud.spanner import KeyRange, KeySet
from google.cloud.spanner_admin_database_v1.types import spanner_database_admin
from google.cloud.spanner_v1 import Mutation, param_types

from google.rpc.code_pb2 import OK

from grr_response_core.lib.util import collection
from grr_response_core.lib.util import iterator

Row = Tuple[Any, ...]
Cursor = Iterator[Row]

_T = TypeVar("_T")

class QueueReceiver:
  """
  This stores the callback internally, and will continue to deliver messages to
  the callback as long as it is referenced in python code and Stop is not
  called.
  """

  def __init__(
      self,
      queue_type: str,
      callback,  # : Callable[[spanner.KeyBuilder, List[Any], Any, bytes,
      receiver_max_keepalive_seconds: int,
      receiver_max_active_callbacks: int,
      receiver_max_messages_per_callback: int,
  ):
    # An optional executor to use. If not specified, a default one with maximum 10
    # threads will be created.
    executor = futures.ThreadPoolExecutor(max_workers=receiver_max_messages_per_callback)
    # A thread pool-based scheduler. It must not be shared across SubscriberClients.
    scheduler = pubsub_v1.subscriber.scheduler.ThreadScheduler(executor)

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    def subcallback(message: pubsub_v1.subscriber.message.Message) -> None:
      callback()
      message.ack()

    flow_control = pubsub_v1.types.FlowControl(max_messages=receiver_max_messages_per_callback)

    streaming_pull_future = subscriber.subscribe(
      subscription_path, callback=subcallback, scheduler=scheduler, flow_control=flow_control
    )

  # Wrap subscriber in a 'with' block to automatically call close() when done.
  with subscriber:
    try:
        # When `timeout` is not set, result() will block indefinitely,
        # unless an exception is encountered first.
        streaming_pull_future.result(timeout=receiver_max_keepalive_seconds)
    except TimeoutError:
        streaming_pull_future.cancel()  # Trigger the shutdown.
        streaming_pull_future.result()  # Block until the shutdown is complete.

  def Stop(self):
    streaming_pull_future.cancel()


class Database:
  """A wrapper around the PySpanner class.

  The wrapper is supposed to streamline the usage of Spanner database through
  an abstraction that is much harder to misuse. The wrapper will run retryable
  queries through a transaction runner handling all brittle logic for the user.
  """

  _PYSPANNER_PARAM_REGEX = re.compile(r"@p\d+") 

  def __init__(self, pyspanner: spanner_lib.database) -> None:
    super().__init__()
    self._pyspanner = pyspanner

  def _parametrize(self, query: str, names: Iterable[str]) -> str:
    match = self._PYSPANNER_PARAM_REGEX.search(query)
    if match is not None:
      raise ValueError(f"Query contains illegal sequence: {match.group(0)}")

    kwargs = {}
    for name in names:
      kwargs[name] = f"@{name}"

    return query.format(**kwargs)

  def _get_param_type(self, value):
    """
    Infers the Google Cloud Spanner type from a Python value.

    Args:
        value: The Python value whose Spanner type is to be inferred.

    Returns:
        A google.cloud.spanner_v1.types.Type object, or None if the type
        cannot be reliably inferred (e.g., for a standalone None value or
        an empty list).
    """
    if value is None:
        # Cannot determine a specific Spanner type from a None value alone.
        # This indicates that the type is ambiguous without further schema context.
        return None

    py_type = type(value)

    if py_type is int:
        return param_types.INT64
    elif py_type is float:
        return param_types.FLOAT64
    elif py_type is str:
        return param_types.STRING
    elif py_type is bool:
        return param_types.BOOL
    elif py_type is bytes:
        return param_types.BYTES
    elif py_type is datetime.date:
        return param_types.DATE
    elif py_type is datetime.datetime:
        # Note: Spanner TIMESTAMPs are stored in UTC. Ensure datetime objects
        # are timezone-aware (UTC) when writing data. This function only maps the type.
        return param_types.TIMESTAMP
    elif py_type is decimal.Decimal:
        return param_types.NUMERIC
    else:
        # Potentially raise an error for unsupported types or return None
        # For a generic solution, raising an error for unknown types is often safer.
        raise TypeError(f"Unsupported Python type: {py_type.__name__} for Spanner type conversion.")

  def Transact(
      self,
      func: Callable[["Transaction"], _T],
      txn_tag: Optional[str] = None,
  ) -> List[Any]:

    """Execute the given callback function in a Spanner transaction.

    Args:
      func: A transaction function to execute.
      txn_tag: Transaction tag to apply.

    Returns:
      The result the transaction function returned.
    """
    return self._pyspanner.run_in_transaction(func)

  def Mutate(
      self, func: Callable[["Mutation"], None], txn_tag: Optional[str] = None
  ) -> None:
    """Execute the given callback function in a Spanner mutation.

    Args:
      func: A mutation function to execute.
      txn_tag: Optional[str] = None,
    """

    self.Transact(func, txn_tag=txn_tag)

  def Query(self, query: str, txn_tag: Optional[str] = None) -> Cursor:
    """Queries Spanner database using the given query string.

    Args:
      query: An SQL string.
      txn_tag: Spanner transaction tag.

    Returns:
      A cursor over the query results.
    """
    with self._pyspanner.snapshot() as snapshot:
        results = snapshot.execute_sql(query)

    return results

  def QuerySingle(self, query: str, txn_tag: Optional[str] = None) -> Row:
    """Queries PySpanner for a single row using the given query string.

    Args:
      query: An SQL string.
      txn_tag: Spanner transaction tag.

    Returns:
      A single row matching the query.

    Raises:
      NotFound: If the query did not return any results.
      ValueError: If the query yielded more than one result.
    """
    return self.Query(query, txn_tag=txn_tag).one()

  def ParamQuery(
      self, query: str, params: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> Cursor:
    """Queries PySpanner database using the given query string with params.

    The query string should specify parameters with the standard Python format
    placeholder syntax [1]. Note that parameters inside string literals in the
    query itself have to be escaped.

    Also, the query literal is not allowed to contain any '@p{idx}' strings
    inside as that would lead to an incorrect behaviour when evaluating the
    query. To prevent mistakes the function will raise an exception in such
    cases.

    [1]: https://docs.python.org/3/library/stdtypes.html#str.format

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      txn_tag: Spanner transaction tag.

    Returns:
      A cursor over the query results.

    Raises:
      ValueError: If the query contains disallowed sequences.
      KeyError: If some parameter is not specified.
    """
    names, values = collection.Unzip(params.items())
    query =  self._parametrize(query, names)

    param_type = {}
    for key, value in params.items():
      try:
        param_type[key] = self._get_param_type(value)
      except TypeError as e:
        print(f"Warning for key '{key}': {e}. Setting type to None.")
        param_type[key] = None # Or re-raise, or handle differently

    print("query: {}".format(query))
    print("params: {}".format(params))
    print("param_type: {}".format(param_type))

    with self._pyspanner.snapshot() as snapshot:
        results = snapshot.execute_sql(
            query,
            params=params,
            param_types=param_type,
        )

    return results

  def ParamQuerySingle(
      self, query: str, params: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> Row:
    """Queries the database for a single row using with a query with params.

    See documentation for `ParamQuery` to learn more about the syntax of query
    parameters and other caveats.

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      txn_tag: Spanner transaction tag.

    Returns:
      A single result of running the query.

    Raises:
      NotFound: If the query did not return any results.
      ValueError: If the query yielded more than one result.
      ValueError: If the query contains disallowed sequences.
      KeyError: If some parameter is not specified.
    """
    return self.ParamQuery(query, params, txn_tag=txn_tag).one()

  def ParamExecute(
      self, query: str, params: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Executes the given query with parameters against a Spanner database.

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.

    Raises:
      ValueError: If the query contains disallowed sequences.
      KeyError: If some parameter is not specified.
    """
    names, values = collection.Unzip(params.items())
    query =  self._parametrize(query, names)

    param_type = {}
    for key, value in params.items():
      try:
        param_type[key] = self._get_param_type(value)
      except TypeError as e:
        print(f"Warning for key '{key}': {e}. Setting type to None.")
        param_type[key] = None # Or re-raise, or handle differently

    print("query: {}".format(query))
    print("params: {}".format(params))
    print("param_type: {}".format(param_type))

    def param_execute(transaction):
        row_ct = transaction.execute_update(
            query,
            params=params,
            param_types=param_type,
        )

        print("{} record(s) updated.".format(row_ct))
    self._pyspanner.run_in_transaction(param_execute)

  def ExecutePartitioned(
      self, query: str, txn_tag: Optional[str] = None
  ) -> None:
    """Executes the given query against a Spanner database.

    This is a more efficient variant of the `Execute` method, but it does not
    guarantee atomicity. See the official documentation on partitioned updates
    for more information [1].

    [1]: go/spanner-partitioned-dml

    Args:
      query: An SQL query string to execute.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    query_options = None
    if txn_tag is not None:
      query_options = spanner_lib.QueryOptions()
      query_options.SetTag(txn_tag)

    return self._pyspanner.execute_partitioned_dml(query)

  def Insert(
      self, table: str, row: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Insert a row into the given table.

    Args:
      table: A table into which the row is to be inserted.
      row: A mapping from column names to column values of the row.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    columns, values = collection.Unzip(row.items())

    columns = list(columns)
    values = list(values)

    with self._pyspanner.batch() as batch:
      batch.insert(
        table=table,
        columns=columns,
        values=[values]
      )

  def Update(
      self, table: str, row: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Updates a row in the given table.

    Args:
      table: A table in which the row is to be updated.
      row: A mapping from column names to column values of the row.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    columns, values = collection.Unzip(row.items())

    columns = list(columns)
    values = list(values)

    with self._pyspanner.batch() as batch:
      batch.update(
        table=table,
        columns=columns,
        values=[values]
      )

  def InsertOrUpdate(
      self, table: str, row: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Insert or update a row into the given table within the transaction.

    Args:
      table: A table into which the row is to be inserted.
      row: A mapping from column names to column values of the row.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    columns, values = collection.Unzip(row.items())

    columns = list(columns)
    values = list(values)

    with self._pyspanner.mutation_groups() as groups:
      groups.group().insert_or_update(
        table=table,
        columns=columns,
        values=[values]
      )
      for response in groups.batch_write():
        if response.status.code != OK:
          raise Exception(response.status.message)

  def Delete(
      self, table: str, key: Sequence[Any], txn_tag: Optional[str] = None
  ) -> None:
    """Deletes a specified row from the given table.

    Args:
      table: A table from which the row is to be deleted.
      key: A sequence of values denoting the key of the row to delete.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    keyset = KeySet(all_=True)
    if key:
      keyset = KeySet(keys=[key])
    with self._pyspanner.batch() as batch:
      batch.delete(table, keyset)

  def DeleteWithPrefix(self, table: str, key_prefix: Sequence[Any]) -> None:
    """Deletes a range of rows with common key prefix from the given table.

    Args:
      table: A table from which rows are to be deleted.
      key: A sequence of value denoting the prefix of the key of rows to delete.

    Returns:
      Nothing.
    """
    range = KeyRange(start_closed=key_prefix, end_closed=key_prefix)
    keyset = KeySet(ranges=[range])

    with self._pyspanner.batch() as batch:
      batch.delete(table, keyset)

  def Read(
      self,
      table: str,
      key: Sequence[Any],
      cols: Sequence[str],
  ) -> Mapping[str, Any]:
    """Read a single row with the given key from the specified table.

    Args:
      table: A name of the table to read from.
      key: A key of the row to read.
      cols: Columns of the row to read.

    Returns:
      A mapping from columns to values of the read row.
    """
    range = KeyRange(start_closed=key, end_closed=key)
    keyset = KeySet(ranges=[range])
    with self._pyspanner.snapshot() as snapshot:
        results = snapshot.read(
            table=table,
            columns=cols,
            keyset=keyset
        )
    
    return results.one()

  def ReadSet(
      self,
      table: str,
      rows: KeySet,
      cols: Sequence[str],
  ) -> Iterator[Mapping[str, Any]]:
    """Read a set of rows from the specified table.

    Args:
      table: A name of the table to read from.
      rows: A set of keys specifying which rows to read.
      cols: Columns of the row to read.

    Returns:
      Mappings from columns to values of the rows read.
    """
    with self._pyspanner.snapshot() as snapshot:
        results = snapshot.read(
            table=table,
            columns=cols,
            keyset=rows
        )
    
    return results
