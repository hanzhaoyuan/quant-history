#include "market_data.h"
#include <functional>
#include <ctime>
#include <algorithm>

namespace quant {

MarketDataCache::MarketDataCache() {}

MarketDataCache::~MarketDataCache() {}

void MarketDataCache::initialize(const std::string& symbol) {
    if (has_symbol(symbol)) {
        return;  // Already initialized
    }

    std::vector<Bar> bars;
    bars.reserve(100 * 240);  // 100 trading days * 240 bars per day

    uint32_t seed = get_seed_from_symbol(symbol);

    // Generate 100 trading days starting from 2024-01-02 (UTC+8)
    // We'll use a simple date iteration and skip weekends
    int year = 2024;
    int month = 1;
    int day = 2;  // Tuesday

    int trading_days = 0;
    while (trading_days < 100) {
        if (is_trading_day(year, month, day)) {
            // Calculate timestamp for this date at 00:00:00 local time
            std::tm tm_date = {};
            tm_date.tm_year = year - 1900;
            tm_date.tm_mon = month - 1;
            tm_date.tm_mday = day;
            tm_date.tm_hour = 0;
            tm_date.tm_min = 0;
            tm_date.tm_sec = 0;

            // Convert to timestamp (local time, assumed to be UTC+8)
            // mktime returns local time timestamp, which is what we want
            int64_t date_ts = std::mktime(&tm_date);

            auto day_bars = generate_trading_day(symbol, date_ts, seed);
            bars.insert(bars.end(), day_bars.begin(), day_bars.end());
            trading_days++;
        }

        // Move to next day
        day++;
        int days_in_month[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
        // Check for leap year
        if (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)) {
            days_in_month[1] = 29;
        }

        if (day > days_in_month[month - 1]) {
            day = 1;
            month++;
            if (month > 12) {
                month = 1;
                year++;
            }
        }
    }

    cache_[symbol] = std::move(bars);
}

const std::vector<Bar>& MarketDataCache::get_bars(const std::string& symbol) {
    if (!has_symbol(symbol)) {
        initialize(symbol);
    }
    return cache_[symbol];
}

bool MarketDataCache::has_symbol(const std::string& symbol) const {
    return cache_.find(symbol) != cache_.end();
}

std::vector<Bar> MarketDataCache::generate_trading_day(
    const std::string& symbol,
    int64_t date_ts,
    uint32_t& seed
) {
    std::vector<Bar> bars;
    bars.reserve(240);

    // Morning session: 09:30 - 11:30 (120 bars)
    // eob: 09:31:00 - 11:30:00
    int64_t morning_start = date_ts + (9 * 3600 + 30 * 60);  // 09:30:00
    for (int i = 0; i < 120; i++) {
        int64_t eob_ts = morning_start + (i + 1) * 60;  // eob is at the end of the minute
        bars.push_back(generate_bar(symbol, eob_ts, seed));
    }

    // Afternoon session: 13:00 - 15:00 (120 bars)
    // eob: 13:01:00 - 15:00:00
    int64_t afternoon_start = date_ts + (13 * 3600);  // 13:00:00
    for (int i = 0; i < 120; i++) {
        int64_t eob_ts = afternoon_start + (i + 1) * 60;  // eob is at the end of the minute
        bars.push_back(generate_bar(symbol, eob_ts, seed));
    }

    return bars;
}

Bar MarketDataCache::generate_bar(
    const std::string& symbol,
    int64_t eob_ts,
    uint32_t& seed
) {
    // Generate OHLC with constraints: low <= min(open, close) <= max(open, close) <= high

    // Base price around 100
    double base_price = 100.0;

    // Generate open and close
    double open = base_price + random_double(seed, -10.0, 10.0);
    double close = base_price + random_double(seed, -10.0, 10.0);

    double min_oc = std::min(open, close);
    double max_oc = std::max(open, close);

    // Generate low <= min(open, close)
    double low = min_oc - random_double(seed, 0.0, 2.0);

    // Generate high >= max(open, close)
    double high = max_oc + random_double(seed, 0.0, 2.0);

    return Bar(symbol, open, high, low, close, eob_ts);
}

bool MarketDataCache::is_trading_day(int year, int month, int day) const {
    // Create tm structure
    std::tm tm_date = {};
    tm_date.tm_year = year - 1900;
    tm_date.tm_mon = month - 1;
    tm_date.tm_mday = day;

    std::mktime(&tm_date);  // Normalize and compute tm_wday

    // Monday = 1, ..., Friday = 5, Saturday = 6, Sunday = 0
    int wday = tm_date.tm_wday;

    // Trading day: Monday to Friday (1-5)
    return wday >= 1 && wday <= 5;
}

uint32_t MarketDataCache::get_seed_from_symbol(const std::string& symbol) const {
    // Simple deterministic hash (same as Python: sum of char codes * 31)
    // This matches Python's simple hash implementation
    uint32_t hash = 0;
    for (unsigned char c : symbol) {
        hash = hash * 31 + c;
    }
    return hash;
}

double MarketDataCache::random_double(uint32_t& seed, double min, double max) {
    // Simple LCG (Linear Congruential Generator)
    seed = seed * 1103515245 + 12345;
    uint32_t random_val = (seed / 65536) % 32768;
    double normalized = static_cast<double>(random_val) / 32768.0;
    return min + normalized * (max - min);
}

}  // namespace quant
