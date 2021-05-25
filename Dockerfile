FROM python:3.8

RUN mkdir -p /usr/src/cryptocurrency_bot/
WORKDIR /usr/src/cryptocurrency_bot/cryptocurrency_bot/

COPY . /usr/src/cryptocurrency_bot/

RUN pip install --no-cache-dir -r ../requirements.txt

CMD ["python", "manage.py", "run"]
