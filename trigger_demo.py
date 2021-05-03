import uuid
app_name = "tempo"

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
    execute("HSET", f"tempo:{item_identifier}", *items_list)

gb = GB('CommandReader')
gb.foreach(add_command)
gb.register(trigger='add')
