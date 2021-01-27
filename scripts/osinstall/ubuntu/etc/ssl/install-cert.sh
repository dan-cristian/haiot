# https://www.openhab.org/docs/installation/security.html#nginx-setup-config

sudo apt-get install openssl
sudo mkdir -p /etc/ssl/certs
#cd /etc/ssl
#sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout dancristian.key -out dancristian.crt

sudo certbot certonly --webroot -w /var/www/letsencrypt -d www.dancristian.ro
