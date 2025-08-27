from ctypes import *
from dwfconstants import *  # Import all constants from dwfconstants
import time
from base_digilent import BaseDigilentDevice

class AnalogDiscovery3(BaseDigilentDevice):
    def __init__(self):
        super().__init__()
        self.model = "Analog Discovery 3"
        self.AI = AI(self)
        self.AO = AO(self)

    # configure the DIO pins for I2C communication
    def configure_i2c(self, do_scl_index, do_sda_index, i2c_clock_frequency):
        iNak = c_int()
        self.dwf.FDwfDigitalI2cReset()
        self.dwf.FDwfDigitalI2cStretchSet(self.hdwf, c_int(1)) # clock stretching
        self.dwf.FDwfDigitalI2cRateSet(self.hdwf, c_double(i2c_clock_frequency)) # 400 kHz
        self.dwf.FDwfDigitalI2cSclSet(self.hdwf, c_int(do_scl_index)) # SCL 
        self.dwf.FDwfDigitalI2cSdaSet(self.hdwf, c_int(do_sda_index)) # SDA 
        # dwf.FDwfDigitalI2cStretchSet(hdwf, c_int(1)) # clock stretching
        self.dwf.FDwfDigitalI2cClear(self.hdwf, byref(iNak))
        
        if iNak.value == 0:
            #print("Reading I2C bus error. Check the pull-ups.")
            return False
        time.sleep(1)
        return True
       
class AI():
    def __init__(self, ad3: AnalogDiscovery3):
        self._ad3 = ad3                
    
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
        self._ad3.dwf.FDwfAnalogInFrequencySet(self._ad3.hdwf, c_double(sampling_frequency))
        self._ad3.dwf.FDwfAnalogInBufferSizeSet(self._ad3.hdwf, c_int(n_samples))
        self._ad3.dwf.FDwfAnalogInChannelEnableSet(self._ad3.hdwf, c_int(channel), c_int(True))
        self._ad3.dwf.FDwfAnalogInChannelRangeSet(self._ad3.hdwf, c_int(channel), c_double(range))
        self._ad3.dwf.FDwfAnalogInChannelFilterSet(self._ad3.hdwf, c_int(channel), filterDecimate)

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
        self._ad3.dwf.FDwfAnalogInConfigure(self._ad3.hdwf, c_int(1), c_int(1))

        return True

    def stop_scope(self):
        """
        Stop the oscilloscope
        """
        self._ad3.dwf.FDwfAnalogInConfigure(self._ad3.hdwf, c_int(0), c_int(0))

        return True

    def read_single_scope_1ch(self, channel=0):
        """
        Wait for the oscilloscope to finish capturing data
        """

        sts = c_byte()
        rgdSamples = (c_double * self._numSamples)()

        while True:
            self._ad3.dwf.FDwfAnalogInStatus(self._ad3.hdwf, c_int(1), byref(sts))
            if sts.value == DwfStateDone.value :
                break
            time.sleep(0.1)
            
        self._ad3.dwf.FDwfAnalogInStatusData(self._ad3.hdwf, channel, rgdSamples, self._numSamples) # get data
        
        return rgdSamples

    def read_single_scope_2ch(self):
        """
        Wait for the oscilloscope to finish capturing data
        """

        sts = c_byte()
        rgdSamples1 = (c_double * self._numSamples)()
        rgdSamples2 = (c_double * self._numSamples)()

        while True:
            self._ad3.dwf.FDwfAnalogInStatus(self._ad3.hdwf, c_int(1), byref(sts))
            if sts.value == DwfStateDone.value :
                break
            time.sleep(0.1)

        self._ad3.dwf.FDwfAnalogInStatusData(self._ad3.hdwf, 0, rgdSamples1, self._numSamples) # get data
        self._ad3.dwf.FDwfAnalogInStatusData(self._ad3.hdwf, 1, rgdSamples2, self._numSamples) # get data

        return rgdSamples1, rgdSamples2

class AO():
    def __init__(self, ad3: AnalogDiscovery3):
        self._ad3 = ad3

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
        self._ad3.dwf.FDwfAnalogOutNodeEnableSet(self._ad3.hdwf, channel, AnalogOutNodeCarrier, c_bool(True))
        # set function type
        self._ad3.dwf.FDwfAnalogOutNodeFunctionSet(self._ad3.hdwf, channel, AnalogOutNodeCarrier, function)
        # load data if the function type is custom
        if function == funcCustom:
            data_length = len(data)
            buffer = (c_double * data_length)()
            for index in range(0, len(buffer)):
                buffer[index] = c_double(data[index])
            self._ad3.dwf.FDwfAnalogOutNodeDataSet(self._ad3.hdwf, channel, AnalogOutNodeCarrier, buffer, c_int(data_length))

        # set frequency
        self._ad3.dwf.FDwfAnalogOutNodeFrequencySet(self._ad3.hdwf, channel, AnalogOutNodeCarrier, c_double(frequency))
        # set amplitude or DC voltage
        self._ad3.dwf.FDwfAnalogOutNodeAmplitudeSet(self._ad3.hdwf, channel, AnalogOutNodeCarrier, c_double(amplitude))
        # set offset
        self._ad3.dwf.FDwfAnalogOutNodeOffsetSet(self._ad3.hdwf, channel, AnalogOutNodeCarrier, c_double(offset))
        # set symmetry
        self._ad3.dwf.FDwfAnalogOutNodeSymmetrySet(self._ad3.hdwf, channel, AnalogOutNodeCarrier, c_double(symmetry))
        # set running time limit
        self._ad3.dwf.FDwfAnalogOutRunSet(self._ad3.hdwf, channel, c_double(run_time))
        # set wait time before start
        self._ad3.dwf.FDwfAnalogOutWaitSet(self._ad3.hdwf, channel, c_double(wait))
        # set number of repeating cycles
        self._ad3.dwf.FDwfAnalogOutRepeatSet(self._ad3.hdwf, channel, c_int(repeat))
        # start
        self._ad3.dwf.FDwfAnalogOutConfigure(self._ad3.hdwf, channel, c_bool(True))
        return
    
    def disable_fgen(self, channel=-1):
        """
        Disables the waveform generator
        
        channel: -1 for all channels, 0 for first channel, 1 for second channel
        """
        self._ad3.dwf.FDwfAnalogOutConfigure(self._ad3.hdwf, c_int(channel), c_int(False))

        return True
    

if __name__ == "__main__":
    AD3 = AnalogDiscovery3()
    AD3.open_device_default()
    # AD3.AO.generate_pattern_fgen(2, funcSine, 0, 1000, 1)
    input("Press Enter to continue...")
    AD3.close_device()