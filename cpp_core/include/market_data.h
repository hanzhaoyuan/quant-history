#pragma once
#include "bar.h"
#include <vector>
#include <map>
#include <string>
#include <cstdint>

namespace quant {

class MarketDataCache {
public:
    MarketDataCache();
    ~MarketDataCache();

    // Initialize data for a symbol (generate 100 trading days of minute bars)
    void initialize(const std::string& symbol);

    // Get all bars for a symbol (read-only)
    const std::vector<Bar>& get_bars(const std::string& symbol);

    // Check if symbol exists in cache
    bool has_symbol(const std::string& symbol) const;

private:
    std::map<std::string, std::vector<Bar>> cache_;

    // Generate minute bars for a single trading day (240 bars)
    // date_ts: timestamp at 00:00:00 of the trading day (UTC+8)
    std::vector<Bar> generate_trading_day(
        const std::string& symbol,
        int64_t date_ts,
        uint32_t& seed
    );

    // Generate a single minute bar
    Bar generate_bar(
        const std::string& symbol,
        int64_t eob_ts,
        uint32_t& seed
    );

    // Check if a date is a trading day (Mon-Fri, simplified, no holidays)
    bool is_trading_day(int year, int month, int day) const;

    // Get deterministic seed from symbol
    uint32_t get_seed_from_symbol(const std::string& symbol) const;

    // Simple LCG random number generator for deterministic results
    double random_double(uint32_t& seed, double min, double max);
};

}  // namespace quant
