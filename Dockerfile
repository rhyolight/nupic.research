FROM ubuntu:14.04

USER root

# https://askubuntu.com/questions/496549/error-you-must-put-some-source-uris-in-your-sources-list
RUN sed -Ei 's/^# deb-src /deb-src /' /etc/apt/sources.list

# Install OS dependencies
RUN apt-get update && \
    apt-get install -y \
            build-essential \
            libssl-dev \
            libffi-dev \
            git-core \
            clang \
            cmake3 \
            curl \
            wget \
            python \
            python2.7 \
            python2.7-dev \
            graphviz \
            graphviz-dev && \
    wget http://releases.numenta.org/pip/1ebd3cb7a5a3073058d0c9552ab074bd/get-pip.py -O - | python

RUN pip install --upgrade --ignore-installed \
        setuptools==36.2.7 \
        wheel==0.29.0 \
        pipdeptree==0.10.1 \
        ndg-httpsclient==0.3.1 \
        awscli==1.11.129

RUN apt-get build-dep -y matplotlib

WORKDIR /usr/local/htmresearch
ADD . /usr/local/htmresearch

RUN pip install .

# Use matplotib 'Agg' backend
ENV MPLBACKEND "Agg"
