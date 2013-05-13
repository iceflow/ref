#!/usr/bin/env python
# -*- coding: UTF-8 -*-



import sys
import os
import errno
import fcntl
import time
from select import *
from socket import *
time_now = time.time
SCGI_SERVER_OK = 0
SCGI_SERVER_WRITE = 1
sys_time_now = time_now()

class SCGI_SOCKET:
	def __init__(self, server_ip, server_port):
		self.server_address = (server_ip, server_port)
		self.sockfd = None
		self.socket_timeout = 10
		self.socket_time = 0

		self.dst_address = None
		self.socket_status = 0
		
		# tcp data
		self.tcp_recv_length = 0
		self.tcp_recv_offset = 0
		self.tcp_recv_data = ''

		self.tcp_send_length = 0
		self.tcp_send_offset = 0
		self.tcp_send_data = ''

		self.post_body_data = ''
		self.post_body_length = 0
		self.post_body_offset = 0

		self.data_length = 0
		self.byte_count = 0

		self.last_active_time = 0

		self.body_flag = 0

	def socket_destory(self):
		self.sockfd.shutdown(SHUT_RDWR)
		self.sockfd.close()

	def socket_create(self):
		try:
			self.sockfd = socket(AF_INET, SOCK_STREAM)
			self.sockfd.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
			self.sockfd.bind(self.server_address)
			self.sockfd.listen(128)
		except Exception, e:
			print e
				
	def socket_set(self, conn, address):
		self.sockfd = conn
		self.dst_address = address

	def tcp_accept(self):
		return self.sockfd.accept()

	def sendmsg(self):
		try:
			send_size = self.sockfd.send(self.tcp_send_data[self.tcp_send_offset:])
			if send_size <= 0:
				return -1
				
			if send_size != 0:
				self.tcp_send_offset += send_size
				if self.tcp_send_offset == self.tcp_send_length:
					self.tcp_send_length = 0
					self.tcp_send_offset = 0
					return 1
			else:
				self.tcp_send_length = 0
				self.tcp_send_offset = 0
				return 1		

		except Exception , e:
			print e

		return 0

	def recvmsg(self):
		try:
			if self.data_length == 0:			
				recv_data = self.sockfd.recv(1)	
				if len(recv_data) <= 0:
					return -1

				self.byte_count += 1
				self.tcp_recv_data += recv_data	
				if recv_data[0] == ":":
					self.data_length = int(self.tcp_recv_data[:self.byte_count-1])
					self.tcp_recv_length = self.data_length + 1
					self.tcp_recv_offset = 0
					self.tcp_recv_data = ''
			else:
				recv_data = self.sockfd.recv(self.tcp_recv_length - self.tcp_recv_offset)	
				length = len(recv_data)
				if len(recv_data) <= 0:
					return -1


				self.tcp_recv_offset += length
				self.tcp_recv_data += recv_data
				if self.tcp_recv_offset == self.tcp_recv_length:
					self.tcp_recv_offset = 0
					self.tcp_send_offset = 0		
					return 1
		except Exception, e:
			print -1

		return 0
			
	
	def recvbody(self):
		try:
			recv_data = self.sockfd.recv(self.post_body_length - self.post_body_offset)
			if len(recv_data) <= 0:		
				return -1

			self.post_body_offset += len(recv_data)
			self.post_body_data += recv_data
			if self.post_body_offset == self.post_body_length:
				self.post_body_offset = 0
				self.body_flag = 0
				return 1

		except Exception, e:
			print -1
		return 0
			
					

