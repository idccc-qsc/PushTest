import sys
from ctypes import *
from abc import ABC, abstractmethod

class BaseDigilentDevice(ABC):
    def __init__(self):
        self.dwf = None
        self.hdwf = None
        
        # Load the DWF library
        self.load_lib()
    
    # Load the DWF library
    def load_lib(self):
        if sys.platform.startswith("win"):
            self.dwf = cdll.dwf
        elif sys.platform.startswith("darwin"):
            self.dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
        else:
            self.dwf = cdll.LoadLibrary("libdwf.so")
        if self.dwf is None:
            print("Failed to load dwf library")
            # utils.log_to_file("Failed to load dwf library")
            quit()  
        # return self.dwf
    
    # Open device by serial number
    def open_device_by_sn(self, sn):
        hdwf = c_int()
        cSN = c_char_p(sn.encode('utf-8')) # convert string to c_char_p        

        version = create_string_buffer(16)
        self.dwf.FDwfGetVersion(version)
        # print("DWF Version: "+str(version.value))

        # print(f"Opening device with device sn {sn}")
        self.dwf.FDwfDeviceOpenEx(byref(cSN), byref(hdwf))

        if hdwf.value == 0:
            print("failed to open device")
            szerr = create_string_buffer(512)
            self.dwf.FDwfGetLastErrorMsg(szerr)
            print(str(szerr.value))
            quit()

        self.dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))# 0 = the device will be configured only when calling FDwf###Configure
        self.hdwf = hdwf
        self.sn = sn
        
        return hdwf

    # Open device by device index
    def open_device_by_device_index(self, device_index):
        hdwf = c_int()
        cDeviceIndex = c_int(device_index)    

        version = create_string_buffer(16)
        self.dwf.FDwfGetVersion(version)
        print("DWF Version: "+str(version.value))

        print(f"Opening device with device index {device_index}")
        self.dwf.FDwfDeviceOpen(byref(cDeviceIndex), byref(hdwf))

        if hdwf.value == 0:
            print("failed to open device")
            szerr = create_string_buffer(512)
            self.dwf.FDwfGetLastErrorMsg(szerr)
            print(str(szerr.value))
            quit()

        self.dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))# 0 = the device will be configured only when calling FDwf###Configure
        self.hdwf = hdwf
        
        return hdwf

    # Open first available device
    def open_device_default(self):
        hdwf = c_int()

        version = create_string_buffer(16)
        self.dwf.FDwfGetVersion(version)
        print("DWF Version: "+str(version.value))

        print(f"Opening first available device")
        self.dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

        if hdwf.value == 0:
            print("failed to open device")
            szerr = create_string_buffer(512)
            self.dwf.FDwfGetLastErrorMsg(szerr)
            print(str(szerr.value))
            quit()

        self.dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))# 0 = the device will be configured only when calling FDwf###Configure
        self.hdwf = hdwf

        return hdwf

    # Close device
    def close_device(self):
        self.dwf.FDwfDeviceClose(self.hdwf)
        return