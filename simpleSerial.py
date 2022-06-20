# importing the necessary python module
import os, time, threading
import serial, serial.tools.list_ports

# Lock acquire timeout 
LOCK_TIMEOUT = 2

# Constant to define simple serial preamble byte
SIMPLE_SERIAL_PREAMBLE_BYTE = b'\xAA'

# Constant to define simple serial version 1 byte
SIMPLE_SERIAL_VERSION_1 = b'\x01'

# Constant to defnie simple serial frame end byte
SIMPLE_SERIAL_FRAME_END = b'\x1e'

# Default baud rate for the application
default_baud='9600'

# List baud rates supported by the application
baud_list = ['600','1200', '1800', '2400', '4800', '9600', '19200', '38400', '57600', '115200']

# Default parity for the application
default_parity = 'None'

# List of parity type
parity_list = ['None', 'Odd', 'Even']

# ---------------------------------------------------------------------------------------------------------------------------------------------------------


# CUSTOM EXCEPTIONS ---------------------------------------------------------------------------------------------------------------------------------------

class OperationTimedOut( Exception ):
    """This exception is raised when an operation times-out
    """
    pass

class OperationFailed( Exception ):
    """This exception is raised when an operation fails
    """
    pass

class OperationInvalid( Exception ):
    """This exception is raied when an operation is invalid
    """
    pass

class OperationNotAllowed( Exception ):
    """This exception is raised when an operation is not allowed
    """
    pass

class OperationInvalidParameters( Exception ):
    """This exception is raised when an operation is invalid
    """
    pass

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


def LOG( str ):
    """This function is used to send logs to console when logging is enabled

    Args:
        str (any object): Object to be printed on the console
    """
    global LOG_ENABLED
    if LOG_ENABLED:
        print(str)

def getPorts():
    """This function is used to get a list of available serial ports

    Returns:
        list : A list containing names of available serial ports 
    """
    ports_list=[]
    for i in list(serial.tools.list_ports.comports()):
        ports_list.append(i.device)
    if len(ports_list) == 0:
        ports_list.append('-')
    return ports_list

def SERIAL_PARITY(parity):
    """This function return parity code for given parity type

    Args:
        parity (str): A string representing parity type

    Returns:
        str: parity code character
    """
    if parity == 'Even':
        return 'E'
    elif parity == 'Odd':
        return 'O'
    else:
        return 'N'

