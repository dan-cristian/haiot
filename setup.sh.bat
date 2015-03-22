#! /bin/bash

virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
python -c "import plotly; plotly.tools.set_credentials_file(username='dancri77', api_key='lw2w6fz9xk',
    stream_ids=['15ytl1hrhc', '24w1i6s6bs'])"