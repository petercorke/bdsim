This folder contains "drivers" for particular i/o hardware configurations.

Each file contains a set of class definitions which are imported in the normal
Python fashion, not dynamically as are most bdsim blocks.

| File | Purpose |
|------|---------|
|Firmata.py | analog and digital i/o for Arduino + Firmata |

Notes:

- For [Firmata](https://github.com/firmata/protocol) you need to load a Firmata sketch onto the Arduino.  
- For now the port and the baudrate (57600) are hardwired.  Perhaps the i/o system is initialized by a
  separate function, or options passed through BDRealTime.
- There are myriad Firmata variants, but StandardFirmata is provided as a built-in 
  example with the Arduino IDE and does digital and analog i/o.  It runs fine on a Uno.
- ConfigurableFirmata has more device options but needs to be installed, and its default
  baud rate is 115200.  It does not include quadrature encoders :(
- The Firmata interface is [pyfirmata](https://github.com/tino/pyFirmata), old but quite solid and efficient.