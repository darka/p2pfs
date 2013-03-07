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

uint16_t FS_PORT = 8080;

// you stole this from the web, replace with something that makes more sense
uint32_t hash(uint32_t key)
{
	key += ~(key << 15);
	key ^=	(key >> 10);
	key +=	(key << 3);
	key ^=	(key >> 6);
	key += ~(key << 11);
	key ^=	(key >> 16);
	return key;
}

enum Command 
{
	ASK_FOR_SUCCESSOR = 0,
	RECEIVE_SUCCESSOR = 1,
	I_AM_SUCCESSOR = 2,
	ASK_FOR_MY_HASH = 3,
	RECEIVE_MY_HASH = 4,
	LOOKUP_VALUE = 5,
	RECEIVE_VALUE = 6,
	STORE_VALUE = 7,
	RELOOKUP_VALUE = 8
};

int h1 = 0;
class MyApp : public Application 
{
public:
	MyApp (Ptr<Node> node)
	: inSocket(0)
	, predecessor(0)
	, successor(0)
	, myNode(node)
	, isOwnSuccessor(false)
	, hasHash(false)
	, myHash(h1)
	{
		h1++;
	}

	void StartApplication()
	{
		inSocket = Socket::CreateSocket(myNode, TcpSocketFactory::GetTypeId ());
		inSocket->Bind(InetSocketAddress(Ipv4Address::GetAny(), 8080));
		
		inSocket->Listen();
		inSocket->SetAcceptCallback(MakeNullCallback<bool, Ptr<Socket>, const Address &> (), MakeCallback(&MyApp::HandleAccept, this));
		std::cout << myHash << " <- started inSocket\n";
	}

	void HandleAccept(Ptr<Socket> s, const Address& from)
	{
		std::cout << myHash << " Someone connected from ";
		InetSocketAddress::ConvertFrom(from).GetIpv4().Print(std::cout);
		std::cout << ' ' << hash(InetSocketAddress::ConvertFrom(from).GetIpv4().Get());
		std::cout << '\n';
		
		uint32_t ip = InetSocketAddress::ConvertFrom(from).GetIpv4().Get();
		socketAddress[s] = ip;
		addressSocket[ip] = s;
		ipToAddress[ip] = from;
		s->SetRecvCallback(MakeCallback(&MyApp::HandleReceive, this));
	}

	void CreateRing()
	{
		isOwnSuccessor = true;
	}

	void Join(Address address)
	{
		GetHash(address);
		GetSuccessor(address);
	}

