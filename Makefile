load:
	@cat trigger_demo.py | redis-cli --no-raw -x RG.PYEXECUTE;

unload:
	@redis-cli --raw RG.DUMPREGISTRATIONS | sed -n '2 p' | xargs -t redis-cli RG.UNREGISTER

nuke-keys:
	@redis-cli FLUSHALL;

clean: unload nuke-keys
