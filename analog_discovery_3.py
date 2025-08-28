from ctypes import *
from dwfconstants import *  # Import all constants from dwfconstants
import time
from base_digilent import BaseDigilentDevice
from collections import namedtuple

### BLAH BLAH BLAH

class AnalogDiscovery3(BaseDigilentDevice):
    def __init__(self):
        super().__init__()

        self.name = ""
        self.model = "Analog Discovery 3"

        self.AI = AI(self)
        self.AO = AO(self)
        self.I2C = I2C(self)

        self.logger = None

    def LogPropertySet(func):
        def wrapper(*args, **kwargs):
            obj = args[0]
            val = args[1]

            logger = obj._ad3.logger

            if logger is not None:
                logger.debug(f"Setting {obj._ad3.name}{obj.name}.{func.__name__} to {val}.")
            
            func(*args, **kwargs)
            
        return wrapper


       
class AI():
    def __init__(self, ad3: AnalogDiscovery3):
        self._ad3 = ad3       
        self._dwf = type(ad3)._dwf       # API Interface ???         
    
    def configure_scope_single(self, channel, sampling_frequency, range=25, n_samples=16384):
        """
        Configure the oscilloscope for single shot mode

        channel: 0 for first channel, 1 for second channel, -1 for both channels

        coupling: 0 for DC, 1 for AC, 2 for GND

        range: range in volts. 100mv-25V

        offset: offset in volts

        samplingFrequncy: in Hz

        n_samples: number of samples to capture, 16384 max when using two channels, 32768 max when using one channel
        """
        self._dwf.FDwfAnalogInFrequencySet(self._ad3._hdwf, c_double(sampling_frequency))
        self._dwf.FDwfAnalogInBufferSizeSet(self._ad3._hdwf, c_int(n_samples))
        self._dwf.FDwfAnalogInChannelEnableSet(self._ad3._hdwf, c_int(channel), c_int(True))
        self._dwf.FDwfAnalogInChannelRangeSet(self._ad3._hdwf, c_int(channel), c_double(range))
        self._dwf.FDwfAnalogInChannelFilterSet(self._ad3._hdwf, c_int(channel), filterDecimate)

        self._numSamples = n_samples
        self._samplingFrequency = sampling_frequency

        return True

    def scope_capture_1ch_single(self, channel=0):
        """
        Capture the oscilloscope data

        Returns: c type of doubles
        """
        self.start_scope()

        return self.read_single_scope_1ch(channel)

    def scope_capture_2ch_single(self):
        """
        Captures both channels of oscilloscope data

        Returns: c type of doubles, c type of doubles
        """
        self.start_scope()
        data1, data2 = self.read_single_scope_2ch()
        return data1, data2

    def start_scope(self):
        """
        Start the oscilloscope
        """
        self._dwf.FDwfAnalogInConfigure(self._ad3._hdwf, c_int(1), c_int(1))

        return True

    def stop_scope(self):
        """
        Stop the oscilloscope
        """
        self._dwf.FDwfAnalogInConfigure(self._ad3._hdwf, c_int(0), c_int(0))

        return True

    def read_single_scope_1ch(self, channel=0):
        """
        Wait for the oscilloscope to finish capturing data
        """

        sts = c_byte()
        rgdSamples = (c_double * self._numSamples)()

        while True:
            self._dwf.FDwfAnalogInStatus(self._ad3._hdwf, c_int(1), byref(sts))
            if sts.value == DwfStateDone.value :
                break
            time.sleep(0.1)
            
        self._dwf.FDwfAnalogInStatusData(self._ad3._hdwf, channel, rgdSamples, self._numSamples) # get data
        
        return rgdSamples

    def read_single_scope_2ch(self):
        """
        Wait for the oscilloscope to finish capturing data
        """

        sts = c_byte()
        rgdSamples1 = (c_double * self._numSamples)()
        rgdSamples2 = (c_double * self._numSamples)()

        while True:
            self._dwf.FDwfAnalogInStatus(self._ad3._hdwf, c_int(1), byref(sts))
            if sts.value == DwfStateDone.value :
                break
            time.sleep(0.1)

        self._dwf.FDwfAnalogInStatusData(self._ad3._hdwf, 0, rgdSamples1, self._numSamples) # get data
        self._dwf.FDwfAnalogInStatusData(self._ad3._hdwf, 1, rgdSamples2, self._numSamples) # get data

        return rgdSamples1, rgdSamples2

