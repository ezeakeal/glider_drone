# Conditionals
RTIMU_EXIST := $(which RTIMULibCal > /dev/null)

dependencies:
	# first time install of dependencies
	apt-get update
	# Required basics
	apt-get install -y vim git python supervisor python-gps python-pip redis-server
	# Requirements for RTIMUlib2
	apt-get install -y i2c-tools cmake python-dev octave uuid-dev libicu-dev qt4-dev-tools 
	# Requirements for Glider (camera/servo/music control)
	apt-get install -y python-PIL python-smbus mpg321
	# Pip modules
	pip install redis nose adafruit-pca9685

rtimu:
	rm -rf /opt/rtimu
	git clone https://github.com/Nick-Currawong/RTIMULib2.git /opt/rtimu
	mkdir /opt/rtimu/Linux/build
	cd /opt/rtimu/Linux/build && cmake .. && make -j4 && make install && ldconfig
	cd /opt/rtimu/Linux/python && python setup.py build && python setup.py install

supervisor:
	cp supervisord.conf /etc/supervisor/conf.d/glider.conf
	supervisorctl -c /etc/supervisor/supervisord.conf reread; supervisorctl -c /etc/supervisor/supervisord.conf update

setup: dependencies rtimu gps supervisor
	mkdir /var/log/glider

clean:
	rm -rf /opt/rtimu

link:
	ln -s $PWD/glider /opt/glider

copy:
	cp -r $PWD/glider /opt/glider

