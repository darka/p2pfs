#include <fstream>
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/csma-star-helper.h"

using namespace ns3;

class MyApp : public Application 
{
public:
  MyApp (Ptr<Node> node)
  : m_node(node)
  {
  	
  }

  void StartApplication()
  {
    out_socket = Socket::CreateSocket(m_node, TcpSocketFactory::GetTypeId ());
    in_socket = Socket::CreateSocket(m_node, TcpSocketFactory::GetTypeId ());
	in_socket->Bind(InetSocketAddress(Ipv4Address::GetAny(), 8080));
	in_socket->Listen();
	in_socket->SetAcceptCallback(MakeNullCallback<bool, Ptr<Socket>, const Address &> (), 
	                            MakeCallback(&MyApp::HandleAccept, this));
  }

  void HandleAccept(Ptr<Socket> s, const Address& from)
  {
  	std::cout << "Someone connected.\n";
  }

  ~MyApp()
  {
    out_socket->Close();
	in_socket->Close();
  }

  void ConnectTo(Address address)
  {
    out_socket->Bind();
    out_socket->Connect(address);
  }

  void SendPacket()
  {
    Ptr<Packet> packet = Create<Packet>(100);
    out_socket->Send(packet);
	std::cout << "SENT!\n";
  }

public:
  Ptr<Socket> in_socket;
  Ptr<Socket> out_socket;
  Ptr<Node> m_node;
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

  Simulator::Schedule( Seconds(3), &MyApp::ConnectTo, app, sinkAddress);
  Simulator::Schedule( Seconds(6), &MyApp::ConnectTo, app2, sinkAddress);
  Simulator::Stop ();
  Simulator::Run ();
  Simulator::Destroy ();

  return 0;
}
