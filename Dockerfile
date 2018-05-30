FROM python:3.6-slim-stretch
RUN apt-get update
RUN apt-get install -y python3-dev gcc git
RUN pip install datasette
ADD registry.db .
ADD metadata.json .
RUN datasette inspect registry.db --inspect-file inspect-data.json

EXPOSE 8001

CMD datasette serve registry.db --host 0.0.0.0 \
    --cors --port 8001 --inspect-file inspect-data.json -m metadata.json
