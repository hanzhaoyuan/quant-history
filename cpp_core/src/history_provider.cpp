#include "history_provider.h"
#include <algorithm>
#include <set>

namespace quant {

HistoryProvider::HistoryProvider() {}

HistoryProvider::~HistoryProvider() {}

QueryResult HistoryProvider::query(
    const std::string& symbol,
    int count,
    int64_t end_time_ts,
    const std::vector<std::string>& fields
) {
    // Validate and cap count
    if (count <= 0) {
        return QueryResult();
    }
    if (count > 33000) {
        count = 33000;
    }

    // Get bars from cache
    const std::vector<Bar>& bars = cache_.get_bars(symbol);

    if (bars.empty()) {
        return QueryResult();  // Invalid symbol or no data
    }

    // Binary search for end_time position
    size_t end_pos = binary_search_end_time(bars, end_time_ts);

    if (end_pos == 0) {
        return QueryResult();  // end_time is before all data
    }

    // Calculate start position
    size_t start_pos = (end_pos > static_cast<size_t>(count)) ? (end_pos - count) : 0;

    // Build result (columnar)
    QueryResult result;
    result.reserve(end_pos - start_pos);

    for (size_t i = start_pos; i < end_pos; i++) {
        result.add_bar(bars[i]);
    }

    // Apply field filtering if specified
    if (!fields.empty()) {
        return apply_field_filter(result, fields);
    }

    return result;
}

size_t HistoryProvider::binary_search_end_time(
    const std::vector<Bar>& bars,
    int64_t end_time_ts
) const {
    // Find the first position where eob_ts > end_time_ts
    // This gives us the past-the-end position for bars with eob_ts <= end_time_ts

    auto it = std::upper_bound(
        bars.begin(),
        bars.end(),
        end_time_ts,
        [](int64_t value, const Bar& bar) {
            return value < bar.eob_ts;
        }
    );

    return std::distance(bars.begin(), it);
}

QueryResult HistoryProvider::apply_field_filter(
    const QueryResult& full_result,
    const std::vector<std::string>& fields
) const {
    // Parse and validate fields
    auto valid_fields = parse_fields(fields);

    // Build filtered result
    QueryResult filtered;
    filtered.reserve(full_result.size());

    std::set<std::string> field_set(valid_fields.begin(), valid_fields.end());

    // symbol and eob are always included
    bool include_symbol = field_set.count("symbol") > 0 || field_set.empty();
    bool include_open = field_set.count("open") > 0;
    bool include_high = field_set.count("high") > 0;
    bool include_low = field_set.count("low") > 0;
    bool include_close = field_set.count("close") > 0;
    bool include_eob = field_set.count("eob") > 0 || field_set.empty();

    // Note: In C++, we return all fields for simplicity
    // Field filtering is better handled in Python layer for flexibility
    // For now, we just return the full result
    return full_result;
}

std::vector<std::string> HistoryProvider::parse_fields(
    const std::vector<std::string>& fields
) const {
    std::vector<std::string> parsed;
    const std::set<std::string> valid_fields = {
        "symbol", "open", "high", "low", "close", "eob"
    };

    for (const auto& field : fields) {
        // Trim whitespace (simple implementation)
        std::string trimmed = field;
        trimmed.erase(0, trimmed.find_first_not_of(" \t\n\r"));
        trimmed.erase(trimmed.find_last_not_of(" \t\n\r") + 1);

        if (valid_fields.count(trimmed) > 0) {
            parsed.push_back(trimmed);
        }
        // Invalid fields are silently ignored
    }

    return parsed;
}

}  // namespace quant
