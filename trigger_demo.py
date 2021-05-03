import uuid
app_name = "quest"
INFLIGHT_KEYS = "inflight"
KEY_SEPARATOR = ":"
DEFAULT_VISIBILITY_TIMEOUT = 5

def add_command(arguments):
    command, list_name, value = arguments
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

def getMessage_command(arguments):
    command, list_name, count, *visibility = arguments

    if len(visibility) == 0:
        visibility = DEFAULT_VISIBILITY_TIMEOUT
    else:
        visibility = int(visibility[0])

    results = execute("lrange", list_name, int(0), int(count)-1)
    return list(map(send_to_in_flight(visibility), results))

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
gb.register(trigger='add')

get_gb = GB('CommandReader')
get_gb.flatmap(getMessage_command)
get_gb.register(trigger='getMessage')

expire_gb = GB('KeysReader')
expire_gb.foreach(un_flight_a_message)
expire_gb.register(prefix=f'{app_name}:{INFLIGHT_KEYS}:*',
             eventTypes=['expired'],
             readValue=False)
