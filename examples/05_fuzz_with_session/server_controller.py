# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This example was authored and contributed by dark-lbp <jtrkid@gmail.com>
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

from kitty.controllers.base import BaseController
import socket
import random
import struct
import threading
from socket_server import TCPServer, BaseRequestHandler
import time


class SessionHandler(BaseRequestHandler):
    '''
    The SessionHandler class for our session server.
    First you need request a session by sending 'get_session' packet to server, server will return same format packet
    with specific session inside.
    After you got the session you can communicate with server by sending 'send_data' packet to server. If your session
    is correct server will return a same packet which you just send, otherwise server will return 'session is incorrect'.
    Remember Session server only support two kind of packet 'get_session' and 'send_data'. If you send other packet to
    server, server will server will return 'packet format is incorrect' and close your current connection.
    Server will stop(fake crash) when you send a large packet(length greater than 255) with 'send_data' format.

    :Example Protocol:

        ::
            Fuzzer (client)                               Target (server)
                ||---------------(get_session)------------------>||
                ||<---------------(session_id)-------------------||
                ||----------(session_id + send_data)------------>||
                ||<---------(session_id + send_data)-------------||
                ||----------(session_id + send_data)------------>||
                ||<---------(session_id + send_data)-------------||
                ||<---------........................-------------||
                ||----------........................------------>||


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

    '''

    def __init__(self, request, client_address, server, name='SessionHandler', logger=None):
        '''
        :param request: TCP socket connected to the client
        :param client_address: Client address of request
        :param server: Session server
        :param name: Name of the object
        :param logger: Logger for the object (default: None)
        '''

        # Create 2 byte specific session for each request
        self._session = struct.pack('H', random.randrange(65535))
        self._recv_data = None
        self._resp_data = None
        self._received_packets = 0
        super(SessionHandler, self).__init__(name, request, client_address, server, logger)

    def _send_session(self):
        self._resp_data = '\x01' + self._session
        self.logger.info('Session id is: %s' % self._session.encode('hex'))
        self.request.send(self._resp_data)
        self._cleanup()

    def _send_data(self, data):
        self.request.send(data)
        self._cleanup()

    def _crash(self):
        self.logger.info('Congratulations you successful crash session server!')
        self.server.stop()
        time.sleep(1)

    def _check_session(self, data):
        if data[1:3] == self._session:
            return True
        else:
            return False

    def _check_crash(self, data):
        if len(data) > 255:
            return True
        else:
            return False

    def _cleanup(self):
        self._recv_data = None
        self._resp_data = None

    def _close(self):
        self.request.close()
        self.finish()

    def handle(self):
        while True:
            # self.request is the TCP socket connected to the client
            if self.request:
                self._recv_data = self.request.recv(1024).strip()
                if self._recv_data:
                    self._received_packets += 1
                    self.logger.debug('Received data is: %s' % self._recv_data.encode('hex'))
                    # Check is get_session packet
                    if self._recv_data == '\x01\x00\x00':
                        self._send_session()
                    # Check is send_data packet
                    elif self._recv_data[0] == '\x02':
                        if self._check_session(self._recv_data):
                            self.logger.info('session is correct')
                            if self._check_crash(self._recv_data):
                                self._crash()
                                break
                            else:
                                self._send_data(self._recv_data)
                        else:
                            self.logger.info('session is incorrect')
                            self._send_data('session is incorrect')
                            self._close()
                            break
                    else:
                        self.logger.info('Packet format is incorrect')
                        self._close()
                        break
                else:
                    self._close()
                    break
            else:
                break


class SessionServer(TCPServer):
    '''
    SessionServer is implementation of a TCP Server for the ServerFuzzer
    '''

    allow_reuse_address = True

    def __init__(self, name, server_address, request_handler, logger=None):
        '''
        :param name: Name of the object
        :param server_address: server address for socket to listen
        :param request_handler: class to handle request
        :param logger: Logger for this object (default: None)
        '''

        super(SessionServer, self).__init__(name, server_address, request_handler, logger)
        self._worker = None
        self._is_closed = False
        self.start()

    def _reset(self):
        self.__init__(self.name, self.server_address, self.request_handler, self.logger)

    def stop(self):
        self.shutdown()
        self.server_close()
        self._is_closed = True
        time.sleep(1)

    def start(self):
        self.server_bind()
        self.server_activate()
        self._worker = threading.Thread(target=self.serve_forever)
        self._worker.daemon = True
        self._worker.start()

    def restart(self):
        if self._is_closed:
            self._reset()
        else:
            self.stop()
            self._reset()


class SessionServerController (BaseController):
    '''
    This controller controls our SessionServer.
    '''

    def __init__(self, name, host, port, logger=None):
        '''
        :param name: name of the object
        :param host: Listen address for server
        :param port: Listen port for server
        :param logger: logger for the controller (default: None)
        :example:

            ::
                controller = ServerController(name='ServerController', host='target_ip', port=target_port)
        '''
        super(SessionServerController, self).__init__(name, logger)
        self._host = host
        self._port = port
        self._server = SessionServer('SessionServer', (self._host, self._port), SessionHandler)
        self._active = False

    def setup(self):
        super(SessionServerController, self).setup()
        self.logger.info('Trying to start target!!!')
        self._restart_target()
        if not self.is_victim_alive():
            msg = 'Controller cannot start target'
            raise Exception(msg)

    def teardown(self):
        super(SessionServerController, self).teardown()
        if not self.is_victim_alive():
            msg = 'Target is already down'
            self.logger.error(msg)
        else:
            msg = 'Test Finish'
            self.logger.info(msg)

    def post_test(self):
        super(SessionServerController, self).post_test()
        if not self.is_victim_alive():
            self.logger.error("Target does not respond")
            self.report.failed('Target does not respond')

    def pre_test(self, test_number):
        self._restart_target()
        super(SessionServerController, self).pre_test(test_number)

    def _restart_target(self):
        """
        Restart our Target.
        """
        self._server.restart()

    def is_victim_alive(self):
        self._active = False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((self._host, self._port))
            s.close()
            self._active = True
        except socket.error:
            return self._active
        return self._active
