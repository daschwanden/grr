summary: How to Add a Client Action
id: how-to-add-a-client-action
categories: GRR
tags: GRR, Client, Action
status: Draft
authors: Tati, Dan
Feedback Link: https://github.com/google/grr/issues

# How to Add a Client Action
<!-- ------------------------ -->
## Before you begin...
Duration: 1

This code lab assumes that you
- understand [GRR's basic concepts](https://www.grr-response.com/),
- read through [GRR's documentation](https://grr-doc.readthedocs.io/) and
- are familiar with [GRR's code base on GitHub](https://github.com/google/grr).

You can follow the [Developing GRR guide](https://grr-doc.readthedocs.io/en/latest/developing-grr/index.html) to learn what you should install on your machine and how to run GRR locally.

The code you'll be touching is mostly Python. You don't need to be an expert to follow along, but if you want more background you can check out [one of many tutorials online](https://www.w3schools.com/python/).

<!-- ------------------------ -->
## Defining the input and outputs for your Client Action
Duration: 2

The input and outputs of your Client Action are its public interface. The input is provided by the Flow when calling your action. The outputs are what you will provide back so it can continue to process.

<aside class="positive">
BEST PRACTICE: Use the <ActionName>Request as input name. This makes the link between them very obvious. For outputs, if the type of return cannot be shared (it's something specific to your action), use <ActionName>Result. Examples of shared/common results are StatEntry (file metadata), BufferReference (partial file content).
</aside>

You'll need to define a ```.proto``` and an equivalent ```RDFValue``` for them. Let's go through [an example](https://github.com/google/grr/blob/master/grr/proto/grr_response_proto/dummy.proto):

```protobuf
message DummyRequest {
  optional string action_input = 1;
}

message DummyResult {
  optional string action_output = 1;
}
```

Next, let's add the corresponding ```RDFValue``` [classes](https://github.com/google/grr/blob/master/grr/core/grr_response_core/lib/rdfvalues/dummy.py). They inherit from ```RDFProtoStruct```, and must have the ```protobuf``` property set. If your proto depends on other ```RDFValues``` (e.g. other protos), you should add them to the list of dependencies in ```rdf_deps``` ([example](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/server/grr_response_server/gui/api_plugins/flow.py#L466C3-L466C11)).

<aside class="positive">
NOTE: RDFValues are a Python class wrapper on top of Protos. At the time they were created, Python proto library was much more limited than it is today (yes, GRR is old). RDFValues exist for legacy reasons and are still used throughout GRR's codebase.
</aside>

```python
#!/usr/bin/env python
"""The various Dummy example rdfvalues."""

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import dummy_pb2


class DummyRequest(rdf_structs.RDFProtoStruct):
  """Request for Dummy action."""

  protobuf = dummy_pb2.DummyRequest
  rdf_deps = []


class DummyResult(rdf_structs.RDFProtoStruct):
  """Result for Dummy action."""

  protobuf = dummy_pb2.DummyResult
  rdf_deps = []
```

An important detail is that for Client Actions, we prefer adding the class to a separate file (see below). This is because we need to import it in both the server and the client. For Flows, we usually prefer to define them close to the Flow class definition themselves (see more on [Adding Flows](../how-to-add-a-flow/index.html)).

<!-- ------------------------ -->
## Writing the Client Action class
Duration: 3

Client Actions are classes that inherit from [```ActionPlugin```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/actions.py#L78). The class must override:

- [```in_rdfvalue```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/actions.py#L98) and [```out_rdfvalues```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/actions.py#L103) properties: these are the public interface for your action - the ```in```nput provided from a Flow to the Action; and the ```out```put that your Action will return to the Flow. An important detail here is that these values must be ```RDFValue```s.
- [```Run```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/actions.py#L263) method: you can think of this as your action's ```main```. It is the entrypoint for your action, and when it returns, the action finishes.

The [```ActionPlugin```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/actions.py#L78) base class has many helper functions that can be used. Here are the most important ones to be aware of:

- [```Progress```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/actions.py#L341): If your action is not "instantaneous", you should consider calling this periodically. Acts like a heartbeat so we know the client is responsive, just busy.
- [```ChargeBytesToSession```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/actions.py#L384): Registers the amount of bytes being sent from Client to Server. The network threshold is checked periodically, and this updates the current usage.
- [```SendReply```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/actions.py#L290): Sends a reply (output(s) of your action) to the parent Flow.
Whith that in mind, let's write our Dummy client action. The action will be simple, reading an input string, modifying it, and sending a string back. It will be available in all three platforms (windows, mac, linux), but behave differently in each one.

### Writing the Unix implementation

Our action will be the same for Linux and MacOS (Unix). So, we'll add it to the [common/shared directory](https://github.com/google/grr/blob/master/grr/client/grr_response_client/client_actions/dummy.py).

```python
class Dummy(actions.ActionPlugin):
  """Returns the received string."""

  in_rdfvalue = rdf_dummy.DummyRequest
  out_rdfvalues = [rdf_dummy.DummyResult]

  def Run(self, args: rdf_dummy.DummyRequest) -> None:
    """Returns received input back to the server."""

    if not args.action_input:
      raise RuntimeError("args.action_input is empty, cannot proceed!")

    self.SendReply(
        rdf_dummy.DummyResult(
            action_output=f"args.action_input: '{args.action_input}'"
        )
    )
```

<aside class="positive">
NOTE: On our example, we return a single response. In real life, you might want to send multiple responses (even of different types). You can consider this in your design, and take a look at existing actions that have multiple types in out_rdfvalues.
</aside>

### Writing the platform-specific (Windows) implementation

For Windows, we will write a [dedicated action](https://github.com/google/grr/blob/master/grr/client/grr_response_client/client_actions/windows/dummy.py). It'll live in the windows folder. For

```python
class Dummy(actions.ActionPlugin):
  """Returns the received string."""

  in_rdfvalue = rdf_dummy.DummyRequest
  out_rdfvalues = [rdf_dummy.DummyResult]

  def Run(self, args: rdf_dummy.DummyRequest) -> None:
    """Returns received input back to the server, but in Windows."""

    if not args.action_input:
      raise RuntimeError("WIN args.action_input is empty, cannot proceed!")

    self.SendReply(
        rdf_dummy.DummyResult(
            action_output=f"WIN args.action_input: '{args.action_input}'"
        )
    )
```

<!-- ------------------------ -->
## Writing the Client Action unit tests
Duration: 1

### Unix implementation unit tests

Here's an [example test](https://github.com/google/grr/blob/master/grr/client/grr_response_client/client_actions/dummy_test.py) for our very simple Client Action. We only need a couple of cases to cover the branches of our logic. In your case, consider what are the boundary conditions you'd like to check as well as what conditions are needed for them (you might need to mock some files, for example).

<aside class="negative">
IMPORTANT: ALWAYS submit your tests together with the code.
</aside>

Whenever a Client Action reaches the end of the processing, the Client sends a Status message back to the server. This is usually the last message sent to the server.

On our unit tests below, we're including this message in the tests. On the successful test case, we also test the status code is ```OK```. On the failure scenario, we test that it returned a ```GENERIC_ERROR``` (since we raise a ```RuntimeException``` in the action). ```Status``` messages can have other values as well (e.g. reached a limit). You can take a look at other actions and the proto to see how else it can be used.

```python
  def testDummyReceived(self):
    action_request = rdf_dummy.DummyRequest(action_input="banana")

    # We use `ExecuteAction` instead of `RunAction` to test `status` result too.
    results = self.ExecuteAction(dummy.Dummy, action_request)

    # One result, and one status message.
    self.assertLen(results, 2)

    self.assertIsInstance(results[0], rdf_dummy.DummyResult)
    self.assertIn("banana", results[0].action_output)

    self.assertIsInstance(results[1], rdf_flows.GrrStatus)
    self.assertEqual(rdf_flows.GrrStatus.ReturnedStatus.OK, results[1].status)
    self.assertEmpty(results[1].error_message)

  def testErrorsOnEmptyInput(self):
    action_request = rdf_dummy.DummyRequest()

    # We use `ExecuteAction` instead of `RunAction` to test `status` result too.
    results = self.ExecuteAction(dummy.Dummy, action_request)

    # One status message.
    self.assertLen(results, 1)

    self.assertIsInstance(results[0], rdf_flows.GrrStatus)
    self.assertEqual(
        rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR, results[0].status
    )
    self.assertIn("empty", results[0].error_message)
```

### Windows implementation unit tests

For Windows, we're doing exactly the [same as the above](https://github.com/google/grr/blob/master/grr/client/grr_response_client/client_actions/windows/dummy_test.py), except for some extra assertions that match the Client Action behavior on Windows.

```python
def testDummyReceived(self):
    action_request = rdf_dummy.DummyRequest(action_input="banana")

    # We use `ExecuteAction` instead of `RunAction` to test `status` result too.
    results = self.ExecuteAction(dummy.Dummy, action_request)

    # One result, and one status message.
    self.assertLen(results, 2)

    self.assertIsInstance(results[0], rdf_dummy.DummyResult)
    self.assertIn("banana", results[0].action_output)
    self.assertIn("WIN", results[0].action_output)

    self.assertIsInstance(results[1], rdf_flows.GrrStatus)
    self.assertEqual(rdf_flows.GrrStatus.ReturnedStatus.OK, results[1].status)
    self.assertEmpty(results[1].error_message)

  def testErrorsOnEmptyInput(self):
    action_request = rdf_dummy.DummyRequest()

    # We use `ExecuteAction` instead of `RunAction` to test `status` result too.
    results = self.ExecuteAction(dummy.Dummy, action_request)

    # One status message.
    self.assertLen(results, 1)

    self.assertIsInstance(results[0], rdf_flows.GrrStatus)
    self.assertEqual(
        rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR, results[0].status
    )
    self.assertIn("empty", results[0].error_message)
```

<!-- ------------------------ -->
## Registering your Client Action
Duration: 1

Now that we have an implemented and tested action, we can register it so it is available to be called (cl/559042698)! Hooray!

For that you need to add it to the following places:

To the [```server_stubs```](https://github.com/google/grr/blob/master/grr/server/grr_response_server/server_stubs.py#L54). The stub must have the same name, ```in_``` and ```out_rdfvalues``` as your class declared on the previous step.

```python
class Dummy(ClientActionStub):
  """Dummy example. Reads a message and sends it back."""

  in_rdfvalue = rdf_dummy.DummyRequest
  out_rdfvalues = [rdf_dummy.DummyResult]
```

To the [```action_registry```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/server/grr_response_server/action_registry.py#L10) and [```registry_init```](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/client_actions/registry_init.py#L74). The registry key should also have the same class name. Note that, we're registering this implementation for both Linux and Darwin, but will do something different for Windows (see next step).

```python
   "Dummy": server_stubs.Dummy,
```

```python
client_actions.Register("Dummy", dummy.Dummy)
```

### Registering platform-specific

Notice that when registering it, we'll register it on the [```Windows```] [section](https://github.com/google/grr/blob/a6f1b31abfe82794b7d82fa8d54d8bd94bfed1bb/grr/client/grr_response_client/client_actions/registry_init.py#L87) of the code.

```python
client_actions.Register("Dummy", win_dummy.Dummy)
```

<!-- ------------------------ -->
## ... And now to call it from a Flow!
Duration: 1

That's it, your Client Action is complete! Now you can start using it in an existing or new Flow! See [Adding a Flow](../how-to-add-a-flow/index.html)
