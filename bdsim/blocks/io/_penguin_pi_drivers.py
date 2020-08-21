#!usr/bin/python3

import sys
import serial
import struct
import time
import os
import os.path
import threading
import queue
import datetime
import string
import re
import pickle
import logging

import traceback

# create a comms mutex
comms_mutex = threading.Lock()


#Communications Defines
STARTBYTE = 0x11 #Device Control 1

BIG_ENDIAN = True #NETWORK BYTE ORDER

DGRAM_MAX_LENGTH = 10 #bytes

CRC_8_POLY = 0x97

debug_comms = False
debug_comms = True


symbols = os.path.join(os.path.dirname(__file__), 'atmel-symbols.pickle')
try:
    with open( symbols, 'rb') as file:
        atmel_symbols = pickle.Unpickler(file).load();
except:
    logging.critical("can't load Atmel symbol table: " + symbols)
    sys.exit(1)

class UART(object):
    """Setup UART comunication between the raspberry pi and the microcontroler
    """
    def __init__(self, port='/dev/serial0', baud=115200):

        try:
            args = {
                    "port" :     port,
                    "baudrate" : baud,
                    "parity" :   serial.PARITY_NONE,
                    "stopbits" : serial.STOPBITS_ONE,
                    "bytesize" : serial.EIGHTBITS,
                    "timeout" :  1,
                    "exclusive" : True      # expect PySerial 3.3 or newer
                    };

            self.ser = serial.Serial( **args)
        except serial.serialutil.SerialException:
            # somebody else has the port open, give up now
            logging.critical("can't acquire exclusive access to communications port")
            sys.exit(1)

        self.queue = queue.Queue()
        self.receive_thread = threading.Thread(target=self.uart_recv, daemon=True)
        self.close_event = threading.Event()

    def start(self):
        """Start UART comunication between the raspberry pi and the
        microcontroler
        """
        #opens serial interface and starts recieve handler
        if self.ser.isOpen() is False:
            self.ser.open()

        #reset the buffers
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        #display that connection is started
        logging.info("Communicating on " + self.ser.name + " at " + str(self.ser.baudrate) + " " + str(self.ser.bytesize) + " " + self.ser.parity + " " + str(self.ser.stopbits))

        #start the recive thread
        self.receive_thread.start()

    def stop(self):
        '''Close the comunication between the raspberry pi and the
        microcontroler
        '''
        self.close_event.set()
        self.receive_thread.join()
        self.ser.close()
        self.ser.__del__()

    def flush(self):
        '''flushes input and output buffer, clears queue
        '''
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def putcs(self, dgram):
        '''function: prepends startbyte and puts datagram into write buffer
        '''
        dgram = (struct.pack('!B', STARTBYTE)) + dgram
        self.ser.write(dgram)
        #print(str(datetime.datetime.now())+": DGRAM: ad=0x%02x op=0x%02x" % (dgram[2], dgram[3]) )    ;
    def puts(self, s):
        self.ser.write(s.encode('utf-8'))

    def uart_recv(self):
        '''thread: receives command packets, and prints other messages
        '''
        startLine = True;
        while not self.close_event.is_set():
            try:
                # blocking read on first byte
                byte = self.ser.read(size=1)
                if len(byte) == 0:
                    continue;
                if ord(byte) == 0:
                    continue
                elif ord(byte) == STARTBYTE:
                    # we have a packet start, read the rest

                    paylen = self.ser.read(size=1)  # get the length
                    paylenint = ord(paylen)

                    dgram = self.ser.read(paylenint-1)  # read the rest
                    if len(dgram) != paylenint-1:
                        logging.error('short read', len(dgram), paylenint-1)

                    dgram = paylen + dgram   # datagram is length + the rest

                    # remove the crc byte
                    crcDgram = dgram[-1]
                    dgram = dgram[:-1]

                    #run crcCalc to ensure correct data
                    crcCalc = crc8(dgram, paylenint-1)
                    if crcCalc == crcDgram:
                        # valid CRC, put the datagram into the queue
                        self.queue.put(dgram)
                    else:
                        # bad CRC, print some diagnostics
                        logging.error("CRC Failed ", hex(crcCalc), " received ", hex(crcDgram), datagram2str(dgram));
                        self.queue.put(None)
                else: 
                    # text from the Atmel, perhaps an error message
                    if ord(byte) == 0x0a:
                        # it's a linefeed
                        print("")   # print the LF
                        startLine = True;  # indicate a new line is coming
                    else:
                        if startLine:
                            # print a timestamped message
                            print(str(datetime.datetime.now())+": ", end="");
                            startLine = False;
                        print(chr(ord(byte)), end="")
                            
            except serial.SerialException:
                logging.error("--- caught serial port error")

