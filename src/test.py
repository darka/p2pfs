# /*
#  * This program is free software; you can redistribute it and/or modify
#  * it under the terms of the GNU General Public License version 2 as
#  * published by the Free Software Foundation;
#  *
#  * This program is distributed in the hope that it will be useful,
#  * but WITHOUT ANY WARRANTY; without even the implied warranty of
#  * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  * GNU General Public License for more details.
#  *
#  * You should have received a copy of the GNU General Public License
#  * along with this program; if not, write to the Free Software
#  * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#  */

import ns.applications
import ns.core
import ns.internet
import ns.network
import ns.point_to_point
import ns.csma
#import visualizer

class ChordApp(ns.network.Application): 
	def StartApplication(self):
		print("chord node started")
		self.tid = ns.core.TypeId.LookupByName('ns3::TcpSocketFactory')
		self.socket = ns.network.Socket.CreateSocket(self.GetNode(), self.tid)
		self.socket.Bind(ns.network.InetSocketAddress(ns.network.Ipv4Address.GetAny(), 9))
		self.socket.Listen()
	def StopApplication(self):
		print("chord node stopped")
#	def __init__(self, addr, socket):
#		self.addr = addr
#		self.socket = socket

#	def send_hello(self, peer):
#		self.packet = ns.network.Packet()
#		self.socket.Send(packet)

node_count = 2

#ns.core.LogComponentEnable("UdpEchoClientApplication", ns.core.LOG_LEVEL_INFO)
#ns.core.LogComponentEnable("UdpEchoServerApplication", ns.core.LOG_LEVEL_INFO)

nodes = ns.network.NodeContainer()
nodes.Create(node_count)

internet = ns.internet.InternetStackHelper()
internet.Install(nodes)

eth = ns.csma.CsmaHelper()
eth.SetChannelAttribute("DataRate", ns.core.StringValue("5Mbps"))
eth.SetChannelAttribute("Delay", ns.core.TimeValue(ns.core.MilliSeconds(2)))
eth.SetDeviceAttribute("Mtu", ns.core.UintegerValue(1400))

devices = eth.Install(nodes)

ipv4 = ns.internet.Ipv4AddressHelper()
ipv4.SetBase(ns.network.Ipv4Address("10.1.1.0"), ns.network.Ipv4Mask("255.255.255.0"))
ipf = ipv4.Assign (devices)

addr = ns.network.InetSocketAddress(ipf.GetAddress(0), 6000)
#capp = ChordApp(addr, None)
capp = ChordApp()
capp2 = ChordApp()

#capp = ns.applications.UdpEchoServer()
nodes.Get(0).AddApplication(capp);
nodes.Get(1).AddApplication(capp2);

############
#pointToPoint = ns.point_to_point.PointToPointHelper()
#pointToPoint.SetDeviceAttribute("DataRate", ns.core.StringValue("5Mbps"))
#pointToPoint.SetChannelAttribute("Delay", ns.core.StringValue("2ms"))
#
#devices = pointToPoint.Install(nodes)
#
#stack = ns.internet.InternetStackHelper()
#stack.Install(nodes)
#
#echoServer = ns.applications.UdpEchoServerHelper(9)
#
#serverApps = echoServer.Install(nodes.Get(1))
#serverApps.Start(ns.core.Seconds(1.0))
#serverApps.Stop(ns.core.Seconds(10.0))
#
#echoClient = ns.applications.UdpEchoClientHelper(interfaces.GetAddress(1), 9)
#echoClient.SetAttribute("MaxPackets", ns.core.UintegerValue(1))
#echoClient.SetAttribute("Interval", ns.core.TimeValue(ns.core.Seconds (1.0)))
#echoClient.SetAttribute("PacketSize", ns.core.UintegerValue(1024))
#
#clientApps = echoClient.Install(nodes.Get(0))
#clientApps.Start(ns.core.Seconds(2.0))
#clientApps.Stop(ns.core.Seconds(10.0))

#visualizer.start()
ns.core.Simulator.Run()
ns.core.Simulator.Destroy()

