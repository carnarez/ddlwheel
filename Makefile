# docker flags
dkflags=--rm \
        --tty \
		--user "$$(id -u)":"$$(id -g)" \
        --volume /etc/group:/etc/group:ro \
        --volume /etc/passwd:/etc/passwd:ro \
        --volume /etc/shadow:/etc/shadow:ro \
        --volume "$(PWD)/ddltree":/usr/src \
        --volume "$(PWD)/samples":/usr/local/samples \
        --workdir /usr/src

# interactive flags
itflags=--entrypoint /bin/bash --interactive

build:
	@docker build --tag ddltree .

clean:
	@rm -fr $$(find . -name __pycache__)

test: build
	# @docker run $(dkflags) ddltree \
	#     python -m pytest --color=yes --cov=ddltree --override-ini="cache_dir=/tmp/pytest" --verbose
	@docker run $(dkflags) ddltree /bin/sh -c "python sql.py /usr/local/samples/fact_order_details.sql"

dev: build
	@docker run --name ddltree $(dkflags) $(itflags) ddltree
