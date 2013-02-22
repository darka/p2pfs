#include <fstream>
#include <string>
#include <functional>
#include <map>
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/csma-star-helper.h"

using namespace ns3;

uint32_t hash(uint32_t n)
{
  std::hash<uint32_t> hash_fn;
  return (uint32_t)hash_fn(n);
}

enum Command {
	ASK_FOR_SUCCESSOR = 0,
	RECEIVE_SUCCESSOR = 1,
	I_AM_SUCCESSOR = 2,
	ASK_FOR_MY_HASH = 3,
	RECEIVE_MY_HASH = 4
};

int h1 = 0;
class MyApp : public Application 
{
public:
  MyApp (Ptr<Node> node)
  : in_socket(0)
  , predecessor(0)
  , successor(0)
  , m_node(node)
  , is_own_successor(false)
  , my_hash(h1)
  {
  	h1++;
  }

  void StartApplication()
  {
    in_socket = Socket::CreateSocket(m_node, TcpSocketFactory::GetTypeId ());
	in_socket->Bind(InetSocketAddress(Ipv4Address::GetAny(), 8080));
	
	in_socket->Listen();
	in_socket->SetAcceptCallback(MakeNullCallback<bool, Ptr<Socket>, const Address &> (), 
	                             MakeCallback(&MyApp::HandleAccept, this));
	std::cout << my_hash << " <- started in_socket\n";
  }

  void HandleAccept(Ptr<Socket> s, const Address& from)
  {
  	std::cout << my_hash << " Someone connected from ";
	InetSocketAddress::ConvertFrom(from).GetIpv4().Print(std::cout);
	std::cout << ' ' << hash(InetSocketAddress::ConvertFrom(from).GetIpv4().Get());
	std::cout << '\n';
    
	uint32_t ip = InetSocketAddress::ConvertFrom(from).GetIpv4().Get();
	socket_address[s] = ip;
	address_socket[ip] = s;
	ip_to_address[ip] = from;
    s->SetRecvCallback(MakeCallback(&MyApp::HandleReceive, this));
  }

  void CreateRing()
  {
  	is_own_successor = true;
  }

  void HandleReceive(Ptr<Socket> s)
  {
	Ptr<Packet> packet = s->Recv();
	if (packet == 0)
	{
	  std::cout << "0 packet received\n";
	}
	else
	{
  	  uint8_t buffer[5];
  	  packet->CopyData(buffer, sizeof(buffer));
	  Command command = (Command)buffer[0];
      uint32_t new_hash;
	  switch (command)
	  {
	  	case ASK_FOR_SUCCESSOR:
		  SendMessageReceiveSuccessor(s);
		  break;
		case ASK_FOR_MY_HASH:
		  SendMessageReceiveHash(s);
		  if (!my_hash) // Ask back for my own hash
		  	GetHash(ip_to_address[socket_address[s]]);
		  break;
		case RECEIVE_MY_HASH:
		  new_hash = byteArrayToInt(&buffer[1]);
		  std::cout << my_hash << " new hash is: " << new_hash << '\n';
		  my_hash = new_hash;
		  break;
		default:
		  break;
	  }
	}    
  }

  ~MyApp()
  {
	if (in_socket) 
	  in_socket->Close();
	for (std::map< Ptr<Socket>, uint32_t >::iterator i = socket_address.begin(); i != socket_address.end(); ++i)
	{
	  i->first->Close();
	}
  }

  Ptr<Socket> GetSocket(Address address)
  {
	uint32_t ip = InetSocketAddress::ConvertFrom(address).GetIpv4().Get();
    std::map< uint32_t, Ptr<Socket> >::iterator result = address_socket.find(ip);
	if (result != address_socket.end())
	{
		std::cout << "found socket\n";
		return result->second;
	}
	else
	{
	  Ptr<Socket> out_socket = Socket::CreateSocket(m_node, TcpSocketFactory::GetTypeId());
	  out_socket->Bind();
	  out_socket->Connect(address);
      out_socket->SetRecvCallback(MakeCallback(&MyApp::HandleReceive, this));
	  socket_address[out_socket] = ip;
	  address_socket[ip] = out_socket;
	  ip_to_address[ip] = address;
	  return out_socket;
	}
  }

  void GetHash(Address address)
  {
    Ptr<Socket> out_socket = GetSocket(address);
	SendMessageAskForMyHash(out_socket);
  }


  void GetSuccessor(Address address)
  {
    Ptr<Socket> out_socket = GetSocket(address);
	// ask address for successor
	SendMessageAskForSuccessor(out_socket);
  }

  void SendMessageAskForSuccessor(Ptr<Socket> socket)
  {
	uint8_t buffer[1];
	buffer[0] = (uint8_t)ASK_FOR_SUCCESSOR;
	Ptr<Packet> packet;
	packet = Create< Packet >(buffer, sizeof(buffer));
    socket->Send(packet);
	std::cout << my_hash << " ASKED FOR SUCCESSOR\n";
  }

