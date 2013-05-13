#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import zlib
import random
import MySQLdb
import sys
import  os
import string
import struct
import datetime
import time
import os,sys
import urllib


class post_data:
	def __init__(self):
		self.dict = {}
		self.dict_desc = {}
		self.key = ""
		self.keylen = 0


	def parse_desc(self, text):
		name = ""
		filename = ""

		ret = text.find('name="')	
		if ret != -1:
			temp = text[ret+6:]			
			ret = temp.find('"')					
			if ret != -1:
				name = temp[:ret]		
		else:
			return name, filename	

		ret = text.find('filename="')
		if ret != -1:
			temp = text[ret+10:]			
			ret = temp.find('"')					
			if ret != -1:
				filename = temp[:ret]		
			else:
				return name, filename	
		

		return name, filename
		

	def get_data(self, key):
		try:
			return self.dict[key], self.dict_desc[key]
		except Exception, e:
			return "", ""

		return "", ""

	def parse_data(self, body):
		ret = body.find('\r\n')	
		if ret != -1:
			self.key = body[:ret-1]	
			self.keylen = len(self.key)
		else:
			return -1


		while True:
			ret = body.find(self.key)
			if ret != -1:
				body = body[ret+self.keylen:]
				ret = body.find('Content-Disposition:')
				if ret != 1:
					ret = body.find('\r\n\r\n')		
					if ret != -1:
						text = body[:ret]	
						body = body[ret+4:]
						name, filename = self.parse_desc(text)

						ret = body.find(self.key)
						if ret != -1:
							content = body[:ret]	
							self.dict[name] = content[:-2]
							self.dict_desc[name] = filename
							body = body[ret:]
	
							
			else:
				break	



			
			


