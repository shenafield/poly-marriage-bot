FROM python:3.9-slim
COPY "requirements.txt" .
RUN apt-get update && apt-get -y install wget unzip
RUN pip3 install -r requirements.txt
RUN wget https://dl.freefontsfamily.com/download/Impact-Font -O impact.zip
RUN unzip impact.zip
COPY . .
CMD ["python3", "bot.py"]