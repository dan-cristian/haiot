#! /bin/bash
cd ..
sudo pip install virtualenv
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
