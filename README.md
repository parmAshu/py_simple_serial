# py_simple_serial 

This is a python package to communicate with a device using simple serial over uart.

---
## Module Reference

`class py_simple_serial.simpleSerial`

```__init__( self, _port, _baudrate = 115200, _stop_bits = 1, _parity = "None", packet_timeout = 0.5 )```

This is the class constructor.

**Parameters**

* _port : String representing port which a device is connected to.
* _baudrate : Integer representing communication baudrate
* _stop_bits : Integer representing number of stop bits. The default value is 1.
* _parity : String representing parity - "None", "Odd" or "Even". The default value is "None".
* packet_timeout : This is the time in seconds within which a valid simple serial packet must be received. The default value is 0.5 seconds.

```connect()```

This function is used to connect to the serial device. This function must be called before using any other function.

```recv()```

This function is used to receive a simple serial frame from the connected device. This function is used for polling for received simple serial messages.

**Returns**

The function returns `None` if no simple serial message is available. If a simple serial message is available, a dictionary of the following type is returned :

```
{
    "version" : 1,
    "title" : 12,
    "message" : b'12345'
}
```

```send_message( self, msg, _timeout = LOCK_TIMEOUT )```

This function is used to send a simple serial message to the connected device.

**Parameters**

* msg : A dictionary of representing the simple serial frame. It is of the following format -

```
{
    "version" : 1,
    "title" : 12,
    "message" : b'12345'
}
```

* _timeout : It is the time in seconds within which the transmit operation must get completed.

```disconnect()```

This function is used to disconnect the device.

---

## Sending Example

```
import time
from py_simple_serial import simpleSerial

dev = simpleSerial.simpleSerialDevice( "COM15" )
dev.connect()

frm = {
    "version" : 1,
    "title" : 15,
    "message" : b'Hello'
}

try:
    while True:
        dev.send_message( frm )
        time.sleep( 1 )
except:
    pass
finally:
    dev.disconnect()
```

---

## Receiving Example

```
import time
from py_simple_serial import simpleSerial

dev = simpleSerial.simpleSerialDevice( "COM15" )
dev.connect()

try:
    while True:
        frm = dev.recv()
        if frm:
            print( frm )
        time.sleep( 0.5 )
except:
    pass
finally:
    dev.disconnect()
```