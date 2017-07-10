depdencies:
	# first time install of dependencies
	apt-get update
	# Required basics
	apt-get install -y vim git python supervisor python-gps python-pip redis-server
	# Requirements for RTIMUlib2
	apt-get install -y i2c-tools cmake python-dev octave
	# Pip modules
	pip install redis

rtimu:
	git clone https://github.com/richards-tech/RTIMULib2.git /opt/rtimu
	cd /opt/rtimu/Linux
	mkdir build
	cd build
	cmake ..
	make -j4
	make install
	ldconfig

setup: depdencies rtimu
	mkdir /var/log/glider
	cp supervisord.conf /etc/supervisor/conf.d/glider.conf
