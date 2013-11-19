#!/usr/bin/python
# -*- coding: utf-8 -*-


# This file is part of fmatoolbox.
#
# fmatoolbox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# fmatoolbox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LinShare user cli.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2013 Frédéric MARTIN
#
# Contributors list :
#
#  Frédéric MARTIN frederic.martin.fma@gmail.com
#


import os
import logging
import getpass
import base64
import copy
import datetime
from ordereddict import OrderedDict
import sys
import ConfigParser


# ---------------------------------------------------------------------------------------------------------------------
log = logging.getLogger()
log.setLevel(logging.INFO)
# logger formats
myFormat = logging.Formatter("%(asctime)s %(levelname)-8s: %(message)s", "%H:%M:%S")
myDebugFormat = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s:%(funcName)s:%(message)s", "%H:%M:%S")
# logger handlers
streamHandler = logging.StreamHandler(sys.stdout)
streamHandler.setFormatter(myFormat)
log.addHandler(streamHandler)
# debug mode
# if you need debug during class construction, file config loading, ...,  you need to modify the logger level here.
if False:
	log.setLevel(logging.DEBUG)
	streamHandler.setFormatter(myDebugFormat)

# global logger variable
log = logging.getLogger('linshare-cli')


# ---------------------------------------------------------------------------------------------------------------------
class DefaultHook(object):
	def __init__(self):
		pass

	def __call__(self, elt):
		#plugin ? hook ? post function ? ex decode pwd
		pass

# ---------------------------------------------------------------------------------------------------------------------
class Base64DataHook(DefaultHook):
	def __init__(self, warning = False):
		self.warning = warning

	def __call__(self, elt):
		if elt.value :
			try:
				data = base64.b64decode(elt.value)
				elt.value = data
			except TypeError as e:
				if self.warning :
					log.warn("current field '%(name)s' is not stored in the configuration file with base64 encoding" , { "name" : elt.name })
				else :
					raise e

# ---------------------------------------------------------------------------------------------------------------------
class Config(object):

	def __init__(self, prog_name, config_file = None, description = None, mandatory = False ) :
		self.config_file = config_file
		self.prog_name = prog_name
		self.sections = OrderedDict()
		self.mandatory = mandatory
		self._default_section = self.add_section(Section("DEFAULT"))

	def add_section(self, section):
		if not isinstance(section, Section):
			raise TypeError("argument should be a subclass of Section")
		self.sections[section.name] = section
		return section

	def get_section(self, section):
		return self.sections.get(section)

	def get_default_section(self):
		return self._default_section

	def load(self):
		fileParser = ConfigParser.SafeConfigParser()
		discoveredFileList = []
		if self.config_file :
			if isinstance(self.config_file , str):
				discoveredFileList = fileParser.read(self.config_file)
			else:
				discoveredFileList = fileParser.readfp(self.config_file, "file descriptor")
		else:
			defaultFileList = []
			defaultFileList.append(self.prog_name + ".cfg")
			defaultFileList.append(os.path.expanduser('~/.' + self.prog_name + '.cfg'))
			defaultFileList.append('/etc/' + self.prog_name + '.cfg')
			discoveredFileList = fileParser.read(defaultFileList)

		log.debug("discoveredFileList: " + str(discoveredFileList))

		if self.mandatory and len(discoveredFileList) < 1 :
			msg="The required config file was missing. Default config files : " + str(defaultFileList)
			log.error(msg)
			raise EnvironmentError(msg)

		#print fileParser.items("DEFAULT")
		for s in self.sections.values():
			log.debug("loading section : " + s.name)
			s.load(fileParser)

	def write_default_config_file(self):
		pass

	def reload(self, args):
		pass

	def push(self, args):
		pass

	def __getattr__(self, name):
		if name.lower() == "default":
			return self._default_section
		s = self.sections.get(name)
		if s :
			return s
		else:
			raise AttributeError("'%(class)s' object has no attribute '%(name)s'" 
						% { "name" : name, "class" : self.__class__.__name__ } )

# ---------------------------------------------------------------------------------------------------------------------
class Section(object):

	def __init__(self, name, description = None, prefix = None, suffix = None):
		self.elements = OrderedDict()
		self.name = name
		self.description = description
		self.prefix = prefix
		self.suffix = suffix

	def add_element(self, elt):
		if not isinstance(elt, Element):
			raise TypeError("argument should be a subclass of Element")
		self.elements[elt.name] = elt
		return elt

	def load(self, fileParser):
		for e in self.elements.values() :
			e.load(fileParser, self.name)

	def __getattr__(self, name):
		e = self.elements.get(name)
		if e :
			return getattr(e, 'value')
		else:
			raise AttributeError("'%(class)s' object has no attribute '%(name)s'" 
						% { "name" : name, "class" : self.__class__.__name__ } )

# ---------------------------------------------------------------------------------------------------------------------
class ListSection(object):

	def __init__(self, name, description = None, prefix = None, suffix = None):
		pass
# ---------------------------------------------------------------------------------------------------------------------
class Element(object):
	def __init__(self, name, e_type = str, required = False, default = None, required_as_arg = False, description = None, hooks = [ DefaultHook() ], hidden = False ):
		self.name = name
		self.e_type = e_type
		self.required = required
		self.default = default
		self.required_as_arg = required_as_arg
		self.description = description
		self.description_for_config = None
		self.description_for_argparse = None
		self.value = None
		self.hidden = hidden
		self.hooks = hooks

		for h in hooks :
			if not isinstance(h, DefaultHook):
				raise TypeError("hook argument should be a subclass of DefaultHook")

	def post_read(self):
		for h in self.hooks :
			h(self)

	def set_value(self, val):
		if not instance(val, self.e_type):
			raise TypeError("Element value from config called '%(name)s' should have the type : '%(e_type)s'" 
				 % { "name": self.name , "e_type" : self.e_type })
		self.value = val

	def load(self, fileParser, section_name):
		self._load(fileParser , section_name)
		self.post_read()

	def _load(self, fileParser, section_name):
		try:
			data = fileParser.get( section_name, self.name)
			log.debug("field found : " + self.name )
			if self.required :
				if not data :
					msg = "The required field '%(name)s' was missing from the config file." % { "name": self.name }
					log.error(msg)
					raise ValueError(msg)
				data = self.e_type(data)
			elif self.default :
				if not data :
					data = self.default

			log.debug("field found : '%(name)s' , value : '%(data)s', type : '%(e_type)s'" , { "name": self.name , "data": data , "e_type" : self.e_type })
			data = self.e_type(data)

			# happens only when the current field is present, type is string, but value is ''
			if not data:
				msg = "The optional field '%(name)s' was present, type is string, but the current value is an empty string." % { "name": self.name }
				log.error(msg)
				raise ValueError(msg)

			self.value = data

		except ConfigParser.NoOptionError :
			if self.required :
				msg = "The required field " + self.name  + " was missing from the config file."
				log.error(msg)
				raise ValueError(msg)

			if self.default :
				self.value = self.default
				log.debug("Field not found : " + self.name + ", default value : " + str(self.default))
			else:
				log.debug("Field not found : " + self.name)

