# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Kitty.
#
# Kitty is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Kitty is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kitty.  If not, see <http://www.gnu.org/licenses/>.

import SocketServer
import random
import struct
import time
import logging

HOST = '0.0.0.0'
PORT = 9999
logger = logging
logger.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


class SessionHandler(SocketServer.BaseRequestHandler):
    """
    The SessionHandler class for our server.
    First you need request a session with op_code(1), Server will return a specific session for this connect.
    After you got the session you can use op_code(2) with correct session to send data to Server.
    When Server recived op_code(2) with correct session, it will send back the packet which you send to Server.

    :Example Protocol:

        ::
            Fuzzer (client)                               Target (server)
                ||---------------(get_session)----------------->||
                ||<---------------(session_id)-------------------||
                ||----------(session_id + send_data)------------>||
                ||<---------(session_id + send_data)-------------||


    :get_session:

        ::
            get_session = Template(name='get_session', fields=[
                UInt8(value=1, name='op_code', fuzzable=False),
                UInt16(value=0, name='session_id', fuzzable=False)
            ])


    :send_data:
        ::
            send_data = Template(name='send_data', fields=[
                UInt8(value=2, name='op_code', fuzzable=False),
                Dynamic(key='session_id', default_value='\x00\x00'),
                String(name='data', value='some data')
            ])

    """
    def handle(self):
        # Create 2 byte specific session
        self._session = struct.pack('H', random.randrange(65535))
        while True:
            # self.request is the TCP socket connected to the client
            if self.request:
                self._data = self.request.recv(1024).strip()
                if self._data:
                    logger.info('Received data is: %s' % self._data.encode('hex'))
                    # Check is get_session packet
                    if self._data[0] == '\x01':
                        rsp = '\x01' + self._session
                        logger.info('Session id is: %s' % self._session.encode('hex'))
                        self.request.send(rsp)
                    # Check is send_data packet
                    elif self._data[0] == '\x02':
                        # Check session is correct
                        if self._data[1:3] == self._session:
                            logger.info('session is correct')
                            self.request.send(self._data)
                        else:
                            logger.info('session is incorrect')
                            self.request.close()
                            self.finish()
                            break
                else:
                    time.sleep(0.2)
            else:
                break


if __name__ == "__main__":
    # Create the server, binding to localhost on port 9999
    server = ThreadedTCPServer((HOST, PORT), SessionHandler)
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
