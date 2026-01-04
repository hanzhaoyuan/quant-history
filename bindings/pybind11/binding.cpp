#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "history_provider.h"

namespace py = pybind11;

PYBIND11_MODULE(_cpp_history_core, m) {
    m.doc() = "C++ backend for history_n query interface";

    // Expose QueryResult
    py::class_<quant::QueryResult>(m, "QueryResult")
        .def(py::init<>())
        .def_readonly("symbols", &quant::QueryResult::symbols)
        .def_readonly("opens", &quant::QueryResult::opens)
        .def_readonly("highs", &quant::QueryResult::highs)
        .def_readonly("lows", &quant::QueryResult::lows)
        .def_readonly("closes", &quant::QueryResult::closes)
        .def_readonly("eob_timestamps", &quant::QueryResult::eob_timestamps)
        .def("size", &quant::QueryResult::size);

    // Expose HistoryProvider
    py::class_<quant::HistoryProvider>(m, "HistoryProvider")
        .def(py::init<>())
        .def("query", &quant::HistoryProvider::query,
             py::arg("symbol"),
             py::arg("count"),
             py::arg("end_time_ts"),
             py::arg("fields") = std::vector<std::string>(),
             "Query history_n data\n\n"
             "Args:\n"
             "    symbol: Symbol code\n"
             "    count: Number of bars to return\n"
             "    end_time_ts: End time as Unix timestamp (seconds)\n"
             "    fields: List of field names to include\n\n"
             "Returns:\n"
             "    QueryResult with columnar data");
}
