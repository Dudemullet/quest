def cas(x):
    log(str(x), level='warning')

# Event handling function registration
gb = GearsBuilder()
gb.foreach(cas)
gb.register('person:*', convertToStr=True)

## Expected result: ['OK']
