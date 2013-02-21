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

/*size_t hash(uint32_t n)
{
  std::tr1::hash<std::string> hash_fn;
  return hash_fn(n);
}*/

enum Command {
	FIND_SUCCESSOR = 0
};

class MyApp : public Application 
{
public:
  MyApp (Ptr<Node> node)
  : in_socket(0)
  , predecessor(0)
  , successor(0)
  , m_node(node)
  {
  	
  }

  void StartApplication()
  {
    in_socket = Socket::CreateSocket(m_node, TcpSocketFactory::GetTypeId ());
	in_socket->Bind(InetSocketAddress(Ipv4Address::GetAny(), 8080));
	
	in_socket->Listen();
	in_socket->SetAcceptCallback(MakeNullCallback<bool, Ptr<Socket>, const Address &> (), 
	                             MakeCallback(&MyApp::HandleAccept, this));
  }

  void HandleAccept(Ptr<Socket> s, const Address& from)
  {
  	std::cout << "Someone connected from ";
	InetSocketAddress::ConvertFrom(from).GetIpv4().Print(std::cout);
	//std::cout << ' ' << hash(InetSocketAddress::ConvertFrom(from).GetIpv4().Get());
	std::cout << '\n';

	socket_address[s] = from;
    s->SetRecvCallback(MakeCallback(&MyApp::HandleReceive, this));
  }

  void HandleReceive(Ptr<Socket> s)
  {
	Ptr<Packet> packet = s->Recv();
	if (packet == 0)
	{
	  std::cout << "0 packet from ";
	  InetSocketAddress::ConvertFrom(socket_address[s]).GetIpv4().Print(std::cout);
	  std::cout << '\n';
	}
	else
	{
  	  uint8_t buffer[5];
  	  packet->CopyData(buffer, sizeof(buffer));
	  std::cout << ( byteArrayToInt(&buffer[1]) ) << " from ";
	  InetSocketAddress::ConvertFrom(socket_address[s]).GetIpv4().Print(std::cout);
	  std::cout << '\n';
	  SendCommand(s, FIND_SUCCESSOR);
	}    
  }

  ~MyApp()
  {
	if (in_socket) 
	  in_socket->Close();
  }

  void GetSuccessor(Address address)
  {
	//bool found = false;
    Ptr<Socket> out_socket = Socket::CreateSocket(m_node, TcpSocketFactory::GetTypeId ());
	out_socket->Bind();
	out_socket->Connect(address);

	SendCommand(out_socket, FIND_SUCCESSOR);
	socket_address[out_socket] = address;
    out_socket->SetRecvCallback(MakeCallback(&MyApp::HandleReceive, this));

	//Ptr<Packet> packet = out_socket->Recv();
	//uint8_t buffer[5];
	//packet->CopyData(buffer, sizeof(buffer));
	//std::cout << byteArrayToInt(&buffer[1]) << '\n';
	// handle successor!!

	out_socket->Close();
  }

  void SendCommand(Ptr<Socket> socket, Command command)
  {
	uint8_t buffer[5];
	buffer[0] = (uint8_t)command;
	intToByteArray(21341, &buffer[1]);
    Ptr<Packet> packet = Create<Packet>(buffer, sizeof(buffer));
    socket->Send(packet);
	std::cout << "SENT!\n";
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
  Ptr<Node> m_node;

  std::map< Ptr<Socket>, Address > socket_address;

  std::map<size_t, std::string> items;
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

  Ptr<MyApp> receiverApplication = CreateObject<MyApp> (nodes.Get(2));
  nodes.Get(2)->AddApplication(receiverApplication);

  Ptr<MyApp> app = CreateObject<MyApp> (nodes.Get (1));
  nodes.Get (1)->AddApplication (app);
  Ptr<MyApp> app2 = CreateObject<MyApp> (nodes.Get (0));
  nodes.Get (0)->AddApplication (app2);

  Simulator::Schedule( Seconds(3), &MyApp::GetSuccessor, app, sinkAddress);
  Simulator::Schedule( Seconds(6), &MyApp::GetSuccessor, app2, sinkAddress);
  Simulator::Stop ();
  Simulator::Run ();
  Simulator::Destroy ();

  return 0;
}
