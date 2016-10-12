#!/bin/bash
set -e

ODB_DEV_DIR=/tmp/orientdb
ODB_VERSION=2.2.11
ODB_WORK_DIR=/opt/orientdb

[ -f $ODB_WORK_DIR/bin/server.sh ] && echo "Use cached OrientDB" && exit 0

mkdir -p $ODB_DEV_DIR
cd $ODB_DEV_DIR
wget -O orientdb-community-$ODB_VERSION.tar.gz "https://orientdb.com/download.php?file=orientdb-community-$ODB_VERSION.tar.gz"
tar xf orientdb-community-$ODB_VERSION.tar.gz
sed -i \
    -e "s|YOUR_ORIENTDB_INSTALLATION_PATH|$ODB_WORK_DIR|" \
    -e "s|USER_YOU_WANT_ORIENTDB_RUN_WITH||" \
    orientdb-community-$ODB_VERSION/bin/orientdb.sh

# add user and storage to server config
sed -i \
    -e 's|</storages>|<storage path="memory:temp" name="temp" userName="sovrin" userPassword="password" loaded-at-startup="true" />\n&|' \
    -e 's|</users>|<user name="sovrin" password="password" resources="\*" />\n<user name="root" password="password" resources="\*" />\n&|' \
    orientdb-community-$ODB_VERSION/config/orientdb-server-config.xml

sudo rm -rf $ODB_WORK_DIR
sudo mv orientdb-community-$ODB_VERSION $ODB_WORK_DIR

