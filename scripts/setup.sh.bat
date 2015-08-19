#! /bin/bash
sudo pip install virtualenv
virtualenv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
chmod +x startserver*.sh
chmod +x scripts/stopserver.sh

