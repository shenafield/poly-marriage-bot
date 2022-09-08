FROM python:3.9-slim
COPY "requirements.txt" .
RUN pip3 install -r requirements.txt
RUN wget https://dl.freefontsfamily.com/download/Impact-Font -O impact.zip
RUN unzip impact.zip
COPY . .
CMD ["python3", "bot.py"]