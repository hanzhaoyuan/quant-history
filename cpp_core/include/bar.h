#pragma once
#include <string>
#include <cstdint>

namespace quant {

struct Bar {
    std::string symbol;
    double open;
    double high;
    double low;
    double close;
    int64_t eob_ts;  // End of bar timestamp (seconds since epoch, UTC+8)

    Bar() : open(0), high(0), low(0), close(0), eob_ts(0) {}

    Bar(const std::string& sym, double o, double h, double l, double c, int64_t ts)
        : symbol(sym), open(o), high(h), low(l), close(c), eob_ts(ts) {}
};

}  // namespace quant
