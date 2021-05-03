import uuid
app_name = "quest"
INFLIGHT_KEYS = "quest:inflight"

def add_command(arguments):
    command, list_name, value = arguments
    item_identifier = uuid.uuid4()
    execute("RPUSH", list_name, item_identifier)

    items_dictionary = {
            "uuid": item_identifier,
            "value": value,
            "tries": 0
            }
    items_list = list(sum(items_dictionary.items(), tuple()))
    execute("HSET", f"{app_name}:{item_identifier}", *items_list)

def incr_and_get_message(item):
    execute("HINCRBY", f'{app_name}:{item}', 'tries', 1)
    return execute("HGETALL", f'{app_name}:{item}')


def getMessage_command(arguments):
    command, list_name, count = arguments
    results = execute("lrange", list_name, int(0), int(count)-1)
    return list(map(incr_and_get_message, results))

gb = GB('CommandReader')
gb.foreach(add_command)
gb.register(trigger='add')

get_gb = GB('CommandReader')
get_gb.flatmap(getMessage_command)
get_gb.register(trigger='getMessage')
