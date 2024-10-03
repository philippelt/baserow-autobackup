FROM python:3.11-alpine
LABEL author=ph.larduinat@wanadoo.fr

ENV PYTHONIOENCODING utf-8
ENV LANG             fr_FR.UTF-8
ENV TZ               Europe/Paris

ADD ./requirements.txt /pyapp/
WORKDIR /pyapp/

RUN pip3.11 install --no-cache-dir -r requirements.txt

ADD auto_backup.py /pyapp/

CMD python3 -u auto_backup.py