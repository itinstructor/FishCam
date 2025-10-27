# run on the Pi as root or with sudo
sudo mkdir -p /etc/systemd/journald.conf.d
sudo cp /home/pi/fishcam/etc/systemd/journald.conf.d/99-limit.conf /etc/systemd/journald.conf.d/99-limit.conf
sudo systemctl restart systemd-journald