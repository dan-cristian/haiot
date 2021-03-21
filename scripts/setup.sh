#! /bin/bash

#chmod +x startserver*.sh
#chmod +x scripts/stopserver.sh
source venv/bin/activate
if [ "$?" != "0" ]; then
    echo "detected that venv is not installed"
    #python 2.7 install
    #sudo pip install --upgrade pip
    #sudo pip install virtualenv
    #virtualenv --system-site-packages venv

    #python3 install
    #https://raspberrypi.stackexchange.com/questions/9246/how-to-install-smbus-to-virtualenv
    sudo apt install python3-venv
    python3 -m venv 3venv
    source 3venv/bin/activate
fi

# echo "Installing mysql connector"
# wget http://dev.mysql.com/get/Downloads/Connector-Python/mysql-connector-python-2.1.3.zip
# unzip mysql-connector-python-2.1.3.zip
# cd mysql-connector-python-2.1.3/
# python setup.py install
# echo "Installing done for mysql connector"
# cd ..
# rm mysql-connector-python-2.1.3.zip
# rm -r mysql-connector-python-2.1.3

#setuptools latest needed for apscheduler
echo "Updating pip etc."
if [ ! -f /tmp/updated_pip ]; then
    pip install --no-cache-dir --upgrade pip
    pip install --no-cache-dir --upgrade setuptools
    touch /tmp/updated_pip
fi

echo Install mandatory requirements
pip install --no-cache-dir -r requirements.txt

echo Install optional requirements, you can ignore errors
res=`cat /etc/os-release | grep raspbian -q ; echo $?`
if [ "$res" == "0" ]; then
	pip install --no-cache-dir -r requirements-rpi.txt
else
	pip install --no-cache-dir -r requirements-beaglebone.txt
fi

echo "Setup python done"
