import socket
def main():
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect(('localhost', 6000))
	print(sock.send("3:lol"))
	print(sock.send("3:lol"))
	print(sock.send("8:whatever"))
	sock.close()
	#totalsent = 0
	#while totalsent < len(netstring):
	#	sent = self.sock.send(netstring[totalsent:])
	#	if sent == 0:
	#		raise RuntimeError("connection broken")
	#	totalsent += sent

if __name__ == "__main__":
	main()
