FROM jcr.apops.bocsoft.it/docker-local/python:3.12.5-slim
LABEL  maintainer Xi Siyuan "yokoxsy@msn.com"

WORKDIR /messagebridge
EXPOSE 5000

COPY requirements /tmp

RUN cd  /tmp \
    && pip install -r requirements   \
          -i http://nexus3.apops.bocsoft.it/repository/pypi-group/simple   \
          --trusted-host nexus3.apops.bocsoft.it \
    && rm requirements \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

COPY . /messagebridge

CMD ["flask", "run", "--host=0.0.0.0"]
