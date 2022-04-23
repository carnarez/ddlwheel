# docker flags
dkflags=--env-file .env \
        --name ddlwheel \
        --rm \
        --tty \
        --user "$$(id -u)":"$$(id -g)" \
        --volume /etc/group:/etc/group:ro \
        --volume /etc/passwd:/etc/passwd:ro \
        --volume /etc/shadow:/etc/shadow:ro \
        --volume "$(PWD)/ddlwheel":/usr/src \
        --volume "$(PWD)/html":/var/www \
        --workdir /usr/src

# interactive flags
itflags=--entrypoint /bin/bash \
        --interactive

build:
	@docker build --tag ddlwheel .

serve: build
	@docker run $(dkflags) --publish 8000:8000 ddlwheel \
		python -m http.server --directory /var/www

env: build
	@docker run $(dkflags) $(itflags) ddlwheel
