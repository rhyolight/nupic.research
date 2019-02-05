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
RUN pip uninstall -y tensorflow heroku quilt
# Install nupic and nupic.core dependencies
RUN pip install asteval==0.9.1 \
        coverage==3.7.1 \
        mock==1.0.1 \
        ordereddict==1.1 \
        psutil==1.0.1 \
        pytest==3.0.7 \
        pytest-cov==2.5.0 \
        pytest-xdist==1.16.0 \
        python-dateutil==2.1 \
        PyYAML==3.10 \
        unittest2==0.5.1 \
        validictory==0.9.1 \
        PyMySQL==0.6.2 \
        DBUtils==1.1 \
        pyproj==1.9.3 \
        prettytable==0.7.2 \
        pycapnp==0.6.3 \
        numpy==1.12.1
# Install htmresearch and htmresearch-core dependencies
RUN apt-get build-dep -y matplotlib
RUN pip install matplotlib==2.1.0 \
        urllib3[secure]==1.22 \
        pandas==0.18.1 \
        plotly==2.0.13 \
        simplejson==2.6.2 \
        tabulate==0.7.5 \
        tqdm==4.8.4 \
        prettytable==0.7.2 \
        plyfile==0.5 \
        pyqtgraph==0.10.0 \
        scipy==1.0.0rc1 \
        scikit-learn==0.19.0 \
        seaborn==0.8.1 \
        gensim==3.0.0 \
        tensorflow==1.12.0 \
        onnx==1.3.0 \
        onnx-tf==1.2.0 \
        torch==1.0.0 \
        torchvision==0.2.1 \
        librosa>=0.6.2 \
        scikit-image>=0.14.1
# Use matplotib 'Agg' backend
ENV MPLBACKEND "Agg"
