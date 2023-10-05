# -*- coding: utf-8 -*-

import ctypes
import nisync.errors as errors
import threading

from nisync._visatype import * 



class Library(object):
    '''Library

    Wrapper around driver library.
    Class will setup the correct ctypes information for every function on first call.
    '''

    def __init__(self, ctypes_library):
        self._func_lock = threading.Lock()
        self._library = ctypes_library
        # We cache the cfunc object from the ctypes.CDLL object
        self.niSync_init_cfunc = None
        self.niSync_close_cfunc = None
        self.niSync_error_message_cfunc = None
        self.niSync_reset_cfunc = None
        self.niSync_self_test_cfunc = None
    
    
    def _get_library_function(self, name):
        try:
            function = getattr(self._library, name)
        except AttributeError as e:
            raise errors.DriverTooOldError() from e
        return function
        
        
    def niSync_init(self, resource_name, id_query, reset_device, vi):  
        with self._func_lock:
            if self.niSync_init_cfunc is None:
                self.niSync_init_cfunc = self._get_library_function('niSync_init')
                self.niSync_init_cfunc.argtypes = [ctypes.POINTER(ViChar), ViBoolean, ViBoolean, ctypes.POINTER(ViSession)]  
                self.niSync_init_cfunc.restype = ViStatus  
        return self.niSync_init_cfunc(resource_name, id_query, reset_device, vi)
        
        
    def niSync_close(self, vi):  # noqa: N802
        with self._func_lock:
            if self.niSync_close_cfunc is None:
                self.niSync_close_cfunc = self._get_library_function('niSync_close')
                self.niSync_close_cfunc.argtypes = [ViSession]  
                self.niSync_close_cfunc.restype = ViStatus  
        return self.niSync_close_cfunc(vi)
        
    def niSync_error_message(self, vi, error_code, error_message): 
        with self._func_lock:
            if self.niSync_error_message_cfunc is None:
                self.niSync_error_message_cfunc = self._get_library_function('niSync_error_message')
                self.niSync_error_message_cfunc.argtypes = [ViSession, ViStatus, ctypes.POINTER(ViChar)] 
                self.niSync_error_message_cfunc.restype = ViStatus 
        return self.niSync_error_message_cfunc(vi, error_code, error_message)

    def niSync_reset(self, vi):
        with self._func_lock:
            if self.niSync_reset_cfunc is None:
                self.niSync_reset_cfunc = self._get_library_function('niSync_reset')
                self.niSync_reset_cfunc.argtypes = [ViSession]
                self.niSync_reset_cfunc.restype = ViStatus
        return self.niSync_reset_cfunc(vi)

    def niSync_self_test(self, vi, test_result, test_message):
        with self._func_lock:
            if self.niSync_self_test_cfunc is None:
                self.niSync_self_test_cfunc = self._get_library_function('niSync_self_test')
                self.niSync_self_test_cfunc.argtypes = [ViSession, ctypes.POINTER(ViInt16), ctypes.POINTER(ViChar)] 
                self.niSync_self_test_cfunc.restype = ViStatus 
        return self.niSync_self_test_cfunc(vi, test_result, test_message)