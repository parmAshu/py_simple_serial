"""
@author : Ashutosh.p
@date : 26-04-2022
@brief : This is the module that contains all the necessary classes and APIs for simple serial communication
"""
# importing the necessary python module
import os, time, threading
from queue import Queue
import py_simple_serial.simpleSerialConstants as const
import serial, serial.tools.list_ports

# Default baud rate for the application
default_baud='9600'

# List baud rates supported by the application
baud_list = ['600','1200', '1800', '2400', '4800', '9600', '19200', '38400', '57600', '115200']

# Default parity for the application
default_parity = 'None'

# List of parity type
parity_list = ['None', 'Odd', 'Even']

#LOGGER = #LOGGER.create_#LOGGER( 'simple_serial.log', create_logfile = False, backupCount=1, maxBytes=50*1048576, log_level="ERROR", STDOUT_PRINT=True)

def LOG( str ):
    """
    @brief This function is used to log strings to console screen
    """
    global LOG_ENABLED
    if LOG_ENABLED:
        print(str)

def getPorts():
    """
    This function returns the list of available serial ports
    PARAMETES
    ---------
    NONE
    RETURNS : list
    -------
    A list of available com  ports at the time of calling. If there are no com ports available then, a list with single item
    '-' is returned. This can be used to make decision at higher level.
    """
    ports_list=[]
    for i in list(serial.tools.list_ports.comports()):
        ports_list.append(i.device)
    if len(ports_list) == 0:
        ports_list.append('-')
    return ports_list

def SERIAL_PARITY(parity):
    """
    This function returns the serial.Serial class compatible parity code corresponding to the provided parity string - 'parity'
    
    PARAMETERS
    ----------
    parity : str
    The parity string
    RETURNS
    -------
    E : for even parity
    O : for odd parity
    N : for no parity
    """
    if parity == 'Even':
        return 'E'
    elif parity == 'Odd':
        return 'O'
    else:
        return 'N'

