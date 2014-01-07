sudo cp sysctl.conf /etc/sysctl.conf
sudo sysctl -p
sudo apt-get update
sudo apt-get install subversion build-essential autoconf automake flex bison rpcbind
svn checkout svn://svn.code.sf.net/p/unfs3/code/trunk unfs3-code
cd unfs3-code
autoheader
autoconf
./configure
make
sudo make install
mkdir -p ~/tmp/test
