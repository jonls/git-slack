FROM ubuntu:14.04
MAINTAINER Jon Lund Steffensen <jonlst@gmail.com>

RUN apt-get update && apt-get install -y \
    git \
    libyaml-dev \
    librabbitmq-dev \
    python3 \
    python3-dev \
    python3-pip

RUN pip3 install \
    git+https://github.com/jonls/git-slack.git

CMD ["/usr/local/bin/git-slack", "--config", "/etc/git-slack/config.yaml"]
