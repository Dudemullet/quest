# Redis Quest
This is a redis module (using RedisGears) that provides AWS SQS like api on top of redis.

## Supported features
  - Visibility timeout
  - inFlight visibility
  - Dead letter queues
  - Message handle

## Installing
There are a set of commands in the `Makefile` which will help you run and install this library locally. To be able to run this on your redis server you need to make sure the `RedisGears` module is loaded on that redis server.

### start (Requires Docker)

`make start` runs a `RedisGears` enabled redis server via docker

### load

Will load all of the libraries commands into your local redis server. You could modify this command to target your remote redis server. After loading this module on a redis server you will be able to run the commands on that server.

### unload (WARNING ⚠️ )

Will unregister commands from a redis server. This was useful while testing but should not be used in a server where other `RedisGears` commands are loaded as this will delete them indescriminately.

## Api
This module adds 3 different `RedisGears` commands.

### sendMessage
Sends a message to a queue with an optional visibility timeout.

```python
RG.TRIGGER sendMessage list_name value [timeout]
```

>list_name (required)

The name of the list to add this message to

>value (required)

The message itself

>timeout (optional)

Amount of seconds before this message is visible

### getMessage
Get a message from a list and optionally set its visibility timeout.

```python
RG.TRIGGER getMessage list_name count [timeout]
```

>list_name (required)

The name of the list to get messages from

>count (required)

The amount of messages to get from the list

>timeout (optional)

Amount of seconds you need to process this message, after the timeout. Quest will make this message visible again for anyone else to process and the handle will not be able to remove this message from the list

#### Returns
The list of items specified by count or an empty array if list doesn't exist or has no more items. If the list has less items available(not in-flight) than those specified by count it will only return those.

each item is represented by an array of values that map to a dictionary:

`"['uuid', <uuid>, 'value', <msg_value>, 'tries', <number>, 'in_flight', <python_bool[True|False]>, 'list', <string>, 'handle', <uuid>]"`

#### Message fields

>uuid

The immutable id given to the message when sent to Quest. This uuid will never change inside Quest even when the message gets moved to a DLQ

>value

whatever value was assigned to the message when added to Quest

>tries

The amount of times the message has been delivered before without it being deleted/processed. In the apps current state, after reaching `5` it will be sent to a `DLQ`

>in_flight

For internal use only. Flag to know if the message is  currently in flight or not

>list

The name of the list this message was retrieved from

>handle

The <uuid> used to delete this message

### deleteMessage
Delete a message from a queue

```python
RG.TRIGGER deleteMessage list_name handle
```

>list_name (required)

The list to remove this message from

>handle (required)

The handle given to this message via `getMessage`. Notice that a single message gets different handles every time it delivered via `getMessage`

If a message tries to get deleted after its `timeout` has expired a `Message not in flight` message will be returned
