# -*- coding: utf-8 -*-

import array

import nisync._library_interpreter as _library_interpreter
import nisync.errors as errors

# Used for __repr__
import pprint
pp = pprint.PrettyPrinter(indent=4)

class _Lock(object):
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        # _lock_session is called from the lock() function, not here
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._session.unlock()
        

class _SessionBase(object):
    '''Base class for all NI-Sync sessions.'''

    # This is needed during __init__. Without it, __setattr__ raises an exception
    _is_frozen = False
    
    def __init__(self, interpreter, freeze_it=False):
        self._interpreter = interpreter

        # Store the parameter list for later printing in __repr__
        param_list = []
        param_list.append("interpreter=" + pp.pformat(interpreter))
        self._param_list = ', '.join(param_list)

        # Finally, set _is_frozen to True which is used to prevent clients from accidentally adding
        # members when trying to set a property with a typo.
        self._is_frozen = freeze_it

    def __repr__(self):
        return '{0}.{1}({2})'.format('nisync', self.__class__.__name__, self._param_list)

    def __setattr__(self, key, value):
        if self._is_frozen and key not in dir(self):
            raise AttributeError("'{0}' object has no attribute '{1}'".format(type(self).__name__, key))
        object.__setattr__(self, key, value)
        
    def lock(self):
        '''lock

        Obtains a multithread lock on the device session. Before doing so, the
        software waits until all other execution threads release their locks
        on the device session.

        Other threads may have obtained a lock on this session for the
        following reasons:

            -  The application called the lock method.
            -  A call to NI-Digital Pattern Driver locked the session.
            -  After a call to the lock method returns
               successfully, no other threads can access the device session until
               you call the unlock method or exit out of the with block when using
               lock context manager.
            -  Use the lock method and the
               unlock method around a sequence of calls to
               instrument driver methods if you require that the device retain its
               settings through the end of the sequence.

        You can safely make nested calls to the lock method
        within the same thread. To completely unlock the session, you must
        balance each call to the lock method with a call to
        the unlock method.

        Returns:
            lock (context manager): When used in a with statement, nidigital.Session.lock acts as
            a context manager and unlock will be called when the with block is exited
        '''
        self._interpreter.lock()  # We do not call this in the context manager so that this function can
        # act standalone as well and let the client call unlock() explicitly. If they do use the context manager,
        # that will handle the unlock for them
        return _Lock(self)
        
    def unlock(self):
        '''unlock

        Releases a lock that you acquired on an device session using
        lock. Refer to lock for additional
        information on session locks.
        '''
        self._interpreter.unlock()
        
    def _error_message(self, error_code):
        r'''_error_message

        Takes the error code returned by the nisync methods, interprets it, and returns it as a user readable string.

        Args:
            error_code (int): The specified error code.


        Returns:
            error_message (str): The error information formatted as a string. The array must contain at least 256 characters.

        '''
        error_message = self._interpreter.error_message(error_code)
        return error_message

class Session(_SessionBase):
    '''An NI-Syncr session'''

    def __init__(self, resource_name, id_query=False, reset_device=False):
    
        interpreter = _library_interpreter.LibraryInterpreter(encoding='windows-1251')
        # Initialize the superclass with default values first, populate them later
        super(Session, self).__init__(
            interpreter=interpreter,
            freeze_it=False
        )
        
        # Call specified init function
        # Note that _interpreter default-initializes the session handle in its constructor, so that
        # if _init_with_options fails, the error handler can reference it.
        # And then here, once _init_with_options succeeds, we call set_session_handle
        # with the actual session handle.
        self._interpreter.set_session_handle(self._init(resource_name, id_query, reset_device))
        
        # Store the parameter list for later printing in __repr__
        param_list = []
        param_list.append("resource_name=" + pp.pformat(resource_name))
        param_list.append("reset_device=" + pp.pformat(reset_device))
        self._param_list = ', '.join(param_list)
        
        # Finally, set _is_frozen to True which is used to prevent clients from accidentally adding
        # members when trying to set a property with a typo.
        self._is_frozen = True
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._interpreter._close_on_exit:
            self.close()
            
    def close(self):
        '''close

        Closes the specified instrument session to a nisync instrument

        Note:
        This method is not needed when using the session context manager
        '''
        try:
            self._close()
        except errors.DriverError:
            self._interpreter.set_session_handle()
            raise
        self._interpreter.set_session_handle()
        
    def self_test(self):
        '''self_test

        Returns self test results from a digital pattern instrument. This test requires several minutes to execute.

        Raises `SelfTestError` on self test failure. Properties on exception object:

        - code - failure code from driver
        - message - status message from driver

        +----------------+-------------------+
        | Self-Test Code | Description       |
        +================+===================+
        | 0              | Self test passed. |
        +----------------+-------------------+
        | 1              | Self test failed. |
        +----------------+-------------------+
        '''
        code, msg = self._self_test()
        if code:
            raise errors.SelfTestError(code, msg)
        return None
        
    def _init(self, resource_name, id_query=False, reset_device=False):
        r'''_init_with_options

        Creates and returns a new session to the specified nisync instrument to use in all subsequent method calls. To place the instrument in a known startup state when creating a new session, set the reset parameter to True, which is equivalent to calling the reset method immediately after initializing the session.

        Args:
            resource_name (str): The specified resource name shown in Measurement & Automation Explorer (MAX) for a digital pattern instrument, for example, PXI1Slot3, where PXI1Slot3 is an instrument resource name. **resourceName** can also be a logical IVI name. This parameter accepts a comma-delimited list of strings in the form PXI1Slot2,PXI1Slot3, where ``PXI1Slot2`` is one instrument resource name and ``PXI1Slot3`` is another. When including more than one digital pattern instrument in the comma-delimited list of strings, list the instruments in the same order they appear in the pin map.

                +--------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
                | |Note| | Note   You only can specify multiple instruments of the same model. For example, you can list two PXIe-6570s but not a PXIe-6570 and PXIe-6571. The instruments must be in the same chassis. |
                +--------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

                .. |Note| image:: note.gif

                Note:

            id_query (bool): A Boolean that verifies that the digital pattern instrument you initialize is supported by NI-Digital. NI-Digital automatically performs this query, so setting this parameter is not necessary.

            reset_device (bool): A Boolean that specifies whether to reset a digital pattern instrument to a known state when the session is initialized. Setting the **resetDevice** value to True is equivalent to calling the reset method immediately after initializing the session.

        Returns:
            new_vi (int): The returned instrument session.

        '''
        new_vi = self._interpreter.init(resource_name, id_query, reset_device)
        return new_vi
        
    def _close(self):
        r'''_close

        Closes the specified instrument session to a nisync instrument.
        '''
        self._interpreter.close()
        
    def reset(self):
        r'''reset

        Returns a nisync instrument to a known state.
        '''
        self._interpreter.reset()
        
    def _self_test(self):
        r'''_self_test

        Returns self test results from a nisync instrument. This test requires several minutes to execute.

        Returns:
            test_result (int): A parameter that indicates if the self test passed (0) or failed (!=0).

            test_message (str): The returned self test status message. The array must contain at least 256 characters.

        '''
        test_result, test_message = self._interpreter.self_test()
        return test_result, test_message