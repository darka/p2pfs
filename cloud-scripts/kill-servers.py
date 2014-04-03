import flexiapi
import sys
import suds

numbers = range(1, 32)
for n in numbers:
  name = 'Node {}'.format(n)
  print name
  try:
    flexiapi.changeServerStatus(name, 'STOPPED')
  except TypeError:
    print 'No such server?'
    continue
  except suds.WebFault:
    print 'ERROR!'
    continue
