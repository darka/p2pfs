from fabric.api import *
import os
import random

def fix_boot():
  local('./fix-server.sh {0}'.format(env.host))

def ls():
  run('ls')

def upload_keys():
  path = 'keys/'
  key_filenames = [ f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f)) and f.startswith('key')]
  for filename in key_filenames:
    full_path = os.path.join(path, filename)
    put(full_path, '~/p2pfs/src/keys/')

def fix_sudoers():
  n = random.randint(1, 100)
  put('sudoers', '~/.tmp-sudoers-{0}'.format(n), mode=0440)
  sudo('chown root:root ~/.tmp-sudoers-{0} && mv ~/.tmp-sudoers-{0} /etc/sudoers'.format(n))

def bootstrap():
  put('bootstrap-p2pfs.sh', '~/')
  put('sysctl.conf', '~/')
  sudo('sh bootstrap-p2pfs.sh')

def prepare_dirs():
  run('mkdir -p ~/p2pfs/work/res')

def upload_run_scripts():
  put('host.sh', '~/p2pfs/', mirror_local_mode=True)
  put('connect.sh', '~/p2pfs/', mirror_local_mode=True)
  #put('connect-all.sh', '~/p2pfs/')
  #put('connect-new.sh', '~/p2pfs/')
  #put('connect-and-mount.sh', '~/p2pfs/')

def connect():
  with cd('~/p2pfs/'):
    run('./connect.sh')

def host():
  with cd('~/p2pfs/'):
    run('./host.sh')
