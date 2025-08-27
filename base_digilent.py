import sys
from ctypes import *
from abc import ABC, abstractmethod

class BaseDigilentDevice(ABC):
    _dwf = None
    LibraryLoaded = False

    def __init__(self):
        self._hdwf = None
        self.SerialNumber = ""
        
        # Load the DWF library
        self.load_library()
    
    # Load the DWF library
    @classmethod
    def load_library(cls):
        if cls.LibraryLoaded:
            return
        
        if sys.platform.startswith("win"):
            cls._dwf = cdll.dwf
        elif sys.platform.startswith("darwin"):
            cls._dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
        else:
            cls._dwf = cdll.LoadLibrary("libdwf.so")
        if cls._dwf is None:
            print("Failed to load dwf library")
            # utils.log_to_file("Failed to load dwf library")
            quit()  
        else:
            cls.LibraryLoaded = True
    

    # Open device by serial number
    def open_by_sn(self, sn):
        cls = type(self)

        hdwf = c_int()
        cSN = c_char_p(sn.encode('utf-8')) # convert string to c_char_p        

        version = create_string_buffer(16)
        cls._dwf.FDwfGetVersion(version)
        cls._dwf.FDwfDeviceOpenEx(byref(cSN), byref(hdwf))

        if hdwf.value == 0:
            print(f"Failed to open device: {sn}")
            szerr = create_string_buffer(512)
            cls._dwf.FDwfGetLastErrorMsg(szerr)
            print(str(szerr.value))
            return False

        cls._dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))# 0 = the device will be configured only when calling FDwf###Configure

        self._hdwf = hdwf
        self.SerialNumber = sn

        return True

    # Open device by device index
    def open_by_device_index(self, device_index):
        cls = type(self)
    
        hdwf = c_int()
        cDeviceIndex = c_int(device_index)    

        version = create_string_buffer(16)
        cls._dwf.FDwfGetVersion(version)
        print("DWF Version: "+str(version.value))

        print(f"Opening device with device index {device_index}")
        cls._dwf.FDwfDeviceOpen(byref(cDeviceIndex), byref(hdwf))

        if hdwf.value == 0:
            print("failed to open device")
            szerr = create_string_buffer(512)
            cls._dwf.FDwfGetLastErrorMsg(szerr)
            print(str(szerr.value))
            return False

        cls._dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))# 0 = the device will be configured only when calling FDwf###Configure
        self._hdwf = hdwf
        
        return True

    # Open first available device
    def open_by_default(self):
        cls = type(self)

        hdwf = c_int()

        version = create_string_buffer(16)
        cls._dwf.FDwfGetVersion(version)
        print("DWF Version: "+str(version.value))

        print(f"Opening first available device")
        cls._dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

        if hdwf.value == 0:
            print("failed to open device")
            szerr = create_string_buffer(512)
            cls._dwf.FDwfGetLastErrorMsg(szerr)
            print(str(szerr.value))
            return False

        cls._dwf.FDwfDeviceAutoConfigureSet(hdwf, c_int(0))# 0 = the device will be configured only when calling FDwf###Configure
        self.hdwf = hdwf

        return True

    # Close device
    def close(self):
        cls = type(self)

        cls._dwf.FDwfDeviceClose(self._hdwf)
        return