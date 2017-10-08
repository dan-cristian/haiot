#!/usr/bin/env bash

opkg update
opkg install shadow
useradd haiot
mkdir -p /home/haiot
chown haiot:haiot /home/haiot
ssh haiot@$HOST "tee -a ~/.ssh/authorized_keys" < ~/.ssh/id_rsa.pub
