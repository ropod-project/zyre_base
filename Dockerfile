FROM blumenthal/ropod-base-cpp:latest

RUN apt-get -y update && apt-get install -y \
    vim \
    git \
    cmake \
    build-essential \
    automake \
    libtool \
    libtool-bin \
    pkg-config \
    wget \
    curl \
    unzip \
    libssl-dev \
    libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

ADD . /opt/ropod/ropod_common/
