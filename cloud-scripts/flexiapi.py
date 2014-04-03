from suds.client import Client
import datetime
import credentials

username = credentials.username
password = credentials.password

url = 'https://cp.sd1.flexiant.net:4442/?wsdl'
client = Client(url, username=username, password=password)

def getIP(name):
  server = findServerByName(name)
  return server.nics[0].ipAddresses[0].ipAddress

def createServer(name):
  server = client.factory.create('server')
  server.resourceName = name
  server.cpu = 1
  server.ram = 512

  nic = client.factory.create('nic')
  ip = client.factory.create('ip')
  ip.auto = True
  nic.ipAddresses = ip
  server.nics = nic

  return client.service.createServer(server, '74d92578-c0b6-3f2f-a074-a83465541a17')

def findServerByName(name):
  filterCondition = client.factory.create('filterCondition')
  filterCondition.condition = 'IS_EQUAL_TO'
  filterCondition.field = 'resourceName'
  filterCondition.value = name
  searchFilter = client.factory.create('searchFilter')
  searchFilter.filterConditions = filterCondition

  resourceType = client.factory.create('resourceType')

  result = client.service.listResources(searchFilter=searchFilter, resourceType=resourceType.SERVER)
  return result[0][0]

def changeServerStatus(name, status):
  server = findServerByName(name)
  serverStatus = client.factory.create('serverStatus')
  if status == 'RUNNING':
    status = serverStatus.RUNNING
  elif status == 'REBOOTING':
    status = serverStatus.REBOOTING
  elif status == 'STOPPED':
    status = serverStatus.STOPPED
  else:
    assert(False)
  client.service.changeServerStatus(str(server['resourceUUID']), status, False, client.factory.create('resourceMetadata'))

def main():
  print findServerByName('Node 1')

if __name__ == '__main__':
  main()