class simpleSerialDevice:
    """
    @brief This class contains all the necessary APIs for communicating with a simple serial enabled device
    """

    # Change arguments to **kwargs
    def __init__( self, _port, _baudrate = 115200, _stop_bits = 1, _parity = "None", _timeout = None, _recv_callback = None, _error_callback = None ):
        """
        @brief This is the class constructor
        """

        # Channel related members
        self.__PORT = _port
        self.__BAUDRATE = _baudrate
        self.__STOP_BITS = _stop_bits
        self.__PARITY = _parity
        self.__TIMEOUT = _timeout
        self.__DEVICE = None
        self.__CHANNEL_LOCK = threading.Lock()
        
        # Receive state machine related varaibles
        self.__SIMPLE_SERIAL_RECV_STATE_MACHINE_RESET = False
        self.__SIMPLE_SERIAL_RECV_STATE_MACHINE_RESET_LOCK = threading.Lock()
        self.__RECV_STATE_MACHINE_THREAD = None

        # Callbacks
        self.__RECV_CALLBACK = _recv_callback
        self.__ERROR_CALLBACK = _error_callback
        
        # Receive and send queue
        self.__RECVQ = Queue()
        self.__SENDQ = Queue()
        self.__RECV_NUM_MSG = 0

        # Create a serial device object
        self.__DEVICE = serial.Serial()

        # Populating various parameters for the device
        self.__DEVICE.port = self.__PORT
        self.__DEVICE.baudrate = int(self.__BAUDRATE)
        self.__DEVICE.stopbits = int(self.__STOP_BITS)
        self.__DEVICE.parity = SERIAL_PARITY( self.__PARITY )
        self.__DEVICE.timeout = self.__TIMEOUT

    def connect(self):
        """
        @brief This function is used to connect to the serial device

        @detail Internally it opens a serail connection
        """

        try:

            self.__DEVICE.open()
        except Exception as e:

            # Call the error callback function if there is some exception in opening the port
            if self.__ERROR_CALLBACK != None :
                self.__ERROR_CALLBACK( { "reason" : "connection_failed" } )

            # Raise the exception again
            raise e

    def recv_state_machine(self):
        """
        @brief This function runs the simple serial state machine. It will be run as a separate thread
        """

        try:

            recv_msg = { "title" : 0, "length" : 0, "message" : b'' }
            recv_num_bytes = 0
            byt = b''

            simple_serial_scan_state = "SIMPLE_SERIAL_PREAMBLE"

            while True:

                # dequeue to bytes and send to pyserial api
                # if self.__SENDQ.qsize() :
                #    self.__DEVICE.write( self.__SENDQ.get() ) 

                # Read one byte from the serial buffer
                byt = self.__DEVICE.read(1)

                # If the reset signal is active then, restart the state machine
                if self.__SIMPLE_SERIAL_RECV_STATE_MACHINE_RESET :
                    simple_serial_scan_state = "SIMPLE_SERIAL_PREAMBLE"

                if simple_serial_scan_state == "SIMPLE_SERIAL_PREAMBLE":
                    
                    # If the preamble byte is received, go to next state
                    if byt == const.SIMPLE_SERIAL_PREAMBLE_BYTE:

                        #LOGGER.debug( "PREAMBLE" )

                        # Set the value of reset variable to False
                        self.__SIMPLE_SERIAL_RECV_STATE_MACHINE_RESET_LOCK.acquire()
                        self.__SIMPLE_SERIAL_RECV_STATE_MACHINE_RESET = False
                        self.__SIMPLE_SERIAL_RECV_STATE_MACHINE_RESET_LOCK.release()
                        
                        simple_serial_scan_state = "SIMPLE_SERIAL_VERSION"

                elif simple_serial_scan_state == "SIMPLE_SERIAL_VERSION":
                    
                    #LOGGER.debug( "VERSION" )

                    # If the version byte indicates version 1 then, move ahead
                    if byt == const.SIMPLE_SERIAL_VERSION_1:
                        simple_serial_scan_state = "SIMPLE_SERIAL_TITLE"
                    # Otherwise, go back to preamble scan
                    else:
                        simple_serial_scan_state = "SIMPLE_SERIAL_PREAMBLE"

                elif simple_serial_scan_state == "SIMPLE_SERIAL_TITLE":
                    
                    #LOGGER.debug("TITLE")

                    # Get the title as integer
                    recv_msg["title"] = int.from_bytes( byt, "little" )
                    simple_serial_scan_state = "SIMPLE_SERIAL_LENGTH"

                elif simple_serial_scan_state == "SIMPLE_SERIAL_LENGTH":
                    
                    #LOGGER.debug( "LENGTH" )

                    # Empty the message buffer
                    recv_msg["message"] = b''

                    # Save the message length in bytes
                    recv_msg["length"] = int.from_bytes( byt, "little" )

                    recv_num_bytes = 0

                    # If the length of message is 0 go to end scan
                    if recv_msg["length"] == 0:
                        simple_serial_scan_state = "SIMPLE_SERIAL_END"
                        #LOGGER.debug( "Next state : Serial END" )
                    else:
                        simple_serial_scan_state = "SIMPLE_SERIAL_MESSAGE"
                        #LOGGER.debug( "Next state : Serial Message" )

                elif simple_serial_scan_state == "SIMPLE_SERIAL_MESSAGE":
                    
                    #LOGGER.debug( "MESSAGE" )

                    recv_msg["message"] += byt
                    recv_num_bytes += 1

                    if recv_num_bytes == recv_msg["length"]:
                        simple_serial_scan_state = "SIMPLE_SERIAL_END"

                elif simple_serial_scan_state == "SIMPLE_SERIAL_END":

                    #LOGGER.debug( "END" )
                    
                    if byt == const.SIMPLE_SERIAL_FRAME_END:
                        
                        self.__RECVQ.put( recv_msg )
                        # self.__RECV_NUM_MSG += 1

                        # call the receive callback function 
                        if self.__RECV_CALLBACK:
                            self.__RECV_CALLBACK( recv_msg )
                    
                    simple_serial_scan_state = "SIMPLE_SERIAL_PREAMBLE"

        # If something goes wrong and the thread terminates, then call the error callback function
        except Exception as e:

            self.__DEVICE.close()

            # call the error callback
            if self.__ERROR_CALLBACK != None:
                self.__ERROR_CALLBACK( { "reason" : "receive_thread_terminated" } )
            
            # Re-raise the exception
            raise e

    def message_available(self):
        """
        @brief This function returns the number of simple serial message available in the buffer
        """
        return self.__RECVQ.qsize()

    def get_message(self):
        """
        @brief This function returns a simple serial message from the RECV buffer
        """
        #self.__RECV_NUM_MSG -=1 
        try:
            return self.__RECVQ.get()
        except Exception as e:
            
            if self.__ERROR_CALLBACK:
                self.__ERROR_CALLBACK( { "reason" : "get_message_failed" } )

            raise e

    def send_message( self, msg ):
        """
        @brief This function is used to send a simple serial message over the connected channel
        """
        #print( msg )
        try:
            msg["length"] = len(msg["message"])
            
            if msg["version"] ==  "1":
            
                bytes_to_send = b''
                bytes_to_send += const.SIMPLE_SERIAL_PREAMBLE_BYTE + const.SIMPLE_SERIAL_VERSION_1 + msg["title"].to_bytes(1, 'little') + msg["length"].to_bytes(1, 'little') + msg["message"] + const.SIMPLE_SERIAL_FRAME_END
                
                # LOGGER.debug( bytes_to_send )

                # Send the bytes to pyserial api
                #print( bytes_to_send )

                print( bytes_to_send )
                
                self.__DEVICE.write( bytes_to_send )

                # enqueue the bytes in the send buffer
                # self.__SENDQ.put( bytes_to_send )
        except Exception as e:

            if self.__ERROR_CALLBACK:
                self.__ERROR_CALLBACK( { "reason" : "send_message_failed" } )

            raise e

    def start(self):
        """
        @brief This function is used to start the receive state machine
        """
        try:
            self.__RECV_STATE_MACHINE_THREAD = threading.Thread( target=self.recv_state_machine, daemon=True )
            self.__RECV_STATE_MACHINE_THREAD.start()
        except Exception as e:
            
            self.__ERROR_CALLBACK( { "reason" : "serial_connection_failed" } )

            raise e

    def stop(self):
        """
        @brief This fucntion is used to stop the receive state machine, if it is already running
        """