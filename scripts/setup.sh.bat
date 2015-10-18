#! /bin/bash
chmod +x startserver*.sh
chmod +x scripts/stopserver.sh
sudo pip install --upgrade pip
sudo pip install virtualenv
virtualenv venv
source venv/bin/activate
#ensure latest version
pip install --upgrade pip
#latest needed for apscheduler
pip install --upgrade setuptools
#mandatory requirements
pip install -r requirements.txt
#optional requirements
pip install -r requirements-beaglebone.txt
pip install -r requirements-rpi.txt
pip install -r requirements-win.txt

# installing mysql connector
wget http://dev.mysql.com/get/Downloads/Connector-Python/mysql-connector-python-2.1.3.zip
unzip mysql-connector-python-2.1.3.zip
cd mysql-connector-python-2.1.3/
python setup.py install
cd ..
rm mysql-connector-python-2.1.3.zip
rm -r mysql-connector-python-2.1.3