FROM python:3.7
WORKDIR /app

RUN pip install -U pyrogram tgcrypto
RUN pip install -U https://github.com/pyrogram/pyrogram/archive/asyncio.zip
RUN pip install pyyaml
RUN pip install psycopg2

COPY . .
ENTRYPOINT ["python", "bot.py"]
