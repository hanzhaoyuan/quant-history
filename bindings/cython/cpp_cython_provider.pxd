# cython: language_level=3
# Cython declaration file for C++ history provider

from libcpp.string cimport string
from libcpp.vector cimport vector

cdef extern from "history_provider.h" namespace "quant":
    cdef cppclass QueryResult:
        vector[string] symbols
        vector[double] opens
        vector[double] highs
        vector[double] lows
        vector[double] closes
        vector[long long] eob_timestamps
        size_t size()

    cdef cppclass HistoryProvider:
        HistoryProvider()
        QueryResult query(const string& symbol, int count, long long end_time_ts, const vector[string]& fields)
