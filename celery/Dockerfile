FROM python:3.5.2-alpine
MAINTAINER Aldo Culquicondor "aldo@amigocloud.com"

LABEL description="Syncs IGP data for earthquakes to AmigoCloud"

COPY requirements.txt requirements.txt

RUN apk --update add ca-certificates build-base libxml2-dev libxslt-dev python3-dev && \
    rm -rf /var/cache/apk/* && \
    pip install -r requirements.txt && \
    rm requirements.txt && \
    apk del build-base libxml2-dev

WORKDIR /srv/earthquakes_celery

ENV C_FORCE_ROOT=1

COPY . .
