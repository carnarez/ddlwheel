FLAGS=--name ddlwheel \
     --rm \
     --tty \
     --user "$$(id -u)":"$$(id -g)" \
     --volume /etc/group:/etc/group:ro \
     --volume /etc/passwd:/etc/passwd:ro \
     --volume /etc/shadow:/etc/shadow:ro \
     --volume "$(PWD)/ddlwheel":/usr/src \
     --volume "$(PWD)/www":/var/www \
     --workdir /usr/src

build:
	@docker build --tag ddlwheel .

clean:
	@rm -fr $$(find . -name __pycache__)

env: build
	@docker run $(FLAGS) --entrypoint /bin/bash --interactive ddlwheel

serve: build
	@docker run $(FLAGS) --publish 8000:8000 ddlwheel \
		python -m http.server --directory /var/www

test: build
	@docker run $(FLAGS) --env COLUMNS=$(COLUMNS) ddlwheel \
	    python -m pytest --capture=no \
	                     --color=yes \
	                     --cov=ddlwheel \
	                     --cov-report term-missing \
	                     --override-ini="cache_dir=/tmp/pytest" \
	                     --verbose \
	                     --verbose
