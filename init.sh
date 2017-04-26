#/usr/sbin/env bash

source ~/.bash_profile

wget https://bootstrap.pypa.io/get-pip.py
python get-pip.py
pip install ping
pip install tornado
pip install futures
pip install supervisor
mkdir logs
supervisord -c supervisord.conf