class AO():
    def __init__(self, ad3: AnalogDiscovery3):
        self._ad3 = ad3
        self._dwf = type(ad3)._dwf       # API Interface ???    

    # AD3 - Function Generator 
    def generate_pattern_fgen(self, channel, function, offset, frequency=2e06, amplitude=2, symmetry=50, wait=0, run_time=0, repeat=0, data=[]):
        """
            generate an analog signal
            parameters: - device data
                        - the selected wavegen channel (0 or 1)
                        - function - possible: custom, sine, square, triangle, noise, ds, pulse, trapezium, sine_power, ramp_up, ramp_down
                        - offset voltage in Volts
                        - frequency in Hz, default is 1KHz
                        - amplitude in Volts, default is 1V
                        - signal symmetry in percentage, default is 50%
                        - wait time in seconds, default is 0s
                        - run time in seconds, default is infinite (0)
                        - repeat count, default is infinite (0)
                        - data - list of voltages, used only if function=custom, default is empty
        """
        # enable channel
        channel = c_int(channel)
        self._dwf.FDwfAnalogOutNodeEnableSet(self._ad3._hdwf, channel, AnalogOutNodeCarrier, c_bool(True))
        # set function type
        self._dwf.FDwfAnalogOutNodeFunctionSet(self._ad3._hdwf, channel, AnalogOutNodeCarrier, function)
        # load data if the function type is custom
        if function == funcCustom:
            data_length = len(data)
            buffer = (c_double * data_length)()
            for index in range(0, len(buffer)):
                buffer[index] = c_double(data[index])
            self._dwf.FDwfAnalogOutNodeDataSet(self._ad3._hdwf, channel, AnalogOutNodeCarrier, buffer, c_int(data_length))

        # set frequency
        self._dwf.FDwfAnalogOutNodeFrequencySet(self._ad3._hdwf, channel, AnalogOutNodeCarrier, c_double(frequency))
        # set amplitude or DC voltage
        self._dwf.FDwfAnalogOutNodeAmplitudeSet(self._ad3._hdwf, channel, AnalogOutNodeCarrier, c_double(amplitude))
        # set offset
        self._dwf.FDwfAnalogOutNodeOffsetSet(self._ad3._hdwf, channel, AnalogOutNodeCarrier, c_double(offset))
        # set symmetry
        self._dwf.FDwfAnalogOutNodeSymmetrySet(self._ad3._hdwf, channel, AnalogOutNodeCarrier, c_double(symmetry))
        # set running time limit
        self._dwf.FDwfAnalogOutRunSet(self._ad3._hdwf, channel, c_double(run_time))
        # set wait time before start
        self._dwf.FDwfAnalogOutWaitSet(self._ad3._hdwf, channel, c_double(wait))
        # set number of repeating cycles
        self._dwf.FDwfAnalogOutRepeatSet(self._ad3._hdwf, channel, c_int(repeat))
        # start
        self._dwf.FDwfAnalogOutConfigure(self._ad3._hdwf, channel, c_int(1))
        return
    
    def disable_fgen(self, channel=-1):
        """
        Disables the waveform generator
        
        channel: -1 for all channels, 0 for first channel, 1 for second channel
        """
        self._dwf.FDwfAnalogOutConfigure(self._ad3._hdwf, c_int(channel), c_int(False))

        return True
    

    