class simpleSerialDevice:

    # Change arguments to **kwargs
    def __init__( self, _port, _baudrate = 115200, _stop_bits = 1, _parity = "None" ):
        """This is the class constructor

        Args:
            _port (str): The port which the device is connected to
            _baudrate (int): The baudrate for serial communication with the Device. Defaults to 115200.
            _stop_bits (int): Stop bits. Defaults to 1.
            _parity (str): Parity - Even or Odd. Defaults to "None".
        """

        # Channel related members
        self.__PORT = _port
        self.__BAUDRATE = _baudrate
        self.__STOP_BITS = _stop_bits
        self.__PARITY = _parity
        self.__DEVICE = None
 
        # Create a serial device object, read operation in polling mode
        self.__DEVICE = serial.Serial( timeout = 0 )
        self.__DEVICE.port = self.__PORT
        self.__DEVICE.baudrate = int(self.__BAUDRATE)
        self.__DEVICE.stopbits = int(self.__STOP_BITS)
        self.__DEVICE.parity = SERIAL_PARITY( self.__PARITY )

        self.__SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_PREABLE"
        self.__SIMPLE_SERIAL_PACKET_END_TIME = 0
        self.__RECV_MSG = { "title" : 0, "length" : 0, "message" : b'' }

    def connect(self):
        """This function is used to connect to the Device over serial port.
        """
        self.__DEVICE.open()

    def recv(self):
        """This function to receive a simple serial message from connected device. It must be called periodically for scanning for messages.

        Returns:
            dict/NoneType: If a valid message is received a dict over containing the message is returned
        """
        # Read one byte from the serial buffer
        byt = self.__DEVICE.read(1)

        # Add condition to verify if a byte is received
        if True:
            if self.__SIMPLE_SERIAL_SCAN_STATE == "SIMPLE_SERIAL_PREAMBLE":
                
                # If the preamble byte is received, go to next state
                if byt == SIMPLE_SERIAL_PREAMBLE_BYTE:
                    self.__SIMPLE_SERIAL_PACKET_END_TIME = time.time() + self.__TIMEOUT
                    self.__SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_VERSION"

            elif self.__SIMPLE_SERIAL_SCAN_STATE == "SIMPLE_SERIAL_VERSION":

                # If the version byte indicates version 1 then, move ahead
                if byt == SIMPLE_SERIAL_VERSION_1:
                    self.__SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_TITLE"
                # Otherwise, go back to preamble scan
                else:
                    self.__SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_PREAMBLE"

            elif self.__SIMPLE_SERIAL_SCAN_STATE == "SIMPLE_SERIAL_TITLE":

                # Get the title as integer
                self.__RECV_MSG["title"] = int.from_bytes( byt, "little" )
                self.__SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_LENGTH"

            elif self.__SIMPLE_SERIAL_SCAN_STATE == "SIMPLE_SERIAL_LENGTH":

                # Empty the message buffer
                self.__RECV_MSG["message"] = b''

                # Save the message length in bytes
                self.__RECV_MSG["length"] = int.from_bytes( byt, "little" )

                recv_num_bytes = 0

                # If the length of message is 0 go to end scan
                if self.__RECV_MSG["length"] == 0:
                    __SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_END"
                else:
                    __SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_MESSAGE"

            elif __SIMPLE_SERIAL_SCAN_STATE == "SIMPLE_SERIAL_MESSAGE":

                self.__RECV_MSG["message"] += byt
                recv_num_bytes += 1

                if recv_num_bytes == self.__RECV_MSG["length"]:
                    __SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_END"

            elif __SIMPLE_SERIAL_SCAN_STATE == "SIMPLE_SERIAL_END":
                
                if byt == SIMPLE_SERIAL_FRAME_END:
                   # self.__RECV_NUM_MSG += 1
                    return self.__RECV_MSG
                
                __SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_PREAMBLE"

            if self.__SIMPLE_SERIAL_SCAN_STATE != "SIMPLE_SERIAL_PREAMBLE" and self.__SIMPLE_SERIAL_PACKET_END_TIME > time.time() :
                self.__SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_PREAMBLE"
                return
            else:
                # Make a recursive call to check for more bytes in input stream
                return self.recv()
        else:
            if self.__SIMPLE_SERIAL_SCAN_STATE != "SIMPLE_SERIAL_PREAMBLE" and self.__SIMPLE_SERIAL_PACKET_END_TIME > time.time() :
                self.__SIMPLE_SERIAL_SCAN_STATE = "SIMPLE_SERIAL_PREAMBLE"
                return

    def send_message( self, msg, _timeout = LOCK_TIMEOUT ):
        """This function is used to send a simple serial message to the connected device.

        Args:
            msg (dict): A dictionary containing simple serial message fields
            _timeout (int, optional): Timeout for send operation in seconds. Defaults to LOCK_TIMEOUT.
        """
        
        msg["length"] = len(msg["message"])
        
        if msg["version"] ==  "1":

            bytes_to_send = b''
            bytes_to_send += SIMPLE_SERIAL_PREAMBLE_BYTE + SIMPLE_SERIAL_VERSION_1 + msg["title"].to_bytes(1, 'little') + msg["length"].to_bytes(1, 'little') + msg["message"] + SIMPLE_SERIAL_FRAME_END
            
            self.__DEVICE.write( bytes_to_send, timeout = _timeout )

    def disconnect(self):
        """This function is used to disconnect from simple serial device.
        """
        self.__DEVICE.close()