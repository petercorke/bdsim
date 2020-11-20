# would like to support hosting bdsim-web and the tuner directly over websockets. however:

# Want to avoid the asyncio dependency because it doesn't appear supported by circuitpython and is a large dependency
# also want to avoid _thread because it is experimental on mpy and unsupported by circuitpy

# Haven't been able to find a PyPi module that meets these design constraints but
# There is a blog post about it that uses raw sockets which should save a lot of development time:
# https://superuser.blog/websocket-server-python/
# implementing that here should do the trick and work for CPython and all micropython variants
