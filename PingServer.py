#!/usr/bin/env python
"""
	One HTTP Server For Ping On Linux OS
	NOTE: It must start by root user for ping icmp
	ex. sudo python PingServer.py port  
	 port default as 8181

	client can call as follow:
	curl 'http://localhost:8181/getping?host=10.0.0.40&count=5&timeout=1'
	and return [0, 0.096, 0.06] [packages lost precent, avg round trip time(ms), max round trip time(ms)]
"""

from BaseHTTPServer import BaseHTTPRequestHandler
import os
import select
import socket
import struct
import sys
import time
import json
import urlparse

PING_COUNT = 5 
PING_TIMEOUT=2
ALLOW_IPS = ("10.0.0.40","127.0.0.1","localhost")
ALLOW_URI = ("/getping")

	
class PingServerHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		parsed_path = urlparse.urlparse(self.path)
		client_ip = self.client_address[0]
		uri = parsed_path.path.rstrip("/")

		if client_ip not in ALLOW_IPS or uri not in ALLOW_URI :
			message = "ip[%s] or uri[%s] not allowed"  %  (client_ip, uri)
			self.log_error(message)
			return self.__failed(message)

		params = urlparse.parse_qs(parsed_path.query)
		self.log_message("parse input is %s", params)
		if params.has_key('host') :
			host = params['host'][0]
			host = host.lower().strip().rstrip('/').lstrip('http://').lstrip("https://")
		else:
			message = "lost [host] arg"
			self.log_message(message)
			return self.__failed(message)

		if not params.has_key('count') :
			count = PING_COUNT
		else:
			count = int(float(params['count'][0]))

		if not params.has_key('timeout') :
			timeout = PING_TIMEOUT
		else:
			timeout = float(params['timeout'][0])

		res = self.__ping(host, timeout, count)
		self.log_message("lost precent[%s]%%, artt[%s]ms, martt[%s]ms.", res[0], res[1], res[2])
		message = json.dumps(res)

		self.send_response(200)
		self.end_headers()
 		self.wfile.write(message)
		return

	def __failed(self, message):
		self.send_response(500)
		self.end_headers()
 		self.wfile.write(message)
		return

	def __checksum(self, source_string):
		sum = 0
		count_to = (len(source_string) / 2) * 2
		for count in xrange(0, count_to, 2):
			this = ord(source_string[count + 1]) * 256 + ord(source_string[count])
			sum = sum + this
			sum = sum & 0xffffffff 

		if count_to < len(source_string):
			sum = sum + ord(source_string[len(source_string) - 1])
			sum = sum & 0xffffffff 

		sum = (sum >> 16) + (sum & 0xffff)
		sum = sum + (sum >> 16)
		sum = ~sum
		sum = sum & 0xffff

		sum = sum >> 8 | (sum << 8 & 0xff00)

		return sum

	def __receive_one_ping(self, my_socket, id, timeout):
		time_left = timeout
		while True:
			started_select = time.time()
			what_ready = select.select([my_socket], [], [], time_left)
			how_long_in_select = (time.time() - started_select)
			if what_ready[0] == []: # Timeout
				return

			time_received = time.time()
			received_packet, addr = my_socket.recvfrom(1024)
			icmpHeader = received_packet[20:28]
			type, code, mychecksum, packet_id, sequence = struct.unpack(
				"bbHHh", icmpHeader
			)  
			if packet_id == id:
				bytes = struct.calcsize("d")
				time_sent = struct.unpack("d", received_packet[28:28 + bytes])[0]
				return time_received - time_sent

			time_left = time_left - how_long_in_select
			if time_left <= 0:
				return


	def __send_one_ping(self, my_socket, dest_addr, id, psize):
		ICMP_ECHO_REQUEST = 8
		dest_addr  =  socket.gethostbyname(dest_addr)

		# Remove header size from packet size
		psize = psize - 8

		# Header is type (8), code (8), checksum (16), id (16), sequence (16)
		my_checksum = 0

		# Make a dummy heder with a 0 checksum.
		header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, id, 1)
		bytes = struct.calcsize("d")
		data = (psize - bytes) * "Q"
		data = struct.pack("d", time.time()) + data

		# Calculate the checksum on the data and the dummy header.
		my_checksum = self.__checksum(header + data)

		# Now that we have the right checksum, we put that in. It's just easier
		# to make up a new header than to stuff it into the dummy.
		header = struct.pack(
			"bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), id, 1
		)
		packet = header + data
		my_socket.sendto(packet, (dest_addr, 1)) # Don't know about the 1


	def __do_one(self, dest_addr, timeout, psize):
		"""
		Returns either the delay (in seconds) or none on timeout.
		"""
		icmp = socket.getprotobyname("icmp")
		try:
			my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
		except socket.error, (errno, msg):
			if errno == 1:
				# Operation not permitted
				msg = msg + (
					" - Note that ICMP messages can only be sent from processes"
					" running as root."
				)
				raise socket.error(msg)
			raise # raise the original error

		my_id = os.getpid() & 0xFFFF

		self.__send_one_ping(my_socket, dest_addr, my_id, psize)
		delay = self.__receive_one_ping(my_socket, my_id, timeout)

		my_socket.close()
		return delay

	def __ping(self, dest_addr, timeout, count, psize = 64):
		mrtt = None
		artt = None
		lost = 0
		plist = []

		for i in xrange(count):
			try:
				delay = self.__do_one(dest_addr, timeout, psize)
			except socket.gaierror, e:
				print "failed. (socket error: '%s')" % e[1]
				break

			if delay != None:
				delay = delay * 1000
				plist.append(delay)
			
		# Find lost package percent
		percent_lost = 100 - (len(plist) * 100 / count)

		# Find max and avg round trip time
		if plist:
			mrtt = round(max(plist), 3)
			artt = round(sum(plist) / len(plist),3)

		return percent_lost, mrtt, artt

def get_now_time():
	now = time.time()
	year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
	s = "%04d-%02d-%02d %02d:%02d:%02d" % (
 		year, month, day, hh, mm, ss)
	return s

if __name__=='__main__':
	from BaseHTTPServer import HTTPServer
	port = len(sys.argv)>1 and int(sys.argv[1]) or 8181
	server = HTTPServer(('',port),PingServerHandler)
	print '[%s] Starting server, use <Ctrl-C> to stop' % get_now_time()
	server.serve_forever()

	