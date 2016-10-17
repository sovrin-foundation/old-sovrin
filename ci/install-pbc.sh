#!/bin/bash
set -e

if [ -d $HOME/pbc/usr ]; then
    echo "Use cached PBC."
else
    PBC_DEV_DIR=/tmp/pbc-build

    mkdir -p $PBC_DEV_DIR
    cd $PBC_DEV_DIR
    wget https://crypto.stanford.edu/pbc/files/pbc-0.5.14.tar.gz
    tar xf pbc-0.5.14.tar.gz
    cd pbc-0.5.14
    ./configure
    make
    make install DESTDIR=$HOME/pbc
fi

sudo cp -P $HOME/pbc/usr/local/lib/libpbc.so* /usr/local/lib
sudo cp -r $HOME/pbc/usr/local/include/pbc /usr/local/include
sudo ldconfig -n /usr/local/lib