#create UART object
uart = UART("/dev/serial0", 115200)


def init():
    '''Initlise the UART object
    '''
    time.sleep(0.5)
    uart.start()

def close():
    '''Close the UART object
    '''
    stop_all()
    time.sleep(1)
    uart.stop()
    logging.info("UART stopped and closed")


def crc8(word, length):
    '''cyclic redundancy check
    '''
    crc = 0
    for i in range(0, length):
        crc = crc ^ word[i]
        for j in range(0, 8):
            if crc & 1:
                crc = (crc >> 1) ^ CRC_8_POLY
            else:
                crc =  (crc >> 1)
    return crc


def datagram2str(bin):
    return ".".join(hex(n) for n in bin)

re_type = re.compile(r"""(?P<t>[a-z0-9]+)  # type
                 (\[
                    (?P<d>[0-9])   # optional dimension
                 \])?
                 """, re.VERBOSE)

def get_struct_format(type):
    if type:
        m = re_type.match(type)

        # get the dimension
        if m.groupdict()['d']:
            n = int(m.groupdict()['d'])
        else:
            n = 1
        paytype = m.groupdict()['t']

        if paytype == 'char' or paytype == 'int8':
            format = 'b'
        elif paytype == 'uchar' or paytype== 'uint8':
            format = 'B'
        elif paytype == 'int16':
            format = 'h'
        elif paytype == 'uint16':
            format = 'H'
        elif paytype == 'int32':
            format = 'i'
        elif paytype == 'uint32':
            format = 'I'
        elif paytype == 'float':
            format = 'f'
        else:
            raise NameError('bad type', type)

        return n*format
    else:
        return ''

def send_datagram(address, opCode, payload=None, paytype='', rxtype=''):
    '''Create and send the datagram to sent to the microcontroler
    '''

    # convert strings to numeric values for the Atmel
    if not address in atmel_symbols:
        print("address symbol %s not defined" % address, file=sys.stderr);
        sys.exit(1)
    address = atmel_symbols[address]

    if not opCode in atmel_symbols:
        print("opcode symbol %s not defined" % opCode, file=sys.stderr);
        sys.exit(1)
    opCode = atmel_symbols[opCode]

    # turn the payload type into a format string for struct.pack
    format = get_struct_format(paytype)

    # if the args are a list, append that to the address and opcode
    args = [address, opCode]
    if payload is not None:
        if type(payload) is list:
            args.extend(payload)
        else:
            args.append(payload)
    # convert to binary string
    dgram = struct.pack('!BB'+format, *args)

    # build up the rest of the datagram
    length = len(dgram) + 2
    dgram = (struct.pack("!B", length)) + dgram
    crc = crc8(dgram, length-1)
    dgram = dgram + (struct.pack("!B", crc))

    if debug_comms:
        logging.debug(datagram2str(dgram))


    with comms_mutex:
        # the following code can be executed by only one thread at a time
        uart.putcs(dgram) # send the message to PPI

        # is a response expected?
        if opCode & 0x80:
            # yes, get the response

            # check that rxtype is given
            if not rxtype:
                raise NameError("no receive data type specified");

            # attempt to get message from the queue
            try:
                dgram = uart.queue.get(timeout=0.2)
            except queue.Empty:
                print('-- queue read times out')
                # some error occurred, flag it
                return None

            if dgram:
                result = extract_payload(dgram, address, opCode, rxtype)
                if result is None:
                    print('-- error in extract_payload')
                if len(result) == 1:
                    result = result[0]
            else:
                # datagram is None, indicates failure at the packet RX end
                print('-- null entry in queue')

            uart.queue.task_done()

            return result
        else:
            return

