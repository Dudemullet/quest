import uuid
app_name = "quest"
INFLIGHT_KEYS = "inflight"
KEY_SEPARATOR = ":"
DEFAULT_VISIBILITY_TIMEOUT = 5

def add_command(arguments):
    command, list_name, value, *rest = arguments

    item_identifier = uuid.uuid4()
    execute("RPUSH", list_name, item_identifier)
    items_dictionary = {
            "uuid": item_identifier,
            "value": value,
            "tries": 0,
            "in_flight": False,
            }
    items_list = list(sum(items_dictionary.items(), tuple()))
    execute("HSET", f"{app_name}:{item_identifier}", *items_list)

    #should we make this invisible for now ?
    if len(rest) == 0:
        return
    visibility = int(rest[0])
    flight_a_message(item_identifier, visibility)

def getMessage_command(arguments):
    command, list_name, count, *visibility = arguments

    if len(visibility) == 0:
        visibility = DEFAULT_VISIBILITY_TIMEOUT
    else:
        visibility = int(visibility[0])

    # Only get elements where in_flight = False
    accumulator = []
    index = 0
    while len(accumulator) < int(count):
        item_id = execute('lindex', list_name, index)
        log(f'accu={accumulator} count={count} index={index} item_id={item_id}', level='warning')

        # If no more items in array, exit loop with whatever we have found
        if item_id is None:
            log(f'Array has no more items, accu {accumulator}', level='warning')
            break

        in_flight = execute('hget', f'{app_name}:{item_id}', 'in_flight')
        log(f'in_flight: {in_flight}', level='warning')
        if in_flight == "False":
            log("not in flight", level='warning')
            log(f'appending {item_id}', level='warning')
            accumulator.append(item_id)
        index = index + 1
    return list(map(send_to_in_flight(visibility), accumulator))

def deleteMessage_command(arguments):
    command, list_name, item_id = arguments

    is_in_flight = is_item_in_flight(item_id)
    if not is_in_flight:
        return "Message not in flight"

    # remove timer
    execute("DEL", f'{app_name}{KEY_SEPARATOR}{INFLIGHT_KEYS}{KEY_SEPARATOR}{item_id}')
    # remove from list
    execute("LREM", list_name, 1, item_id)
    # remove data key
    execute("DEL", f'{app_name}{KEY_SEPARATOR}{item_id}')
    return "OK"

def is_item_in_flight(item_id):
    in_flight = execute('hget', f'{app_name}:{item_id}', 'in_flight')
    return in_flight == "True"

## Message flight
def flight_a_message(identifier, timeout):
    execute("HSET", f'{app_name}:{identifier}', 'in_flight', True)
    execute("SETEX", f'{app_name}:{INFLIGHT_KEYS}:{identifier}', str(timeout), None)

def send_to_in_flight(timeout):
    def __process(item):
        execute("HINCRBY", f'{app_name}:{item}', 'tries', 1)
        flight_a_message(item, timeout)
        return execute("HGETALL", f'{app_name}:{item}')
    return __process

def un_flight_a_message(item):
    log(str(item), level='warning')
    one, two, item_id = item['key'].rsplit(KEY_SEPARATOR)
    log(f'Item id: {item_id}', level='warning')
    execute("HSET", f'{app_name}:{item_id}', 'in_flight', False)

gb = GB('CommandReader')
gb.foreach(add_command)
gb.register(trigger='sendMessage')

get_gb = GB('CommandReader')
get_gb.flatmap(getMessage_command)
get_gb.register(trigger='getMessage')

gb = GB('CommandReader')
gb.flatmap(deleteMessage_command)
gb.register(trigger='deleteMessage')

expire_gb = GB('KeysReader')
expire_gb.foreach(un_flight_a_message)
expire_gb.register(prefix=f'{app_name}:{INFLIGHT_KEYS}:*',
             eventTypes=['expired'],
             readValue=False)
