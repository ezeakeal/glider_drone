# Conditionals
RTIMU_EXIST := $(which RTIMULibCal > /dev/null)

depdencies:
	# first time install of dependencies
	apt-get update
	# Required basics
	apt-get install -y vim git python supervisor python-gps python-pip redis-server
	# Requirements for RTIMUlib2
	apt-get install -y i2c-tools cmake python-dev octave uuid-dev libicu-dev qt4-dev-tools 
	# Pip modules
	pip install redis

rtimu:
	ifndef $(RTIMU_EXIST)
		rm -rf /opt/rtimu
		git clone https://github.com/richards-tech/RTIMULib2.git /opt/rtimu
		mkdir /opt/rtimu/Linux/build
		cd /opt/rtimu/Linux/build && cmake .. && make -j4 && make install && ldconfig
		cd /opt/rtimu/Linux/python && python setup.py build && python setup.py install
	endif

setup: depdencies rtimu
	mkdir /var/log/glider
	cp supervisord.conf /etc/supervisor/conf.d/glider.conf
	supervisorctl -c /etc/supervisor/supervisord.conf reread; supervisorctl -c /etc/supervisor/supervisord.conf update

link:
	ln -s $PWD/glider /opt/glider

copy:
	cp -r $PWD/glider /opt/glider

