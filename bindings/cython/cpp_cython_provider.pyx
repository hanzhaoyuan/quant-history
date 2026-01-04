# cython: language_level=3
# Cython wrapper for C++ history provider

cimport cpp_cython_provider as cpp
from libcpp.string cimport string
from libcpp.vector cimport vector
import numpy as np
cimport numpy as cnp

cnp.import_array()

cdef class CythonHistoryProvider:
    cdef cpp.HistoryProvider* provider

    def __cinit__(self):
        self.provider = new cpp.HistoryProvider()

    def __dealloc__(self):
        if self.provider != NULL:
            del self.provider

    def query(self, str symbol, int count, long long end_time_ts, list fields):
        """
        Query history_n data from C++ backend

        Args:
            symbol: Symbol code
            count: Number of bars
            end_time_ts: End time as Unix timestamp
            fields: List of field names

        Returns:
            dict with numpy arrays for each field
        """
        # Convert Python strings to C++ strings
        cdef string cpp_symbol = symbol.encode('utf-8')
        cdef vector[string] cpp_fields
        for field in fields:
            cpp_fields.push_back(field.encode('utf-8'))

        # Call C++ query
        cdef cpp.QueryResult result = self.provider.query(cpp_symbol, count, end_time_ts, cpp_fields)

        # Convert to Python/NumPy
        cdef size_t size = result.size()

        if size == 0:
            return {
                'symbols': np.array([], dtype=object),
                'opens': np.array([], dtype=np.float64),
                'highs': np.array([], dtype=np.float64),
                'lows': np.array([], dtype=np.float64),
                'closes': np.array([], dtype=np.float64),
                'eob_timestamps': np.array([], dtype=np.int64)
            }

        # Convert vectors to NumPy arrays
        cdef cnp.ndarray[object, ndim=1] symbols = np.empty(size, dtype=object)
        cdef cnp.ndarray[double, ndim=1] opens = np.empty(size, dtype=np.float64)
        cdef cnp.ndarray[double, ndim=1] highs = np.empty(size, dtype=np.float64)
        cdef cnp.ndarray[double, ndim=1] lows = np.empty(size, dtype=np.float64)
        cdef cnp.ndarray[double, ndim=1] closes = np.empty(size, dtype=np.float64)
        cdef cnp.ndarray[long long, ndim=1] eob_ts = np.empty(size, dtype=np.int64)

        cdef size_t i
        for i in range(size):
            symbols[i] = result.symbols[i].decode('utf-8')
            opens[i] = result.opens[i]
            highs[i] = result.highs[i]
            lows[i] = result.lows[i]
            closes[i] = result.closes[i]
            eob_ts[i] = result.eob_timestamps[i]

        return {
            'symbols': symbols,
            'opens': opens,
            'highs': highs,
            'lows': lows,
            'closes': closes,
            'eob_timestamps': eob_ts
        }