def puts(s):
    '''Send non-packet text to the PPI board
    '''
    with comms_mutex:
        uart.puts(s)

def extract_payload(bin, address, opcode, paytype):
    '''Extracts payload from the microcontroler
       return is int or float
    '''

    format = get_struct_format(paytype)

    if bin[1] == address and bin[2] == opcode:
        # check that address and opcode match
        ret = struct.unpack('!'+format, bin[3:])
        return ret
    else:
        print("address/opcode mismatch:", bin, " expected ", [address,opcode], datagram2str(bin))
        return None

### --- Device Classes --- ###
'''
Motor Object
    Control motors by setting the degrees to the desired distance: make conversion from meters
    to degrees in your own code
'''
class Motor(object):
    '''Motor class used with the penguin pi
    '''

    #creates and instance of Motor
    def __init__(self, address):
        self.address = address
        #this might be superflous...
        self.speedDPS = 0
        self.degrees = 0
        self.dir = 0
        self.encoderMode = 1
        self.gainP = 0
        self.gainI = 0
        self.gainD = 0

#SETTERS
    def set_velocity(self, velocity):
        self.velocity = velocity
        send_datagram(self.address, 'MOTOR_SET_VEL', velocity, 'int16')

    def set_encoder_mode(self, mode):
        self.encoderMode = mode
        send_datagram(self.address, 'MOTOR_SET_ENC_MODE', mode, 'uint8')

    def set_kvp(self, kvp):
        self.Kvp = kvp
        send_datagram(self.address, 'MOTOR_SET_KVP', kvp, 'int16')

    def set_kvi(self, kvi):
        self.Kvi = kvi
        send_datagram(self.address, 'MOTOR_SET_KVI', kvi, 'int16')

#GETTERS
    def get_velocity(self):
        self.velocity = send_datagram(self.address, 'MOTOR_GET_VEL', rxtype='int16')
        return self.velocity

    def get_encoder(self):
        self.encoder = send_datagram(self.address, 'MOTOR_GET_ENC', rxtype='int16')
        return self.encoder

    def get_encoder_mode(self):
        self.encoderMode = send_datagram(self.address, 'MOTOR_GET_ENC_MODE', rxtype='uint8')
    def get_kvp(self):
        self.kvp = send_datagram(self.address, 'MOTOR_GET_KVP', rxtype='int16')
        return self.kvp

    def get_kvi(self):
        self.kvi = send_datagram(self.address, 'MOTOR_GET_KVI', rxtype='int16')
        return self.kvi

    def get_all(self):
        self.get_velocity()
        self.get_encoder()
        self.get_encoder_mode()

'''Multi Object
    Access both motors at once
'''

class Multi(object):
    def __init__(self, address):
        self.address = address;

    def set_velocity(velocity):
        send_datagram(self.address, 'MULTI_SET_VEL', velocity, 'int8[2]')
        self.velocity = velocity

    def get_encoders():
        encoders = send_datagram(self.address, 'MULTI_GET_ENC', rxtype='uint16[2]')
        self.encoders = encoders;
        return encoders

    def setget_velocity_encoders(self, velocity):
        encoders = send_datagram(self.address, 'MULTI_SET_SPEED_GET_ENC', velocity, 'int8[2]', rxtype='uint16[2]')
        self.encoders = encoders;
        return encoders

    def stop_all(self):
        send_datagram(self.address, 'MULTI_ALL_STOP')

    def clear_data(self):
        send_datagram(self.address, 'MULTI_CLEAR_DATA')


'''
Servo Object
    position alters the servos output shaft, between the minimum and maximum ranges
    position is clipped to max/min on the ATMEGA side
    neutral position is typically 90 (degrees), in a range of 0-180 (degrees)
    #PWM range can be adjusted to allow for servos with a wider range of control
'''
class Servo(object):

    def __init__(self, address):
        self.address = address
        self.state = 0
        self.position = 90
        self.minRange = 0
        self.maxRange = 180
        self.minPWMRange = 1500
        self.maxPWMRange = 3000

