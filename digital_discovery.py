from ctypes import *
from base_digilent import BaseDigilentDevice
from dwfconstants import *


class DigitalDiscovery(BaseDigilentDevice):
    def __init__(self):
        super().__init__()
        self.model = "Digital Discovery"

        ### Temporary 
        self._dwf = type(self)._dwf
        


    # def configure(self):
    #     self._dwf.configure_digital_input(self.device_handle)

    # def start_acquisition(self):
    #     self._dwf.start_digital_acquisition(self.device_handle)

    # def read_data(self):
    #     return self._dwf.read_digital_data(self.device_handle)

    # def close(self):
    #     self._dwf.close(self.device_handle)


    # configure the Digital Out for clock generation
    def configureDO_clock(self, clock_rate, do_pin, duty_cycle=50):
        hzSys = c_double()
        dividerGet = c_uint()
        self._dwf.FDwfDigitalOutInternalClockInfo(self._hdwf, byref(hzSys))

        print(f'Clock rate: {clock_rate} Hz, internal clock: {hzSys.value} Hz')

        self._dwf.FDwfDigitalOutEnableSet(self._hdwf, c_int(do_pin), c_int(1))
        self._dwf.FDwfDigitalOutDividerSet(self._hdwf, c_int(do_pin), c_int(int(hzSys.value/clock_rate/2)))
        self._dwf.FDwfDigitalOutCounterSet(self._hdwf, c_int(do_pin), c_int(1), c_int(1))
        
        print ("divider = "+str(int(hzSys.value/clock_rate/2)))

    # configure the  Digital Input for data acquisition
    def configureDI_and_DAQ(self, digilent_dd_sample_rate, samples_to_acquire):
        hzRecord = int(digilent_dd_sample_rate)
        nRecord = int(samples_to_acquire)
        rgwRecord = (c_uint16*nRecord)()
        cAvailable = c_int()
        cLost = c_int()
        cCorrupted = c_int()
        iSample = 0
        fLost = 0
        fCorrupted = 0
        hzDI = c_double()
        sts = c_ubyte()




        self._dwf.FDwfDigitalInInternalClockInfo(self._hdwf, byref(hzDI))
        print("DigitanIn base freq: "+str(hzDI.value))

        # in record mode samples after trigger are acquired only
        self._dwf.FDwfDigitalInAcquisitionModeSet(self._hdwf, acqmodeRecord)
        # sample rate = system frequency / divider
        self._dwf.FDwfDigitalInDividerSet(self._hdwf, c_int(int(hzDI.value/hzRecord)))
        # 16bit per sample format
        self._dwf.FDwfDigitalInSampleFormatSet(self._hdwf, c_int(16))
        #dwf.FDwfDigitalInSampleFormatSet(hdwf, c_int(32))
        # number of samples after trigger
        self._dwf.FDwfDigitalInTriggerPositionSet(self._hdwf, c_int(int(nRecord)))
        # number of samples before trigger
        #dwf.FDwfDigitalInTriggerPrefillSet(hdwf, c_int(int(nRecord*1/4)))
        # for Digital Discovery bit order: DIO24:39; with 32 bit sampling [DIO24:39 + DIN0:15]
        self._dwf.FDwfDigitalInInputOrderSet(self._hdwf, c_int(0))
        # begin acquisition
        self._dwf.FDwfDigitalInConfigure(self._hdwf, c_int(1), c_int(1))

        print("Recording...")

        while True:
            self._dwf.FDwfDigitalInStatus(self._hdwf, c_int(1), byref(sts))
            self._dwf.FDwfDigitalInStatusRecord(self._hdwf, byref(cAvailable), byref(cLost), byref(cCorrupted))
            
            iSample += cLost.value
            iSample %= nRecord
            
            if cLost.value :
                fLost = 1
            if cCorrupted.value :
                fCorrupted = 1

            iBuffer = 0
            while cAvailable.value>0:
                cSamples = cAvailable.value
                if iSample+cAvailable.value > nRecord: # we are using circular sample buffer, prevent overflow
                    cSamples = nRecord-iSample
                self._dwf.FDwfDigitalInStatusData2(self._hdwf, byref(rgwRecord, 2*iSample), c_int(iBuffer), c_int(2*cSamples))
                iBuffer += cSamples
                cAvailable.value -= cSamples
                iSample += cSamples
                iSample %= nRecord

            if sts.value == DwfStateDone.value :
                break

        if iSample != 0 :
            rgwRecord = rgwRecord[iSample:]+rgwRecord[:iSample]

        print("  done")
        if fLost:
            print("Samples were lost! Reduce sample rate")
        if fCorrupted:
            print("Samples could be corrupted! Reduce sample rate")

        return rgwRecord

    @classmethod
    def initialize_dio_pins(cls, hdwf, dwf, output_pins=[0,1,2,3], initial_values=[0,0,0,0]):
        if len(output_pins) != len(initial_values):
            print("Error: The size of output_pins and initial_values arrays must be equal.")
            return False

        # Translate the physical pin number to the correct DIO index
            # From the Waveforms SDK documentation:
            #   "The DIO channel indexing for Digital Discovery starts from 0, 0 is DIO-24, 1 is DIO-25…"
        output_pin_index = []
        for pin in output_pins:
            if pin not in range(24, 40):
                print(f"Error: Pin {pin} is not a valid pin number.")
                return False
            pin = pin - 24
            output_pin_index.append(pin)
            
        try:
            # Set the digital IO as output pins
            output_enable_mask = sum(1 << pin for pin in output_pin_index)
            
            # Set DD I/O pins
            dwf.FDwfDigitalIOOutputEnableSet(hdwf, c_int(output_enable_mask))
            print(f"Configured pins {output_pin_index} as output pins.")
            
            # Set DD pin initial values
            current_mask = c_int()
            dwf.FDwfDigitalIOOutputGet(hdwf, byref(current_mask))
            new_mask = current_mask.value
            for i in range(len(initial_values)):
                if initial_values[i]:
                    # Set pin high
                    new_mask |= 1 << output_pin_index[i]
                else:
                    # Set pin low
                    new_mask &= ~(1 << output_pin_index[i])
            dwf.FDwfDigitalIOOutputSet(hdwf, c_int(new_mask))
            
            # Enable the digital IO
            dwf.FDwfDigitalIOConfigure(hdwf)
            pin_status = cls.read_dio_status(hdwf, dwf)
            results = []
            for i in range(len(initial_values)):
                if (pin_status>>output_pins[i])&1 == initial_values[i]:
                    print(f"Pin {output_pins[i]} initialized to {initial_values[i]}")
                    results.append(True)
                else:
                    print(f"Error: Pin {output_pins[i]} not initialized to {initial_values[i]}")
                    results.append(False)
            return True if all(results) else False

        except Exception as e:  
            return False

    @classmethod
    def read_dio_status(cls, hdwf, dwf):
        dwRead = c_uint32()
        dwf.FDwfDigitalIOStatus(hdwf)
        dwf.FDwfDigitalIOInputStatus(hdwf, byref(dwRead))

        # print("Digital I/O Status:")
        # print("DIO-0:", (dwRead.value>>0)&1, "DIO-1:", (dwRead.value>>1)&1, "DIO-2:", (dwRead.value>>2)&1, "DIO-3:", (dwRead.value>>3)&1,
        #     "\nDIO-4:", (dwRead.value>>4)&1, "DIO-5:", (dwRead.value>>5)&1, "DIO-6:", (dwRead.value>>6)&1, "DIO-7:", (dwRead.value>>7)&1,
        #     "\nDIO-8:", (dwRead.value>>8)&1, "DIO-9:", (dwRead.value>>9)&1, "DIO-10:", (dwRead.value>>10)&1, "DIO-11:", (dwRead.value>>11)&1,
        #     "\nDIO-12:", (dwRead.value>>12)&1, "DIO-13:", (dwRead.value>>13)&1, "DIO-14:", (dwRead.value>>14)&1, "DIO-15:", (dwRead.value>>15)&1)
        print("Digital I/O Status (binary):", bin(dwRead.value))

        return dwRead.value

    @classmethod
    def stop_running_processes(cls, hdwf, dwf):
        dwf.FDwfDigitalIOReset(hdwf)
        dwf.FDwfDigitalIOConfigure(hdwf)

        print("All processes stopped.")

    @classmethod
    def set_relay_pin(cls, hdwf, dwf, relay_pin, state, output_pins=[0,1,2,3]):
        # Translate the physical pin number to the correct DIO index
            # From the Waveforms SDK documentation:
            #   "The DIO channel indexing for Digital Discovery starts from 0, 0 is DIO-24, 1 is DIO-25…"
        output_pin_index = []
        for pin in output_pins:
            if pin not in range(24, 40):
                print(f"Error: Pin {pin} is not a valid pin number.")
                return False
            pin = pin - 24
            output_pin_index.append(pin)
        relay_pin = relay_pin - 24
        
        # Set the digital IO output pins
        try:
            output_enable_mask = sum(1 << pin for pin in output_pin_index)
            dwf.FDwfDigitalIOOutputEnableSet(hdwf, output_enable_mask)
            # output_enable_mask = (1 << 15)
            # dwf.FDwfDigitalIOOutputEnableSet(hdwf, output_enable_mask)\

            # Get current IO status
            current_mask = c_int()
            dwf.FDwfDigitalIOOutputGet(hdwf, byref(current_mask))
            # dwf.FDwfDigitalIOInputStatus(hdwf, byref(current_mask))
            # print(f"current_mask: {current_mask.value}")
            new_mask = current_mask.value   

            # dwRead = c_uint32()
            # dwf.FDwfDigitalIOStatus(hdwf)
            # # dwf.FDwfDigitalIOOutputGet(hdwf, byref(dwRead))
            # dwf.FDwfDigitalIOInputStatus(hdwf, byref(dwRead))

            # current_mask = c_int()
            # dwf.FDwfDigitalIOOutputGet(hdwf, byref(current_mask))
            # new_mask = dwRead.value

            if state:
                # Set pin high
                new_mask |= 1 << relay_pin    
            else:
                # Set pin low
                new_mask &= ~(1 << relay_pin)
            
            # info = c_uint32()
            dwf.FDwfDigitalIOOutputSet(hdwf, c_int(new_mask))
            # dwf.FDwfDigitalIOOutputInfo(hdwf, byref(info))
            # dwf.FDwfDigitalIOOutputSet(hdwf, c_int(8000))
            dwf.FDwfDigitalIOConfigure(hdwf)
            pin_status = cls.read_dio_status(hdwf, dwf)
            if (pin_status>>relay_pin)&1 == state:
                # print(f"Pin {relay_pin} successfully set to {state}")
                return True
            else:
                print(f"Error: Pin {relay_pin} not set to {state} (current state: {(pin_status>>relay_pin)&1})")
                return False
            
        except Exception as e:
            return False
    
if __name__ == "__main__":
    # # Open the device
    # dwf = ddo.load_lib()
    # hdwf = ddo.open_device_by_sn(dwf, "sn:210321B0F505") # Digital Discovery
    # if hdwf == hdwfNone.value:
    #     print("Device not found.")
    #     sys.exit(1)

    # read_frequency(hdwf, dwf, 8)


    # # Close the device
    # ddo.close_device(dwf, hdwf)
    pass
