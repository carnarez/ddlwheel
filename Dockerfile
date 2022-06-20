FROM python:3.10-slim

ENV COVERAGE_FILE=/tmp/coverage

RUN pip install --upgrade pip \
 && pip install --no-cache-dir pytest \
                               pytest-cov \
                               redshift-connector \
                               sqlparse \
                               tqdm

COPY ddlwheel/ /usr/src/
COPY www/ /var/www
