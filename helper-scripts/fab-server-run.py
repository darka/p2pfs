from fabric.api import *
import random

def fix_boot():
  local('./fix-server.sh {0}'.format(env.host))

def fix_sudoers():
  n = random.randint(1, 100)
  put('sudoers', '~/.tmp-sudoers-{0}'.format(n), mode=0440)
  sudo('chown root:root ~/.tmp-sudoers-{0} && mv ~/.tmp-sudoers-{0} /etc/sudoers'.format(n))

def bootstrap():
  put('bootstrap-p2pfs.sh', '~/')
  put('sysctl.conf', '~/')
  sudo('sh bootstrap-p2pfs.sh')