#SETTERS
    def set_position(self, position):
        self.position = position
        send_datagram(self.address, 'SERVO_SET_POSITION', position, 'int16')

    def set_state(self, state):
        self.state = state
        send_datagram(self.address, 'SERVO_SET_STATE', state, 'uint8')

    def set_range(self, minimum, maximum):
        self.minRange = minimum
        self.maxRange = maximum
        send_datagram(self.address, 'SERVO_SET_MIN_RANGE', minimum, 'int16')
        send_datagram(self.address, 'SERVO_SET_MAX_RANGE', maximum, 'int16')

#GETTERS
    def get_position(self):
        self.position = send_datagram(self.address, 'SERVO_GET_POSITION', rxtype='int16')
        return self.position

    def get_state(self):
        self.state = send_datagram(self.address, 'SERVO_GET_STATE', rxtype='uint8')
        return self.state

    def get_range(self):
        self.minRange = send_datagram(self.address, 'SERVO_GET_MIN_RANGE', rxtype='int16')
        self.maxRange = send_datagram(self.address, 'SERVO_GET_MAX_RANGE', rxtype='int16')

        return self.minRange, self.maxRange

    def get_PWM_range(self):
        self.minPWMRange = send_datagram(self.address, 'SERVO_GET_MIN_PWM', rxtype='int16')
        self.maxPWMRange = send_datagram(self.address, 'SERVO_GET_MAX_PWM', rxtype='int16')

        return self.minPWMRange, self.maxPWMRange

    def get_all(self):
        self.get_position()
        self.get_state()
        self.get_range()
        self.get_PWM_range()

'''
LED object
    state overrides brightness
    brightness is a percentage
    count is a multiplier of 21us, and determines how long the led is lit for
'''
class LED(object):
    def __init__(self, address):
        self.address = address
        self.state = 0
        self.brightness = 0
        self.count = 0
#SETTERS
    def set_state(self, state):
        self.state = state
        send_datagram(self.address, 'LED_SET_STATE', state, 'uint8')

    def set_count(self, count):
        self.count = count
        send_datagram(self.address, 'LED_SET_COUNT', count, 'uint8')

#GETTERS
    def get_state(self):
        self.state = send_datagram(self.address, 'LED_GET_STATE', rxtype='uint8')
        return self.state

'''
Display object
    dual digit 7 segment display
    can set each digit individualy: will override the value
'''
class Display(object):
    def __init__(self, address):
        self.address = address
        self.value = 0
        self.digit0 = 0
        self.digit1 = 0
        self.mode = 0    # hex
#SETTERS
    def set_value(self, value):
        self.value = value
        if self.mode == 2 and value < 0:
            # signed mode for a negative number, form the 2's complement
            value = value + 0xff + 1;
        send_datagram(self.address, DISPLAY_SET_VALUE, value, 'uchar')

    def set_digit0(self, digit0):
        self.digit0 = digit0
        send_datagram(self.address, DISPLAY_SET_DIGIT_0, digit0, 'uint8')

    def set_digit1(self, digit1):
        self.digit1 = digit1
        send_datagram(self.address, DISPLAY_SET_DIGIT_1, digit1, 'uint8')

    def set_mode(self, mode):
        if mode == 'x':     # hex %02x
            self.mode = 0
        elif mode == 'u':   # decimal %2d
            self.mode = 1
        elif mode == 'd':   # signed decimal %1d
            self.mode = 2
        else:
            print("ERROR: Incompatible Payload Type Defined. (Python)")
            raise NameError('Debug')
            return 0
        send_datagram(self.address, DISPLAY_SET_MODE, self.mode, 'uint8')

#GETTERS
    def get_value(self):
        self.value = send_datagram(self.address, DISPLAY_GET_VALUE, rxtype='uint8')
        return self.value

    def get_digit0(self):
        self.digit0 = send_datagram(self.address, DISPLAY_GET_DIGIT_0, rxtype='uint8')
        return self.digit0

    def get_digit1(self):
        self.digit1 = send_datagram(self.address, DISPLAY_GET_DIGIT_1, rxtype='uint8')
        return self.digit1

    def get_mode(self):
        self.mode = send_datagram(self.address, DISPLAY_GET_MODE, rxtype='uint8')
        return self.mode


    def get_all(self):
        self.get_value()
        self.get_digit0()
        self.get_digit1()

