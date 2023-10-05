# -*- coding: utf-8 -*-

import array
import ctypes
import hightime  
import platform

import nisync._library_singleton as _library_singleton
import nisync._visatype as _visatype
import nisync.errors as errors


# Helper functions for creating ctypes needed for calling into the driver DLL
def _get_ctypes_pointer_for_buffer(value=None, library_type=None, size=None):
    if isinstance(value, array.array):
        assert library_type is not None, 'library_type is required for array.array'
        addr, _ = value.buffer_info()
        return ctypes.cast(addr, ctypes.POINTER(library_type))
    elif str(type(value)).find("'numpy.ndarray'") != -1:
        import numpy
        return numpy.ctypeslib.as_ctypes(value)
    elif isinstance(value, bytes):
        return ctypes.cast(value, ctypes.POINTER(library_type))
    elif isinstance(value, list):
        assert library_type is not None, 'library_type is required for list'
        return (library_type * len(value))(*value)
    else:
        if library_type is not None and size is not None:
            return (library_type * size)()
        else:
            return None


def _convert_to_array(value, array_type):
    if value is not None:
        if isinstance(value, array.array):
            value_array = value
        else:
            value_array = array.array(array_type, value)
    else:
        value_array = None

    return value_array


class LibraryInterpreter(object):
    '''Library C<->Python interpreter.

    This class is responsible for interpreting the Library's C API. It is responsible for:
    * Converting ctypes to native Python types.
    * Dealing with string encoding.
    * Allocating memory.
    * Converting errors returned by Library into Python exceptions.
    '''

    def __init__(self, encoding):
        self._encoding = encoding
        self._library = _library_singleton.get()
        
        # Initialize _vi to 0 for now.
        # Session will directly update it once the driver runtime init function has been called and
        # we have a valid session handle.
        self.set_session_handle()

    def set_session_handle(self, value=0):
        self._vi = value

    def get_session_handle(self):
        return self._vi

    def get_error_description(self, error_code):
        '''get_error_description

        Returns the error description.
        '''
        try:
            returned_error_code, error_string = self.get_error()
            if returned_error_code == error_code:
                return error_string
        except errors.Error:
            pass

        try:
            '''
            It is expected for get_error to raise when the session is invalid
            (IVI spec requires GetError to fail).
            Use error_message instead. It doesn't require a session.
            '''
            error_string = self.error_message(error_code)
            return error_string
        except errors.Error:
            pass
        return "Failed to retrieve error description."

    def init(self, resource_name, id_query, reset_device):
        resource_name_ctype = ctypes.create_string_buffer(resource_name.encode(self._encoding))
        id_query_ctype = _visatype.ViBoolean(id_query)
        reset_device_ctype = _visatype.ViBoolean(reset_device)
        vi_ctype = _visatype.ViSession()
        error_code = self._library.niSync_init(resource_name_ctype, id_query_ctype, reset_device_ctype, None if vi_ctype is None else (ctypes.pointer(vi_ctype)))
        errors.handle_error(self, error_code, ignore_warnings=False, is_error_handling=False)
        self._close_on_exit = True
        return int(vi_ctype.value)
        
    def close(self):
        vi_ctype = _visatype.ViSession(self._vi)
        error_code = self._library.niSync_close(vi_ctype)
        errors.handle_error(self, error_code, ignore_warnings=False, is_error_handling=False)
        return

    def error_message(self, error_code):
        vi_ctype = _visatype.ViSession(self._vi)
        error_code_ctype = _visatype.ViStatus(error_code)
        error_message_ctype = (_visatype.ViChar * 256)()
        error_code = self._library.niSync_error_message(vi_ctype, error_code_ctype, error_message_ctype)
        errors.handle_error(self, error_code, ignore_warnings=False, is_error_handling=True)
        return error_message_ctype.value.decode(self._encoding)

    def reset(self):
        vi_ctype = _visatype.ViSession(self._vi)
        error_code = self._library.niSync_reset(vi_ctype)
        errors.handle_error(self, error_code, ignore_warnings=False, is_error_handling=False)
        return

    def self_test(self):
        vi_ctype = _visatype.ViSession(self._vi)
        test_result_ctype = _visatype.ViInt16()
        test_message_ctype = (_visatype.ViChar * 2048)()
        error_code = self._library.niSync_self_test(vi_ctype, None if test_result_ctype is None else (ctypes.pointer(test_result_ctype)), test_message_ctype)
        errors.handle_error(self, error_code, ignore_warnings=False, is_error_handling=False)
        return int(test_result_ctype.value), test_message_ctype.value.decode(self._encoding)