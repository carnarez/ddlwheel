FROM python:3.10-slim

ENV COVERAGE_FILE=/tmp/coverage

RUN pip install --upgrade pip \
 && pip install --no-cache-dir pytest \
                               pytest-cov \
                               sqlparse \
                               sqlfluff

COPY ddltree/ /usr/src/
COPY samples /usr/local/samples

WORKDIR /usr/src

CMD ["/usr/bin/python", "sql.py", "/usr/local/samples/fact_order_details.sql"]
