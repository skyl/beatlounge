"""
Requires pyo:
http://code.google.com/p/pyo/wiki/Installation
"""
from pyo import *


class PyoServer:
    _started = False
    _server = None
    _error_msg = 'Cannot %s server; server must be started first'

    @classmethod
    def start(cls, audio='jack', **kw):
        """
        Start a pyo server or do nothing if a server has already been started.

        audio: the audio device (default: jack)
        kw: additional keyword arguments to pyo.Server
        """
        if cls._server:
            return
        cls._server = s = Server(audio=audio, **kw)
        s.boot()
        s.start()
        return s

    @classmethod
    def restart(cls):
        """
        Start and top the already running pyo Server.

        raises AssertionError if no server is running
        """
        assert cls._server, cls._error_msg % 'restart'
        cls._server.stop()
        cls._server.start()

    @classmethod
    def stop(cls):
        """
        Stop the running pyo Server.

        raises AssertionError if no server is running
        """
        assert cls._server, cls._error_msg % 'stop'
        cls._server.stop()

    @classmethod
    def shutdown(cls):
        """
        Shutdown the running pyo Server.

        raises AssertionError if no server is running
        """
        assert cls._server, cls._error_msg % 'shutdown'
        cls._server.stop()
        cls._server.shutdown()

    @classmethod
    def reboot(cls):
        """
        Reboot the running pyo Server.

        raises AssertionError if no server is running
        """
        assert cls._server, cls._error_msg % 'reboot'
        cls._server.stop()
        cls._server.shutdown()
        cls._server.boot()
        cls._server.start()

startPyo = PyoServer.start
stopPyo = PyoServer.stop
shutdownPyo = PyoServer.shutdown
restartPyo = PyoServer.restart
rebootPyo = PyoServer.reboot
