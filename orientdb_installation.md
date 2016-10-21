## PreRequisite

Install JRE if you don't have it installed

```
sudo apt-get install default-jre
```
## OrientDB download and installation

Download the latest community version of orientdb for Linux from here. http://orientdb.com/download/.

```
wget http://orientdb.com/download.php?file=orientdb-community-2.2.5.tar.gz -O /tmp/orientdb.tar.gz
```
Extract orientdb to /opt/orientdb

```
sudo mkdir -p /opt/orientdb
sudo tar xzvf /tmp/orientdb.tar.gz --strip-components=1 -C /opt/orientdb

```
**Note:** We have used 'sovrin' as user name (assuming already created), if you want to replace it with other user name, modify steps accordingly and then execute

Setup installation directory path and user name </br>
**Note:** Replace **<actualusername>** in below command (with system username  you want to run orientdb as) and then execute it

```
sudo sed -i 's/YOUR_ORIENTDB_INSTALLATION_PATH/\/opt\/orientdb/g' /opt/orientdb/bin/orientdb.sh
sudo sed -i 's/USER_YOU_WANT_ORIENTDB_RUN_WITH/<actualusername>/g' /opt/orientdb/bin/orientdb.sh
```

Set up users and storages section as below:</br>
**Note:** There should not be any other entry with name="root", if there is comment it out or remove it.

```
sudo sed -i 's/<users>/<users>\n       <user name="root" password="password" resources="*" \/>\n       <user name="sovrin" password="password" resources="*" \/>/g' /opt/orientdb/config/orientdb-server-config.xml
sudo sed -i 's/<storages>/<storages>\n       <storage path="memory:temp" name="temp" userName="sovrin" userPassword="password" loaded-at-startup="true" \/> /g' /opt/orientdb/config/orientdb-server-config.xml
```

## Validation:

count should be 1: 

```
grep "user name=\"root\"" /opt/orientdb/config/orientdb-server-config.xml | wc -l
```
count should be 2: 


```
grep "<storage" /opt/orientdb/config/orientdb-server-config.xml | wc -l
```

Now do :

```
sudo chmod 640 /opt/orientdb/config/orientdb-server-config.xml
```

Change owner and permissions for files in /opt/orientdb

**Note:** Replace <unix user name> and then execute

```
sudo chown -R <unix user name> /opt/orientdb
sudo chgrp -R <unix user name> /opt/orientdb
sudo chmod -R 744 /opt/orientdb/databases
sudo chmod 755 /opt/orientdb/bin/*.sh

```
Make a symlink of orientdb.sh in /etc/init.d/

```
sudo ln -s -f /opt/orientdb/bin/orientdb.sh /etc/init.d/orientdb
```

Add global config for OrientDB in ~/.sovrin/sovrin_config.py

```
mkdir -p ~/.sovrin

cnt=`grep "OrientDB = {" ~/.sovrin/sovrin_config.py  | wc -l`

if [ $cnt == 0 ]; then
echo '
OrientDB = {
    "user": "sovrin",
    "password": "password",
    "startScript": "/opt/orientdb/bin/server.sh",
    "shutdownScript": "/opt/orientdb/bin/shutdown.sh"
}
' >>~/.sovrin/sovrin_config.py
fi;

```


## Start orientdb service

```
service orientdb start
```

## References:

http://orientdb.com/docs/last/Tutorial-Installation.html