class SCGI_SERVER:
	DEFAULT_PORT = 4000

	def __init__(self, server_ip = '127.0.0.1' , server_port = 5000, handler = None, command_handler = None, unixpath = None, timeout = 5):
		self.server_port = server_port
		self.server_ip = server_ip
		self.server_address = (server_ip, server_port)

		# register handler
		self.handler = handler

		# register command handler 
		self.command_handler = command_handler

		self.timeout = timeout
		self.socket_dict = {}
		self.epollfd = epoll()	
		self.sockfd  = socket(AF_INET, SOCK_STREAM)
		self.sockfd.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		self.sockfd.bind(self.server_address)
		self.sockfd.listen(128)
		self.tcp_socket_class = SCGI_SOCKET(server_ip, server_port)
		self.tcp_socket_class.socket_set(self.sockfd, self.server_address)
		self.tcp_socket_class.sockfd.setblocking(0)

		self.epollfd.register(self.sockfd.fileno(), EPOLLIN)
		self.socket_dict[self.sockfd.fileno()] = self.tcp_socket_class    
		self.Running = True	

		# unix socket data
		self.unixpath = unixpath
		self.dst_address = None	
		self.cmdfd = None

		self.client_number = 0

	def server_unix_socket(self):
		if os.path.exists(self.unixpath):				
			os.remove(self.unixpath)		
		try:
			self.cmdfd = socket(AF_UNIX, SOCK_DGRAM)
			self.cmdfd.bind(self.unixpath)
		except Exception, e:
			print e
									
		self.dst_address = None	
		self.cmdfd.setblocking(0)
		self.epollfd.register(self.cmdfd.fileno(), EPOLLIN)

	def server_command_handler(self, handler):
		self.command_handler = command_handler

	def server_handler(self, handler):
		self.handler = handler
	
	def handler(self, env, bodysize, body):
		pass


	def command_handler(self, cmd):
		pass

	def server_parse_scgi_request(self, data, length):
		dict = {}
		args = data.split('\0')
		i = 0
		try:
			while True:
				if args[i] and args[i+1]:
					dict[args[i]] = args[i+1]
				i += 2
		except Exception, e:
			pass
	
		return dict

	def server_run(self):
		global sys_time_now 
		old_time_now = sys_time_now
		while self.Running:
			sys_time_now = int(round(time_now()))
			events  =  self.epollfd.poll(10)
			for fileno, event in events:
				if self.cmdfd != None and fileno == self.cmdfd.fileno():
						(data, address) = self.cmdfd.recvfrom(1500)	
						ret = self.command_handler(data)	
						if ret == 1:
							self.cmdfd.sendto("Command success\n", MSG_DONTWAIT, address) 
						else:
							self.cmdfd.sendto("Command failed\n", MSG_DONTWAIT, address) 

				else:
					try:
						sock_class = self.socket_dict[fileno]
					except Exception, e:
						continue

					if event & EPOLLIN:
						if fileno == self.sockfd.fileno():
							(conn, address) = sock_class.tcp_accept()
							conn.setblocking(0)		
							new_sock_class =  SCGI_SOCKET(self.server_ip, self.server_port)
							new_sock_class.socket_set(conn, address)
							new_sock_class.last_active_time = sys_time_now
							self.socket_dict[new_sock_class.sockfd.fileno()] = new_sock_class
							self.epollfd.register(conn.fileno(), EPOLLIN)
							self.client_number += 1
						else:
							if sock_class.body_flag == 0:
								try:
									retval = sock_class.recvmsg()
									sock_class.last_active_time = sys_time_now

									if retval == 1:
										scgi_env = self.server_parse_scgi_request(sock_class.tcp_recv_data, sock_class.tcp_recv_length)
										bodysize = int(scgi_env['CONTENT_LENGTH'])
										sock_class.body_flag = 0 
										if scgi_env['REQUEST_METHOD'] == 'GET': 
											ret, data = self.handler(scgi_env, bodysize, '')

											if ret == SCGI_SERVER_WRITE:
												sock_class.tcp_send_data = 'Content-type: text/html\r\nConnection: keep-alive\r\n\r\n' + data
												sock_class.tcp_send_length = len(sock_class.tcp_send_data)
												sock_class.tcp_send_offset = 0
												self.epollfd.modify(sock_class.sockfd.fileno(), EPOLLOUT)		
											else:
												self.epollfd.unregister(sock_class.sockfd.fileno())
												del self.socket_dict[sock_class.sockfd.fileno()]
												sock_class.socket_destory()
												self.client_number -= 1

										elif scgi_env['REQUEST_METHOD'] == 'POST':
											if bodysize != 0:		
												sock_class.post_body_length = bodysize
												sock_class.post_body_offset = 0
												sock_class.body_flag = 1
												sock_class.post_body_data = ''

									elif retval == -1:
										self.epollfd.unregister(sock_class.sockfd.fileno())
										del self.socket_dict[sock_class.sockfd.fileno()]
										sock_class.socket_destory()
										self.client_number -= 1



								except Exception, e:
									print e

							else:
								try:
									retval = sock_class.recvbody()
									sock_class.last_active_time = sys_time_now
									if retval == 1:
										ret, data = self.handler(scgi_env, bodysize, sock_class.post_body_data)

										sock_class.body_flag = 0 
										if ret == SCGI_SERVER_WRITE:
											#sock_class.tcp_send_data = 'Content-type: text/html\r\n\r\n' + data
											sock_class.tcp_send_data = 'Content-type: text/html\r\nConnection: keep-alive\r\n\r\n' + data
											sock_class.tcp_send_length = len(sock_class.tcp_send_data)
											sock_class.tcp_send_offset = 0
											self.epollfd.modify(sock_class.sockfd.fileno(), EPOLLOUT)		
										else:
											self.epollfd.unregister(sock_class.sockfd.fileno())
											del self.socket_dict[sock_class.sockfd.fileno()]
											sock_class.socket_destory()
											self.client_number -= 1

									elif retval == -1:
										self.epollfd.unregister(sock_class.sockfd.fileno())
										del self.socket_dict[sock_class.sockfd.fileno()]
										sock_class.socket_destory()
										self.client_number -= 1



								except Exception, e:
									print e

			
					elif event & EPOLLOUT:
						try:
							retval = sock_class.sendmsg()
							sock_class.last_active_time = sys_time_now
							if retval == 1:
								try:
									self.epollfd.unregister(sock_class.sockfd.fileno())
									del self.socket_dict[sock_class.sockfd.fileno()]
									sock_class.socket_destory()
									self.client_number -= 1
								except Exception, e:
									print e

							elif retval == -1:
								self.epollfd.unregister(sock_class.sockfd.fileno())
								del self.socket_dict[sock_class.sockfd.fileno()]
								sock_class.socket_destory()
								self.client_number -= 1


						except Exception, e:
							print e


			# check timeout socket	
			if sys_time_now - old_time_now  > self.timeout:
				old_time_now = sys_time_now
				delete_list = []	
				for key in self.socket_dict:
					if key != self.sockfd.fileno():
						if sys_time_now - self.socket_dict[key].last_active_time > self.timeout:
							delete_list.append(self.socket_dict[key])


				for sock_class in delete_list:
					try:
						self.epollfd.unregister(sock_class.sockfd.fileno())
						del self.socket_dict[sock_class.sockfd.fileno()]
						sock_class.socket_destory()
						self.client_number -= 1
					except Exception, e:
						print "error:", e	
					
	def server_destory(self):
		delete_list = []
		for key in self.socket_dict:
			try:
				sock_class = self.socket_dict[key]
				delete_list.append(sock_class)
			except Exception, e:
				pass


		for sock_class in delete_list:
			self.epollfd.unregister(sock_class.sockfd.fileno())
			del self.socket_dict[sock_class.sockfd.fileno()]
			sock_class.socket_destory()	


		try:
			del self.socket_dict[self.sockfd.fileno()]
			self.epollfd.unregister(self.sockfd.fileno())
			self.sockfd.close()

		except Exception, e:
			print e



