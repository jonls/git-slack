FROM ubuntu:14.04
MAINTAINER Jon Lund Steffensen <jonlst@gmail.com>

RUN apt-get update && apt-get install -y \
    git \
    libyaml-dev \
    python \
    python-dev \
    python-pip

RUN pip install \
    git+https://github.com/jonls/git-slack.git

CMD ["/usr/local/bin/git-slack", "--config", "/etc/git-slack/config.yaml"]
