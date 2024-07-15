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

This text assumes you
- understand [GRR's basic concepts](https://www.grr-response.com/),
- read through [GRR's documentation](https://grr-doc.readthedocs.io/) and
- are familiar with [GRR's code base on GitHub](https://github.com/google/grr).

You can follow the [Developing GRR guide](https://grr-doc.readthedocs.io/en/latest/developing-grr/index.html) to learn what you should install on your machine and how to run GRR locally.

The code you'll be touching is mostly Python. You shouldn't need to be an expert on it to follow along, but if you want some resources you can check out [one of many tutorials online](https://www.w3schools.com/python/).

<!-- ------------------------ -->
## Defining the input and outputs for your Client Action
Duration: 2



<!-- ------------------------ -->
## Writing the Client Action class
Duration: 3



### Writing the Unix implementation


### Writing the platform-specific (Windows) implementation


<!-- ------------------------ -->
## Writing the Client Action unit tests
Duration: 1

### Unix implementation unit tests

### Windows implementation unit tests

<!-- ------------------------ -->
## Registering your Client Action
Duration: 1


### Registering platform-specific

<!-- ------------------------ -->
## ... And now to call it from a Flow!
Duration: 1

That's it, your Client Action is complete! Now you can start using it in an existing or new Flow!