	void LookupKey(uint32_t key)
	{
		SendMessageAskForValue(GetSocket(successor), key);
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
			uint8_t buffer[17];
			packet->CopyData(buffer, sizeof(buffer));
			Command command = (Command)buffer[0];
			switch (command)
			{
			case I_AM_SUCCESSOR:
				successorHash = byteArrayToInt(&buffer[1]);
				std::cout << myHash << " successor " << successorHash << '\n';
				successor = socketAddress[s];
				break;
			case RECEIVE_VALUE:
				{
					uint32_t value = byteArrayToInt(&buffer[1]);
					std::cout << myHash << " received value: " << value << '\n';
				}
				break;
			case RELOOKUP_VALUE:
				{
					uint32_t ip = byteArrayToInt(&buffer[1]);
					uint32_t key = byteArrayToInt(&buffer[5]);
					if (myHash < key && key <= successorHash)
					{
						SendMessageReceiveValue(GetSocket(ip), key);
					}
					else
					{
						SendMessageReaskForValue(GetSocket(successor), ip, key);
					}
				}
				break;
			case LOOKUP_VALUE:
				{
					uint32_t key = byteArrayToInt(&buffer[1]);
					if (myHash < key && key <= successorHash)
					{
						SendMessageReceiveValue(s, key);
					}
					else
					{
						SendMessageReaskForValue(GetSocket(successor), socketAddress[s], key);
					}
				}
				break;
			case STORE_VALUE:
				{
					uint32_t key = byteArrayToInt(&buffer[1]);
					uint32_t value = byteArrayToInt(&buffer[5]);
					if (myHash < key && key <= successorHash)
					{
						lookupData[key] = value;
						std::cout << "stored value " << value << " (key " << key << ") at " << myHash << '\n';
					}
					else
					{
						SendMessageStoreValue(GetSocket(successor), key, value);
					}
				}
				break;
			case ASK_FOR_SUCCESSOR:
				{
					uint32_t askedHash = byteArrayToInt(&buffer[1]);
					if (isOwnSuccessor || (myHash < askedHash && askedHash <= successorHash))
					{
						// this node has the same successor as the node which asked
						SendMessageReceiveSuccessor(s, successorHash, successor);
					}	
					else if (askedHash < myHash)
					{
						SendMessageReceiveMeAsSuccessor(s);
					}
					else
					{
						// continue search via the ring
						onGoingSearches[askedHash] = socketAddress[s];
						GetSuccessorForHash(ipToAddress[successor], askedHash);
					}
				}
				break;
			case RECEIVE_SUCCESSOR:
				{
					std::cout << myHash << " RECEIVED SUCCESSOR!!\n";
					// 4 bytes - id
					// 4 bytes - ip of successor of id
					//if (questionHash != myHash)
					//{
					//	uint32_t sendBackIp = onGoingSearches[questionHash];
					//	packet = Create< Packet >(buffer, sizeof(buffer));
					//	addressSocket[sendBackIp]->Send(packet);
					//}
					//else
					//{
					successorHash = byteArrayToInt(&buffer[1]);
					successor = byteArrayToInt(&buffer[5]);
					std::cout << myHash << " successor is " << successorHash << '\n';
					//}
					//uint32_t successorIp = byteArrayToInt(&buffer[5]);
					//if (id != myHash)
					//{
						
					//}
				}
				break;
			case ASK_FOR_MY_HASH:
				SendMessageReceiveHash(s);
				if (!myHash) // Ask back for my own hash
					GetHash(ipToAddress[socketAddress[s]]);
				break;
			case RECEIVE_MY_HASH:
				{
					uint32_t newHash;
					newHash = byteArrayToInt(&buffer[1]);
					std::cout << myHash << " new hash is: " << newHash << '\n';
					hasHash = true;
					myHash = newHash;
				}
				break;
			default:
				break;
			}
		}		
	}

	~MyApp()
	{
		if (inSocket) 
			inSocket->Close();
		for (std::map< Ptr<Socket>, uint32_t >::iterator i = socketAddress.begin(); i != socketAddress.end(); ++i)
		{
			i->first->Close();
		}
	}

	Ptr<Socket> GetSocket(uint32_t ip)
	{
		std::map< uint32_t, Ptr<Socket> >::iterator result = addressSocket.find(ip);
		if (result != addressSocket.end())
		{
			//std::cout << "found socket\n";
			return result->second;
		}
		else
		{
			Ptr<Socket> outSocket = Socket::CreateSocket(myNode, TcpSocketFactory::GetTypeId());
			outSocket->Bind();

			Ipv4Address addressIpv4(ip);
			InetSocketAddress address(addressIpv4, FS_PORT);
			outSocket->Connect(address);

			outSocket->SetRecvCallback(MakeCallback(&MyApp::HandleReceive, this));
			socketAddress[outSocket] = ip;
			addressSocket[ip] = outSocket;
			ipToAddress[ip] = address;
			return outSocket;
		}
	}

	Ptr<Socket> GetSocket(Address address)
	{
		uint32_t ip = InetSocketAddress::ConvertFrom(address).GetIpv4().Get();
		std::map< uint32_t, Ptr<Socket> >::iterator result = addressSocket.find(ip);
		if (result != addressSocket.end())
		{
			//std::cout << "found socket\n";
			return result->second;
		}
		else
		{
			Ptr<Socket> outSocket = Socket::CreateSocket(myNode, TcpSocketFactory::GetTypeId());
			outSocket->Bind();
			outSocket->Connect(address);
			outSocket->SetRecvCallback(MakeCallback(&MyApp::HandleReceive, this));
			socketAddress[outSocket] = ip;
			addressSocket[ip] = outSocket;
			ipToAddress[ip] = address;
			return outSocket;
		}
	}

	void GetHash(Address address)
	{
		Ptr<Socket> outSocket = GetSocket(address);
		SendMessageAskForMyHash(outSocket);
	}

	void GetSuccessor(Address address)
	{
		GetSuccessorForHash(address, myHash);
	}

	void GetSuccessorForHash(Address address, uint32_t hash)
	{
		Ptr<Socket> outSocket = GetSocket(address);
		SendMessageAskForSuccessor(outSocket, hash);
	}

	//void LookupValue(Address address, uint32_t key)
	//{
	//	Ptr<Socket> outSocket = GetSocket(address);
	//	SendMessageAskForSuccessor(outSocket, hash);
	//}

	void SendMessageReaskForValue(Ptr<Socket> socket, uint32_t ip, uint32_t hash)
	{
		uint8_t buffer[9];
		buffer[0] = (uint8_t)RELOOKUP_VALUE;
		intToByteArray(ip, &buffer[1]);
		intToByteArray(hash, &buffer[5]);
		Ptr<Packet> packet;
		packet = Create<Packet>(buffer, sizeof(buffer));
		socket->Send(packet);
		std::cout << myHash << " REASKED FOR VALUE\n";
	}

	void SendMessageAskForValue(Ptr<Socket> socket, uint32_t hash)
	{
		uint8_t buffer[9];
		buffer[0] = (uint8_t)LOOKUP_VALUE;
		intToByteArray(hash, &buffer[1]);
		Ptr<Packet> packet;
		packet = Create<Packet>(buffer, sizeof(buffer));
		socket->Send(packet);
		std::cout << myHash << " ASKED FOR VALUE\n";
	}

	void SendMessageAskForSuccessor(Ptr<Socket> socket, uint32_t hash)
	{
		uint8_t buffer[5];
		buffer[0] = (uint8_t)ASK_FOR_SUCCESSOR;
		intToByteArray(myHash, &buffer[1]);
		Ptr<Packet> packet;
		packet = Create<Packet>(buffer, sizeof(buffer));
		socket->Send(packet);
		std::cout << myHash << " ASKED FOR SUCCESSOR\n";
	}

	void StoreValue(uint32_t value)
	{
		SendMessageStoreValue(GetSocket(successor), 3278655985, value);
	}

	void SendMessageStoreValue(Ptr<Socket> socket, uint32_t value)
	{
		SendMessageStoreValue(socket, hash(value), value);
	}

	void SendMessageStoreValue(Ptr<Socket> socket, uint32_t key, uint32_t value)
	{
		uint8_t buffer[9];
		buffer[0] = (uint8_t)STORE_VALUE;
		intToByteArray(key, &buffer[1]);
		intToByteArray(value, &buffer[5]);
		Ptr<Packet> packet;
		packet = Create<Packet>(buffer, sizeof(buffer));
		socket->Send(packet);
		std::cout << myHash << " LOOKING WHERE TO STORE VALUE " << value << " with key(" << key << ")\n";
	}

	void SendMessageReceiveValue(Ptr<Socket> socket, uint32_t key)
	{
		uint8_t buffer[5];
		buffer[0] = (uint8_t)RECEIVE_VALUE;
		intToByteArray(lookupData[key], &buffer[1]);
		Ptr<Packet> packet = Create <Packet> (buffer, sizeof(buffer));
		socket->Send(packet);
		std::cout << myHash << " RECEIVE VALUE -> SENT\n";
	}

	void SendMessageAskForMyHash(Ptr<Socket> socket)
	{
		uint8_t buffer[1];
		buffer[0] = (uint8_t)ASK_FOR_MY_HASH;
		Ptr<Packet> packet;
		packet = Create< Packet >(buffer, sizeof(buffer));
		socket->Send(packet);
		std::cout << myHash << " ASKED FOR HASH\n";
	}	
	
	void SendMessageReceiveHash(Ptr<Socket> socket)
	{
		uint8_t buffer[5];
		buffer[0] = (uint8_t)RECEIVE_MY_HASH;
		uint32_t h = hash(socketAddress[socket]);
		intToByteArray(h, &buffer[1]);
		Ptr<Packet> packet = Create <Packet> (buffer, sizeof(buffer));
		socket->Send(packet);
		std::cout << myHash << " RECEIVE HASH -> SENT\n";
	}

	void SendMessageReceiveMeAsSuccessor(Ptr<Socket> socket)
	{
		uint8_t buffer[5];
		buffer[0] = (uint8_t)I_AM_SUCCESSOR;
		intToByteArray(myHash, &buffer[1]);
		Ptr<Packet> packet = Create <Packet> (buffer, sizeof(buffer));
		socket->Send(packet);
		std::cout << myHash << " RECEIVE SUCCESSOR -> SENT (I AM SUCCESSOR)\n";
	}

	void SendMessageReceiveSuccessor(Ptr<Socket> socket, uint32_t successorHash, uint32_t successor)
	{
		if (isOwnSuccessor)
		{
			uint8_t buffer[5];
			buffer[0] = (uint8_t)I_AM_SUCCESSOR;
			intToByteArray(myHash, &buffer[1]);
			Ptr<Packet> packet = Create <Packet> (buffer, sizeof(buffer));
			socket->Send(packet);
			std::cout << myHash << " RECEIVE SUCCESSOR -> SENT (I AM SUCCESSOR)\n";
		}
		else
		{
			uint8_t buffer[13];
			buffer[0] = (uint8_t)RECEIVE_SUCCESSOR;
			intToByteArray(successorHash, &buffer[1]);
			intToByteArray(successor, &buffer[5]);
			Ptr<Packet> packet = Create <Packet> (buffer, sizeof(buffer));
			socket->Send(packet);
			std::cout << myHash << " RECEIVE SUCCESSOR -> SENT\n";
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

	Ptr<Socket> inSocket;
	uint32_t predecessor;
	uint32_t predecessorHash;
	uint32_t successor;
	uint32_t successorHash;
	Ptr<Node> myNode;
	
	std::map< Ptr<Socket>, uint32_t > socketAddress;
	std::map< uint32_t, Ptr<Socket> > addressSocket;

	std::map< uint32_t, Address > ipToAddress;

	std::map<size_t, std::string> items;
	bool isOwnSuccessor;
	bool hasHash;
	uint32_t myHash;
	std::map< uint32_t, uint32_t > onGoingSearches; // hash -> address (see Joining Logic)
	std::map< uint32_t, uint32_t > lookupData; // key -> value data store
};


int 
main (int argc, char *argv[])
{
	CommandLine cmd;
	cmd.Parse (argc, argv);
	NodeContainer nodes;
	nodes.Create (4);

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

	Address creatorAddress (InetSocketAddress (interfaces.GetAddress (2), FS_PORT));
	Address appAddress (InetSocketAddress (interfaces.GetAddress (1), FS_PORT));
	Address appTwoAddress (InetSocketAddress (interfaces.GetAddress (0), FS_PORT));
	Address appThreeAddress (InetSocketAddress (interfaces.GetAddress (3), FS_PORT));

	Ptr<MyApp> creator = CreateObject<MyApp> (nodes.Get(2));
	nodes.Get(2)->AddApplication(creator);

	Ptr<MyApp> app = CreateObject<MyApp> (nodes.Get (1));
	nodes.Get (1)->AddApplication(app);
	Ptr<MyApp> app3 = CreateObject<MyApp> (nodes.Get (3));
	nodes.Get (3)->AddApplication(app3);
	Ptr<MyApp> app2 = CreateObject<MyApp> (nodes.Get (0));
	nodes.Get (0)->AddApplication(app2);

	Simulator::Schedule( Seconds(3), &MyApp::CreateRing, creator);
	Simulator::Schedule( Seconds(9), &MyApp::GetHash, app2, creatorAddress);
	Simulator::Schedule( Seconds(12), &MyApp::GetSuccessor, app2, creatorAddress);

	Simulator::Schedule( Seconds(15), &MyApp::GetHash, app, appTwoAddress );
	Simulator::Schedule( Seconds(18), &MyApp::GetSuccessor, app, appTwoAddress );
	Simulator::Schedule( Seconds(15), &MyApp::GetHash, app3, appAddress );
	Simulator::Schedule( Seconds(18), &MyApp::GetSuccessor, app3, appAddress );
	Simulator::Schedule( Seconds(32), &MyApp::StoreValue, app, 12 );
	Simulator::Schedule( Seconds(48), &MyApp::LookupKey, app3, 3278655985 );
	//Simulator::Schedule( Seconds(100), &MyApp::GetSuccessor, app, appTwoAddress );
	Simulator::Stop ();
	Simulator::Run ();
	Simulator::Destroy ();

	return 0;
}
