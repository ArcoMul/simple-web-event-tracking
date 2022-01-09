FROM python:3.10.1-alpine3.15

WORKDIR /app

RUN set -x \
  && apk update \
  && apk add --no-cache bash

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

ENTRYPOINT ["/app/entrypoint.sh"]
