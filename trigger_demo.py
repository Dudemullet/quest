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
            "list": list_name,
            }
    items_list = list(sum(items_dictionary.items(), tuple()))
    execute("HSET", f"{app_name}:{item_identifier}", *items_list)

    #should we make this invisible for now ?
    if len(rest) == 0:
        return
    visibility = int(rest[0])
    flight_a_message(uuid.uuid4(), item_identifier, visibility)

def getMessage_command(arguments):
    command, list_name, count, *visibility = arguments

    if len(visibility) == 0:
        visibility = DEFAULT_VISIBILITY_TIMEOUT
    else:
        visibility = int(visibility[0])

    # Only get elements where in_flight = False
    results = []
    index = 0
    while len(results) < int(count):
        item_id = execute('lindex', list_name, index)
        log(f'accu={results} count={count} index={index} item_id={item_id}', level='warning')

        # If no more items in array, exit loop with whatever we have found
        if item_id is None:
            log(f'Array has no more items, accu {results}', level='warning')
            break

        in_flight = is_item_in_flight(item_id)
        log(f'in_flight={in_flight}', level='warning')
        if not in_flight:
            item_handle = uuid.uuid4()
            log(f'item_id={item_id} item_handle={item_handle} msg=adding item id to results results', level='warning')
            results.append([item_id, item_handle])
        index = index + 1
    return list(map(send_to_in_flight(visibility), results))

def deleteMessage_command(arguments):
    command, list_name, item_handle = arguments

    is_in_flight = is_handle_in_flight(item_handle)
    if not is_in_flight:
        return "Message not in flight"

    item_id = execute('get', f'{app_name}:{INFLIGHT_KEYS}:{item_id}')

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

def is_handle_in_flight(item_handle):
    return bool(execute('exists', f'{app_name}:{INFLIGHT_KEYS}:{item_handle}'))

## Message flight
def flight_a_message(handle, identifier, timeout):
    execute("HSET", f'{app_name}:{identifier}', 'in_flight', True)
    execute("SETEX", f'{app_name}:{INFLIGHT_KEYS}:{handle}', str(timeout), identifier)

def send_to_in_flight(timeout):
    def __process(item_array):
        item_id, item_handle = item_array
        execute("HINCRBY", f'{app_name}:{item_id}', 'tries', 1)
        flight_a_message(item_handle, item_id, timeout)
        results_list = execute("HGETALL", f'{app_name}:{item_id}')
        results.append('handle')
        results.append(item_handle)
        return results_dict
    return __process

def un_flight_a_message(item):
    one_ignore, two_ignore, item_id = item['key'].rsplit(KEY_SEPARATOR)
    log(f'item_id={item_id} msg=visibility expired', level='warning')

    try_count = int(execute("HGET", f'{app_name}:{item_id}', 'tries'))
    dlq_setting = 5
    if(try_count < dlq_setting):
        log(f'item_id={item_id} tries={try_count} dlq_setting={dlq_setting} msg=item has not expired its try count', level='warning')
        execute("HSET", f'{app_name}:{item_id}', 'in_flight', False)
        return "OK"

    # DLQ territory
    log(f'item_id={item_id} tries={try_count} dlq_setting={dlq_setting} msg=try count is over DLQ setting', level='warning')
    list_name = execute("HGET", f'{app_name}:{item_id}', 'list')
    dlq_list_name = f'{list_name}_dlq'
    log(f'item_id={item_id} list_name={list_name} dlq_list_name={dlq_list_name} msg=adding message to DLQ', level='warning')
    execute("LREM", list_name, 1, item_id)
    execute("HSET", f'{app_name}:{item_id}', "tries", 0)
    execute("HSET", f'{app_name}:{item_id}', 'in_flight', False)
    execute("HSET", f'{app_name}:{item_id}', 'list', dlq_list_name)
    execute("RPUSH", dlq_list_name, item_id)


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
             readValue=True)