class I2C():
    #region Properties

    #region Rate
    @property
    def Rate(self) -> float:
        return self._rate
    
    @Rate.setter
    @AnalogDiscovery3.LogPropertySet
    def Rate(self, bitRate: float):
        self._rate = bitRate

        rate = c_double(bitRate)
        self._dwf.FDwfDigitalI2cRateSet(self._ad3._hdwf, rate)
    #endregion

    #region Timeout
    @property
    def Timeout(self) -> float:
        return self._timeout
    
    @Timeout.setter
    @AnalogDiscovery3.LogPropertySet
    def Timeout(self, duration_sec: float):
        self._timeout = duration_sec

        timeout_sec = c_double(duration_sec)
        self._dwf.FDwfDigitalI2cTimeoutSet(self._ad3._hdwf, timeout_sec)
    #endregion

    #region EnNakOnRead
    @property
    def EnNakOnRead(self) -> bool:
        return self._enNakOnRead
    
    @EnNakOnRead.setter
    @AnalogDiscovery3.LogPropertySet
    def EnNakOnRead(self, value: bool):
        self._enNakOnRead = value

        val = c_int(value)
        self._dwf.FDwfDigitalI2cReadNakSet(self._ad3._hdwf, val)
    #endregion

    #region EnableClockStretching
    @property
    def EnableClockStretching(self) -> bool:
        return self._enClockStretching
    
    @EnableClockStretching.setter
    @AnalogDiscovery3.LogPropertySet
    def EnableClockStretching(self, value: bool):
        self._enClockStretching = value

        val = c_int(value)
        self._dwf.FDwfDigitalI2cStretchSet(self._ad3._hdwf, val)
    #endregion

    #region SCL
    @property
    def SCL(self) -> int:
        return self._scl
    
    @SCL.setter
    @AnalogDiscovery3.LogPropertySet
    def SCL(self, dioChannel: int):
        self._scl = dioChannel

        channel = c_int(dioChannel)
        self._dwf.FDwfDigitalI2cSclSet(self._ad3._hdwf, channel)
    #endregion

    #region SDA
    @property
    def SDA(self) -> int:
        return self._sda
    
    @SDA.setter
    @AnalogDiscovery3.LogPropertySet
    def SDA(self, dioChannel: int):
        self._sda = dioChannel
        
        channel = c_int(dioChannel)
        self._dwf.FDwfDigitalI2cSdaSet(self._ad3._hdwf, channel)
    #endregion



    #endregion

    I2cMessage = namedtuple('I2cMessage', ['ACK', 'Readback', 'Details'])

    def __init__(self, ad3: AnalogDiscovery3):
        self.name = "I2C"

        self._ad3 = ad3                 
        self._dwf = type(ad3)._dwf       # API Interface ???


        self._scl = None
        self._sda = None
        self._rate = None
        self._timeout = None
        self._enNakOnRead = None
        self._enClockStretching = None

    def LogI2C(func):
        def wrapper(*args, **kwargs):
            obj = args[0]
            logger = obj._ad3.logger

            i2cMessage = func(*args, **kwargs)

            if logger is not None:
                logger.debug(f"{obj._ad3.name}:\t{i2cMessage.Details}")
            
            return i2cMessage
        return wrapper


    def Reset(self):
        self._dwf.FDwfDigitalI2cReset(self._ad3._hdwf)
        self._scl = None
        self._sda = None
        self._rate  = None
        self._timeout = None
        self._enNakOnRead = None
        self._enClockStretching = None
    
    def Clear(self) -> bool:
        iNak = c_int()
        self._dwf.FDwfDigitalI2cClear(self._ad3._hdwf, byref(iNak))

        return bool(iNak)
    

    @LogI2C
    def Write(self, address: int, register: int = None, values: int | list[int] = None) -> I2cMessage:
        """I2C write.
            - Single
            - Repeated"""
        

        ## Exception handling
        if not isinstance(address, int):
            raise TypeError(f"Address must be an integer.")
        
        if not isinstance(register, (int | None)):
            raise TypeError(f"Register must be an integer or None.")
        
        if isinstance(values, list):
            if not all(isinstance(val, int) for val in values):
                raise TypeError("Values must be an integer, a list of integers, or None.")
        elif not isinstance(values, (int | None)):
            raise TypeError("Values must be an integer, a list of integers, or None.")
        

        ### Basic setup
        pNak = c_int()
        cAddress = c_ubyte(address)

        if register is None:
            cTx = c_int(0)
            rgTx = (cTx.value * c_ubyte)()

        else:
            if values is None:
                cTx = c_int(1)
                rgTx = (cTx.value * c_ubyte)(register)

            elif isinstance(values, int):
                cTx = c_int(2)
                rgTx = (cTx.value * c_ubyte)(register, values)

            elif isinstance(values, list):
                cTx = c_int(1 + len(values))
                rgTx = (cTx.value * c_ubyte)(register, *values)


        ### Perform the write
        self._dwf.FDwfDigitalI2cWrite(self._ad3._hdwf, cAddress, rgTx, cTx, byref(pNak))

        readback = None
        notAck = bool(pNak)
        ack = not notAck

        addressStr = f"0x{format(address, '02x')}"
        registerStr = "" if register is None else f":0x{format(register, '02x')}"
        if values is None:
            valuesStr = ""
        elif isinstance(values, int):
            valuesStr = f":0x{format(values, '02x')}"
        elif isinstance(values, list):
            valuesStr = ":" + ", ".join(f"0x{format(val, '02x')}" for val in values)

        if ack:
            textMsg = f"{addressStr}[W]{registerStr}{valuesStr}"
        else:
            textMsg = f"{addressStr}[W] (NAK){registerStr}"

        msg = self.I2cMessage(ack, readback, textMsg)
        return msg

    @LogI2C
    def Read(self, address: int, register: int, count=1) -> I2cMessage:
        """I2C Read
        - Single
        - Repeated"""


        ### Exception handling
        if not isinstance(address, int):
            raise TypeError(f"Address must be an integer.")
        if not isinstance(register, (int | None)):
            raise TypeError(f"Register must be an integer or None.")
        if count < 0:
            raise ArgumentError(f"Count must be greater than or equal to 0.")
        
        

        ### Basic setup
        pNak = c_int()
        cAddress = c_ubyte(address)

        ### Repeated start reads (https://www.i2c-bus.org/auto-increment/)
        if register is None:
            cTx = c_int(0)
            rgTx = (cTx.value * c_ubyte)()
        else:
            cTx = c_int(1)
            rgTx = (cTx.value * c_ubyte)(register)

        cRx = c_int(count)
        rgRx = (cRx.value * c_ubyte)()

        ### Write to the register and readback
        self._dwf.FDwfDigitalI2cWriteRead(self._ad3._hdwf, address, rgTx, cTx, rgRx, cRx, byref(pNak))

        readback = list(rgRx)
        notAck = bool(pNak)
        ack = not notAck

        addressStr = f"0x{format(address, '02x')}"
        registerStr = "" if register is None else f":0x{format(register, '02x')}"
        valuesStr = "" if readback is None else ":" + ", ".join(f"0x{format(val, '02x')}" for val in readback)

        if ack:
            textMsg = f"{addressStr}[R]{registerStr}{valuesStr}"
        else:
            textMsg = f"{addressStr}[R] (NAK){registerStr}"

        msg = self.I2cMessage(ack, readback, textMsg)
        return msg

    # configure the DIO pins for I2C communication
    def Configure(self, sclPin, sdaPin, clockFreq, enClkStretch):
        iNak = c_int()
        self.Reset()

        self.SCL = sclPin
        self.SDA = sdaPin
        self.Rate = clockFreq
        self.EnableClockStretching = enClkStretch

        isBusFree = self.Clear()
        
        return isBusFree


    def FindDevices(self, addresses: range = None):
        addresses = list(range(0, 0x7F)) if addresses is None else addresses
        addresses = [address << 1 for address in addresses]

        validAddresses = []
        for address in addresses:
            ack, readback, details = self.Write(address)

            if ack:
                validAddresses.append(address)

        return validAddresses




if __name__ == "__main__":
    AD3 = AnalogDiscovery3()
    AD3.open_by_default()
    # devices = AD3.I2C.FindDevices()
    AD3.close()