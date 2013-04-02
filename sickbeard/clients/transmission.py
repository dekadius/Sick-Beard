# Author: Mr_Orange <mr_orange@hotmail.it>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import re
import json
from base64 import b64encode

import sickbeard
from sickbeard.clients.generic import GenericClient

class TransmissionAPI(GenericClient):
    
    def __init__(self, host=None, username=None, password=None):
        
        super(TransmissionAPI, self).__init__('Transmission', host, username, password)

        self.supportsFilesWanted = True
      
        self.url = self.host + 'transmission/rpc'

    def _get_auth(self):

        post_data = json.dumps({'method': 'session-get',})

        try: 
            self.response = self.session.post(self.url, data=post_data.encode('utf-8'))
            self.auth = re.search('X-Transmission-Session-Id:\s*(\w+)', self.response.text).group(1)
        except:
            return None     
        
        self.session.headers.update({'x-transmission-session-id': self.auth})
        
        #Validating Transmission authorization
        post_data = json.dumps({'arguments': {},
                                'method': 'session-get',
                                })       
        self._request(method='post', data=post_data)            
        
        return self.auth     

    def _add_torrent_uri(self, result):

        arguments = { 'filename': result.url,
                      'paused': 1 if sickbeard.TORRENT_PAUSED else 0,
                      'download-dir': sickbeard.TORRENT_PATH
                      }
        post_data = json.dumps({ 'arguments': arguments,
                                 'method': 'torrent-add',
                                 })        
        self._request(method='post', data=post_data)

        return self.response.json['result'] == "success"

    def _add_torrent_file(self, result):
        files_wanted_indices = []
        files_unwanted_indices = []
        if result.filesWanted != None:
            indices = self.__parse_files_wanted(result.filesWanted)
            files_wanted_indices = indices[0]
            files_unwanted_indices = indices[1]

        arguments = { 'metainfo': b64encode(result.content),
                      'paused': 1 if sickbeard.TORRENT_PAUSED else 0,
                      'download-dir': sickbeard.TORRENT_PATH,
                      'files-wanted': files_wanted_indices,
                      'files-unwanted': files_unwanted_indices
                      }        
        post_data = json.dumps({'arguments': arguments,
                                'method': 'torrent-add',
                                })
        self._request(method='post', data=post_data)

	# if duplicate torrent and filesWanted is specified, try to set filesWanted on existing torrent
	if self.response.json['result'] == "duplicate torrent" and result.filesWanted != None:
            return self.__set_files_wanted(self._get_torrent_hash(result), files_wanted_indices)
        
        return self.response.json['result'] == "success"

    def _set_torrent_ratio(self, result):
        
        #torrent_id = self.response.json["arguments"]["torrent-added"]["id"]
	torrent_id = self._get_torrent_hash(result)
        
        if sickbeard.TORRENT_RATIO == '':
            # Use global settings
            ratio = None
            mode = 0
        elif float(sickbeard.TORRENT_RATIO) == 0:
            ratio = 0
            mode  = 2    
        elif float(sickbeard.TORRENT_RATIO) > 0:
            ratio = float(sickbeard.TORRENT_RATIO)
            mode = 1 # Stop seeding at seedRatioLimit

        arguments = { 'ids': [torrent_id],
                      'seedRatioLimit': ratio,
                      'seedRatioMode': mode
                      } 
        post_data = json.dumps({'arguments': arguments,
                                'method': 'torrent-set',
                                })       
        self._request(method='post', data=post_data)            
        
        return self.response.json['result'] == "success"    

    def __get_torrent_info(self, torrent_hash):
        arguments = { 'ids': [torrent_hash],
                      'fields': ['id', 'files-unwanted']}
        post_data = json.dumps({'arguments': arguments,
                                'method': 'torrent-get',
                                })
        self._request(method='post', data=post_data)

        if self.response.json['result'] != "success":
            return None

        return self.response.json["arguments"]

    def __set_files_wanted(self, torrent_hash, files_wanted_indices):
        arguments = { 'ids': [torrent_hash],
                      'files-wanted': files_wanted_indices
                      }        
        post_data = json.dumps({'arguments': arguments,
                                'method': 'torrent-set',
                                })
        
        self._request(method='post', data=post_data)

        return self.response.json['result'] == "success"

    def __handle_duplicate_torrent(self, torrent_hash, files_unwanted_indices):
        torrent_info = self.__get_torrent_info(torrent_hash)
        if torrent_info == None:
            return False
        new_files_unwanted_indices = list(set(files_unwanted_indices) | set(torrent_info['files-unwanted']))
        
        return __set_torrent_files_unwanted(torrent_hash, new_files_unwanted_indices) 

    def __parse_files_wanted(self, files_wanted):
        files_wanted_indices = []
        files_unwanted_indices = []
        index = 0
        for file_wanted in files_wanted:
            if file_wanted[1]:
                files_wanted_indices.append(index)
            else:
                files_unwanted_indices.append(index)
            index += 1

        return (files_wanted_indices, files_unwanted_indices)

api = TransmissionAPI()
