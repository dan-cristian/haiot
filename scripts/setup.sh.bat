#! /bin/bash
chmod +x startserver*.sh
chmod +x scripts/stopserver.sh
sudo pip install --upgrade pip
sudo pip install virtualenv
virtualenv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-beaglebone.txt
pip install -r requirements-rpi.txt
pip install -r requirements-win.txt