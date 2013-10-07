CC=g++
CFLAGS=-O3 -g -pthread -std=c++11 -Wall
INCLUDES=-I/usr/local/include/ns3.16 -I/usr/include/gtk-2.0 -I/usr/lib/i386-linux-gnu/gtk-2.0/include -I/usr/include/atk-1.0 -I/usr/include/cairo -I/usr/include/gdk-pixbuf-2.0 -I/usr/include/pango-1.0 -I/usr/include/gio-unix-2.0 -I/usr/include/glib-2.0 -I/usr/lib/i386-linux-gnu/glib-2.0/include -I/usr/include/pixman-1 -I/usr/include/freetype2 -I/usr/include/libpng12 -I/usr/include/libxml2 -I/usr/include/python2.7
SETTINGS=-DNS3_ASSERT_ENABLE -DNS3_LOG_ENABLE -DHAVE_PACKET_H=1 -DHAVE_DL=1 -DSQLITE3=1 -DHAVE_IF_TUN_H=1 -DNDEBUG -D_FORTIFY_SOURCE=2
LDFLAGS=-L/usr/lib -L/usr/local/lib -lns3.16-test-debug -lns3.16-csma-layout-debug -lns3.16-point-to-point-layout-debug -lns3.16-netanim-debug -lns3.16-lte-debug -lns3.16-spectrum-debug -lns3.16-antenna-debug -lns3.16-aodv-debug -lns3.16-dsdv-debug -lns3.16-dsr-debug -lns3.16-mesh-debug -lns3.16-olsr-debug -lns3.16-csma-debug -lns3.16-wimax-debug -lns3.16-applications-debug -lns3.16-virtual-net-device-debug -lns3.16-uan-debug -lns3.16-energy-debug -lns3.16-flow-monitor-debug -lns3.16-nix-vector-routing-debug -lns3.16-tap-bridge-debug -lns3.16-visualizer-debug -lns3.16-internet-debug -lns3.16-bridge-debug -lns3.16-point-to-point-debug -lns3.16-mpi-debug -lns3.16-wifi-debug -lns3.16-buildings-debug -lns3.16-propagation-debug -lns3.16-mobility-debug -lns3.16-config-store-debug -lns3.16-tools-debug -lns3.16-stats-debug -lns3.16-emu-debug -lns3.16-topology-read-debug -lns3.16-network-debug -lns3.16-core-debug -lrt -lgtk-x11-2.0 -lgdk-x11-2.0 -latk-1.0 -lgio-2.0 -lpangoft2-1.0 -lpangocairo-1.0 -lgdk_pixbuf-2.0 -lcairo -lpango-1.0 -lfreetype -lfontconfig -lgobject-2.0 -lglib-2.0 -lxml2 -lsqlite3 -lpython2.7
SOURCES=tcp_sock.cc
OBJECTS=$(SOURCES:.cc=.o)
EXECUTABLE=tcp_sock

all: $(SOURCES) $(EXECUTABLE)
	
$(EXECUTABLE): $(OBJECTS) 
	$(CC) -o $@ $(OBJECTS) $(LDFLAGS) 

.cc.o:
	$(CC) $(INCLUDES) $(SETTINGS) -c $< -o $@ $(CFLAGS) 

clean:
	rm -rf $(EXECUTABLE) $(OBJECTS)
	

