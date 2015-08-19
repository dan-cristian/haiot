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