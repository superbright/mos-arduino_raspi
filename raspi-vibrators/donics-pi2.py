#!/usr/bin/python

import pygatt
import time
import pygatt.backends
import array
import logging
from socketIO_client import SocketIO
import threading, time
from threading import Thread
from threading import Timer
from threading import Event
import binascii

# logging
logging.basicConfig()
logging.getLogger('pygatt').setLevel(logging.INFO)

# macs
# 1. F0:C7:7F:1E:5A:84
# 2. 04:A3:16:66:E5:DB
# 3. 60:64:05:ae:17:d9
# 4. 60:64:05:B4:3C:68
# 5. 60:64:05:AE:C6:FF
# 6. 60:64:05:B4:B4:5F
# 7. 60:64:05:B4:43:3B
# 8. 60:64:05:B3:FB:24

host = '192.168.1.212'
port = 4000
player = 'player2vib'

class KeepAliveThread(Thread):
    def __init__(self, event, device):
        Thread.__init__(self)
        self.stopped = event
        self.device = device

    def run(self):
        while not self.stopped.wait(5):
            print("KeepAliveThread", self.device)

            try:
                for uuid in self.device.discover_characteristics().keys():       
                    if (str(uuid) == 'f000b000-0451-4000-b000-000000000000'):
                        time.sleep(.1)
                        try:
                            print("Read UUID %s: %s" % (uuid, binascii.hexlify(self.device.char_read(uuid))))
                            self.device.char_write_handle(0x0025, bytearray([0x1e,0x00,0x00,0x00,0x00,0xDA,0x00,0x00]))
                        except pygatt.exceptions.NotificationTimeout:
                            print("notification timeout")
            except pygatt.exceptions.NotConnectedError:
                print "keep alive, device is not connected"
                pass

class DonicsThread(object):

    def __init__(self):

        self.mac_addresses = [
            # Player 2
            'C8:FD:19:0A:09:E2'
            # Player 2B
            #'60:64:05:B4:3C:68'
        ]

        self.adapter = pygatt.GATTToolBackend()
        self.device = None
        self.stopFlag = Event()
        self.keepAliveThread = None
        
        self.socketio = SocketIO(host, port)
        self.socketio.on('dildon', self.on_event)
        self.socketio.on('dildoff', self.on_event)
        self.connectToVibrator()

        self.receive_events_thread = Thread(target=self._receive_events_thread)
        self.receive_events_thread.daemon = True
        self.receive_events_thread.start()

        while True:
            try:
                check = raw_input()
            except EOFError:
                check = ""
            self.socketio.emit('event', check)

    def callback_func(self):
        print "yo"

    def connectToVibrator(self):
        print "connectToVibrator", self.device

        try: 
            self.device.disconnect()
        except:
            pass
        self.device = None
        self.stopFlag = Event()
        
        
        while self.device == None:
            for i in range(len(self.mac_addresses)):
                self.socketio.emit('pairing', {'player': player, 'device': self.mac_addresses[i]})
                address = self.mac_addresses[i]
                time.sleep(.5)
                self.adapter.start()
                print "adapter started", address
                device_found = False
                while not device_found:
                    try:
                        device_found = self.adapter.filtered_scan('Sync')
                        print "device_found", device_found
                        self.device = self.adapter.connect(address, timeout=10.0)
                        #self.device.subscribe("f000c000-0451-4000-b000-000000000000", callback=self.callback_func)
                    except pygatt.exceptions.BLEError as e:  
                        print "not connected: ", e
                        self.adapter.reset()
                    finally:
                        print "finally device connected?", self.device
                if self.device != None:
                    # wait for the device to REALLY be connected
                    time.sleep(.5)
                    self.socketio.emit('connected', {'player': player, 'device': self.mac_addresses[i]})
                    
                    try:
                        for uuid in self.device.discover_characteristics().keys():
                            
                            if (str(uuid) == 'f000b000-0451-4000-b000-000000000000'):
                                time.sleep(.5)
                                try:
                                    print("Read UUID %s: %s" % (uuid, binascii.hexlify(self.device.char_read(uuid))))  

                                    # self.setIdleTimeout()
                                    self.keepAliveThread = KeepAliveThread(self.stopFlag, self.device)
                                    self.keepAliveThread.start()

                                except pygatt.exceptions.NotificationTimeout:
                                    print("notification timeout")
                    except pygatt.exceptions.NotConnectedError:
                        print "immediate disconnect"
                        pass

                    

                    break
                            
    def writeCommand(self, command):
        try:
            self.device.char_write_handle(0x0025, bytearray(command))
        except pygatt.exceptions.NotConnectedError:
            print "not connected", self.device
            #self.device.connect()
            time.sleep(.5)

            # kill the thread
            print "kill the thread"
            self.stopFlag.set()

            #try to reconnect again
            time.sleep(.5)
            self.connectToVibrator()
            
       
            
            

    def setIdleTimeout(self):
        print ("setIdleTimeout", self.device)
        self.writeCommand([0x78,0xff,0x00,0x00,0x00,0x00,0x00,0x00])


    def keepAlive(self):
        print ("setIdleTimeout", self.device)
        self.writeCommand([0x1e,0x00,0x00,0x00,0x00,0xDA,0x00,0x00])

    def dildOn(self, *args):
        print ("turning on", self.device)
        self.writeCommand([0x0F,0x03,0x05,0x00,0x00,0x00,0x00,0x00])
       

    def dildOff(self, *args):
        print ("turning off", self.device)
        self.writeCommand([0x0F,0x00,0x05,0x00,0x00,0x00,0x00,0x00])
        

    def wave(self, *args):
        print ("wave", self.device)
        self.writeCommand([0x0F,0x07,0x05,0x00,0x00,0x00,0x00,0x00])
       

    def tide(self, *args):
        print ("tide", self.device)
        self.writeCommand([0x0F,0x08,0x05,0x00,0x00,0x00,0x00,0x00])
        

    def pingpong(self, *args):
        print ("pingpong", self.device)
        self.writeCommand([0x0F,0x06,0x05,0x00,0x00,0x00,0x00,0x00])
        

    def surf(self, *args):
        print ("surf", self.device)
        self.writeCommand([0x0F,0x0e,0x05,0x00,0x00,0x00,0x00,0x00])
        

    def on_event(self, event):
        try:
            if (event["player"] == player):
                if (event["set"] == "dildon"):
                    self.dildOn()
                if (event["set"] == "dildoff"):
                    self.dildOff()
                if (event["set"] == "wave"):
                    self.wave()
                if (event["set"] == "tide"):
                    self.tide()
                if (event["set"] == "pingpong"):
                    self.pingpong()
                if (event["set"] == "surf"):
                    self.surf()
                if (event["set"] == "connectvib"):
                    self.connectToVibrator()
        except:
            pass

    def _receive_events_thread(self):
        self.socketio.wait()

def main():
    DonicsThread()

#main
if __name__ == "__main__":
    print "Initializing..."
    main()
