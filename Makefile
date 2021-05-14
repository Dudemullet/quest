load:
	@cat app.py | redis-cli --no-raw -x RG.PYEXECUTE;

unload:
	@redis-cli --raw RG.DUMPREGISTRATIONS | sed -n '2 p' | xargs -t redis-cli RG.UNREGISTER;

flush:
	@redis-cli FLUSHALL;

demo:
	@cat demo_data.txt | xargs -L 1 redis-cli;

start:
	@docker run -d --name redisgears -p 6379:6379 redislabs/redisgears:latest;
