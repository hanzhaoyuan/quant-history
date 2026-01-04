#pragma once
#include "bar.h"
#include "market_data.h"
#include <vector>
#include <string>
#include <cstdint>

namespace quant {

// Columnar query result for zero-copy conversion to NumPy
struct QueryResult {
    std::vector<std::string> symbols;
    std::vector<double> opens;
    std::vector<double> highs;
    std::vector<double> lows;
    std::vector<double> closes;
    std::vector<int64_t> eob_timestamps;

    size_t size() const { return symbols.size(); }

    void reserve(size_t n) {
        symbols.reserve(n);
        opens.reserve(n);
        highs.reserve(n);
        lows.reserve(n);
        closes.reserve(n);
        eob_timestamps.reserve(n);
    }

    void add_bar(const Bar& bar) {
        symbols.push_back(bar.symbol);
        opens.push_back(bar.open);
        highs.push_back(bar.high);
        lows.push_back(bar.low);
        closes.push_back(bar.close);
        eob_timestamps.push_back(bar.eob_ts);
    }
};

class HistoryProvider {
public:
    HistoryProvider();
    ~HistoryProvider();

    // Query history_n interface
    // Returns up to 'count' bars with eob_ts <= end_time_ts
    // fields: vector of field names to include (empty = all fields)
    // Note: symbol and eob are always included
    QueryResult query(
        const std::string& symbol,
        int count,
        int64_t end_time_ts,
        const std::vector<std::string>& fields
    );

private:
    MarketDataCache cache_;

    // Binary search to find the rightmost position where eob_ts <= end_time_ts
    // Returns index+1 (past-the-end position for slicing)
    size_t binary_search_end_time(
        const std::vector<Bar>& bars,
        int64_t end_time_ts
    ) const;

    // Apply field filtering (columnar result)
    QueryResult apply_field_filter(
        const QueryResult& full_result,
        const std::vector<std::string>& fields
    ) const;

    // Parse and validate field names
    std::vector<std::string> parse_fields(const std::vector<std::string>& fields) const;
};

}  // namespace quant
