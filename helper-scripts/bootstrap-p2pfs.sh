sudo cp sysctl.conf /etc/sysctl.conf
sudo sysctl -p
sudo apt-get update
sudo apt-get install git subversion build-essential autoconf automake flex bison rpcbind pypy libsqlite3-dev python-dev pypy-dev unzip python-crypto nmap -y

wget https://pypi.python.org/packages/source/z/zope.interface/zope.interface-4.0.5.zip
unzip zope.interface-4.0.5.zip
cd zope.interface-4.0.5/
sudo pypy setup.py install
cd ..

wget http://pypi.python.org/packages/source/d/distribute/distribute-0.6.49.tar.gz
tar xvzf distribute-0.6.49.tar.gz
cd distribute-0.6.49/
sudo pypy setup.py install
cd ..

# fix for too many open files error when installing twisted
ulimit -n 2048

wget http://twistedmatrix.com/Releases/Twisted/13.2/Twisted-13.2.0.tar.bz2
tar xvjf Twisted-13.2.0.tar.bz2
cd Twisted-13.2.0
sudo pypy setup.py install
cd ..

git clone https://github.com/terencehonles/fusepy.git fusepy
cd fusepy
sudo pypy setup.py install
cd ..

svn checkout svn://svn.code.sf.net/p/entangled/code/ entangled-code
cd entangled-code/entangled
sudo pypy setup.py install
cd ../..

wget https://ftp.dlitz.net/pub/dlitz/crypto/pycrypto/pycrypto-2.6.1.tar.gz
tar xvzf pycrypto-2.6.1.tar.gz
cd pycrypto-2.6.1
sudo pypy setup.py install
cd ..

git clone https://darka@github.com/darka/p2pfs.git
sudo chown ubuntu:ubuntu -R p2pfs

mkdir tmp
cd tmp/
wget http://www.irssi.org/files/irssi-0.8.16-rc1.tar.gz
cd ..
