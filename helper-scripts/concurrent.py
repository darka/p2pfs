import os 
import timeit
import subprocess
import time
import sys

location_dir = 'testfs'
SLEEP_TIME = 3
output_filename = 'output.txt'

def main():
  FNULL = open(os.devnull, 'w')

  output_file = open(output_filename, 'w')

  os.chdir(os.path.join('.', location_dir))

  if len(sys.argv) < 2:
    print 'USAGE: concurrent.py FILENAME'
    sys.exit(1)

  filename = sys.argv[1]
  while True:
    cmd = lambda: subprocess.call('/bin/cp /home/ubuntu/tmp/1MB ./{}'.format(filename), stdout=FNULL, stderr=subprocess.STDOUT, shell=True)
    t = timeit.Timer(cmd)
    miliseconds = t.timeit(number=1)
    miliseconds = int(round(miliseconds*1000))
    print miliseconds
    output_file.write('{0}\n'.format(miliseconds))
    output_file.flush()
    time.sleep(SLEEP_TIME)

  output_file.close()

if __name__ == '__main__':
  main()
