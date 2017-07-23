#! /bin/bash

#chmod +x startserver*.sh
#chmod +x scripts/stopserver.sh
sudo pip install --upgrade pip
sudo pip install --upgrade virtualenv
virtualenv venv
source venv/bin/activate

echo "Installing mysql connector"
wget http://dev.mysql.com/get/Downloads/Connector-Python/mysql-connector-python-2.1.3.zip
unzip mysql-connector-python-2.1.3.zip
cd mysql-connector-python-2.1.3/
python setup.py install
echo "Installing done for mysql connector"
cd ..
rm mysql-connector-python-2.1.3.zip
rm -r mysql-connector-python-2.1.3


echo Ensure pip latest version
pip install --no-cache-dir --upgrade pip
#latest needed for apscheduler
pip install --no-cache-dir --upgrade setuptools

echo Install mandatory requirements
pip install --no-cache-dir -r requirements.txt

echo Install optional requirements, you can ignore errors
res=`cat /etc/os-release | grep raspbian -q ; echo $?`
if [ "$res" == "0" ]; then
	pip install --no-cache-dir -r requirements-rpi.txt
else
	pip install --no-cache-dir -r requirements-beaglebone.txt
	#todo: fix script for windows
	#pip install --no-cache-dir -r requirements-win.txt
fi


#echo "Installing pigpio python module, assuming is installed in user home folder"
#cd ../PIGPIO
#python setup.py install
#cd ../PYC

#echo "Installing kivy"
# http://kivy.org/docs/installation/installation-linux.html
#pip install Cython==0.21.2
#pip install kivy