'''
Button Object
    Controls the behaviour of the onboard buttons
'''
class Button(object):
    def __init__(self, address):
        self.address = address
        self.program_mode = 0
        self.pin_mode = 0

#SETTERS
    def set_program_mode(self, program_mode):
        self.program_mode = program_mode
        send_datagram(self.address, BUTTON_SET_PROGRAM_MODE, program_mode, 'uint8')

    def set_pin_mode(self, pin_mode):
        self.pin_mode = pin_mode
        send_datagram(self.address, BUTTON_SET_PIN_MODE, pin_mode, 'uint8')

#GETTERS
    def get_program_mode(self):
        self.program_mode = send_datagram(self.address, BUTTON_GET_PROGRAM_MODE, rxtype='uint8')
        return self.program_mode

    def get_pin_mode(self):
        self.pin_mode = send_datagram(self.address, BUTTON_GET_PIN_MODE, rxtype='uint8')
        return self.pin_mode

    def get_all(self):
        self.get_program_mode()
        self.get_pin_mode()


'''
ADC Object
    used to retrieve ADC readings from the atmega.
    currently the battery voltage and current are being monitored
    these are AD_ADC_V and AD_ADC_C respectively.
'''
class AnalogIn(object):

    def __init__(self, address):
        self.address = address
        self.raw = 0
        self.value = 0
        self.scale = 0

#SETTERS
    def set_scale(self, scale):
        self.scale = scale
        send_datagram(self.address, 'ADC_SET_SCALE', scale, 'float')

    def set_pole(self, pole):
        self.pole = pole
        send_datagram(self.address, 'ADC_SET_POLE', pole, 'float')

#GETTERS
    def get_scale(self):
        self.scale = send_datagram(self.address, 'ADC_GET_SCALE', rxtype='float')
        return self.scale

    def get_value(self):
        self.value = send_datagram(self.address, 'ADC_GET_VALUE', rxtype='float')
        return self.value

    def get_smooth(self):
        self.smooth = send_datagram(self.address, 'ADC_GET_SMOOTH', rxtype='float')
        return self.smooth

    def get_pole(self):
        self.pole = send_datagram(self.address, 'ADC_GET_POLE', rxtype='float')
        return self.pole

    def get_all(self):
        self.get_scale()
        self.get_value()
        self.get_smooth()
		
'''
HAT Object
    interface with the custom hat board
'''
class Hat(object):
    def __init__(self, address):
        self.address = address
        self.ip_eth   = 0
        self.ip_wlan  = 0

#SETTERS
    def set_screen(self, screen):
        send_datagram(self.address, 'HAT_SET_SCREEN', screen, 'uint8')

    def set_ledarray(self, ledarray):
        send_datagram(self.address, 'HAT_SET_LEDARRAY', ledarray, 'uint16')

    def set_ip_eth( self, ipaddr ):
        if isinstance(ipaddr,list):
            octets = ipaddr
        else:
            octets = [int(x) for x in ipaddr.split('.')]
        send_datagram(self.address, 'HAT_SET_IP_ETH', octets, 'uint8[4]')

    def set_ip_wlan( self, ipaddr ):
        if isinstance(ipaddr,list):
            octets = ipaddr
        else:
            octets = [int(x) for x in ipaddr.split('.')]
        send_datagram(self.address, 'HAT_SET_IP_WLAN', octets, 'uint8[4]')

    def set_mac_wlan( self, mac ):
        if isinstance(mac,list):
            octets = mac
        else:
            octets = [int(x) for x in mac.split(':')]
        send_datagram(self.address, 'HAT_SET_MAC_WLAN', octets, 'uint8[6]')

#GETTERS
    def get_dip(self):
        '''Read the DIP switches.  
           Switch 1 is the high-order bit.`
           ON means 1.
        '''
        dip = send_datagram(self.address, 'HAT_GET_DIP', rxtype='uint8') & 0xff
        return dip

    def get_button(self):
        return send_datagram(self.address, 'HAT_GET_BUTTON', rxtype='uint8') & 0xff

    def get_ledarray(self):
        return send_datagram(self.address, 'HAT_GET_LEDARRAY', rxtype='uint16')


logging.basicConfig(format='%(asctime)s %(levelname)s  %(message)s', level=logging.INFO)