  void SendMessageAskForMyHash(Ptr<Socket> socket)
  {
	uint8_t buffer[1];
	buffer[0] = (uint8_t)ASK_FOR_MY_HASH;
	Ptr<Packet> packet;
	packet = Create< Packet >(buffer, sizeof(buffer));
    socket->Send(packet);
	std::cout << my_hash << " ASKED FOR HASH\n";
  }  
  
  void SendMessageReceiveHash(Ptr<Socket> socket)
  {
	  uint8_t buffer[5];
	  buffer[0] = (uint8_t)RECEIVE_MY_HASH;
	  uint32_t h = hash(socket_address[socket]);
	  intToByteArray(h, &buffer[1]);
      Ptr<Packet> packet = Create <Packet> (buffer, sizeof(buffer));
      socket->Send(packet);
	  std::cout << my_hash << " RECEIVE HASH -> SENT\n";
  }

  void SendMessageReceiveSuccessor(Ptr<Socket> socket)
  {
	if (is_own_successor)
	{
	  uint8_t buffer[1];
	  buffer[0] = (uint8_t)I_AM_SUCCESSOR;
      Ptr<Packet> packet = Create<Packet>(buffer, sizeof(buffer));
      socket->Send(packet);
	  std::cout << "I AM SUCCESSOR -> SENT\n";
	}
	else
	{
	  uint8_t buffer[5];
	  buffer[0] = (uint8_t)RECEIVE_SUCCESSOR;
	  uint32_t ip = socket_address[socket];
	  intToByteArray(ip, &buffer[1]);
      Ptr<Packet> packet = Create <Packet> (buffer, sizeof(buffer));
      socket->Send(packet);
	  std::cout << "RECEIVE SUCCESSOR -> SENT\n";
	}
  }

  void intToByteArray(uint32_t n, uint8_t* arr)
  {
  	arr[0] = n >> 24 & 0xFF;
	arr[1] = n >> 16 & 0xFF;
	arr[2] = n >> 8 & 0xFF;
	arr[3] = n & 0xFF;
  }

  uint32_t byteArrayToInt(uint8_t* arr)
  {
	uint32_t ret = 0;
	ret |= (((uint32_t)arr[0]) << 24);
	ret |= (((uint32_t)arr[1]) << 16);
	ret |= (((uint32_t)arr[2]) << 8);
	ret |= (uint32_t)arr[3];
	return ret;
  }


  Ptr<Socket> in_socket;
  Ptr<Socket> predecessor;
  Ptr<Socket> successor;
  Address predecessorAddr;
  Address successorAddr;
  Ptr<Node> m_node;
  

  std::map< Ptr<Socket>, uint32_t > socket_address;
  std::map< uint32_t, Ptr<Socket> > address_socket;

  std::map< uint32_t, Address > ip_to_address;

  std::map<size_t, std::string> items;
  bool is_own_successor;
  uint32_t my_hash;
};


//static void
//CountRx (Ptr<const Packet> packet, const Address & socketAddress)
//  {
//    std::cout<<"RECEIVED!\n";
//  }

int 
main (int argc, char *argv[])
{
CommandLine cmd;
   cmd.Parse (argc, argv);
  NodeContainer nodes;
  nodes.Create (3);

    CsmaHelper eth;
    eth.SetChannelAttribute("DataRate", DataRateValue(DataRate(5000000)));

    eth.SetChannelAttribute("Delay", TimeValue(MilliSeconds(2)));
    eth.SetDeviceAttribute("Mtu", UintegerValue(1400));

    NetDeviceContainer devices = eth.Install(nodes);


  //PointToPointHelper pointToPoint;
  //NetDeviceContainer devices;
  //devices = pointToPoint.Install (nodes);

  InternetStackHelper stack;
  stack.Install (nodes);
  Ipv4AddressHelper address;
  address.SetBase ("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer interfaces = address.Assign (devices);

  uint16_t sinkPort = 8080;
  Address sinkAddress (InetSocketAddress (interfaces.GetAddress (2), sinkPort));

  Ptr<MyApp> creator = CreateObject<MyApp> (nodes.Get(2));
  nodes.Get(2)->AddApplication(creator);

  Ptr<MyApp> app = CreateObject<MyApp> (nodes.Get (1));
  nodes.Get (1)->AddApplication(app);
  Ptr<MyApp> app2 = CreateObject<MyApp> (nodes.Get (0));
  nodes.Get (0)->AddApplication(app2);

  Simulator::Schedule( Seconds(9), &MyApp::GetHash, app, sinkAddress);
  Simulator::Schedule( Seconds(12), &MyApp::GetHash, app2, sinkAddress);
  Simulator::Stop ();
  Simulator::Run ();
  Simulator::Destroy ();

  return 0;
}
