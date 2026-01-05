"""Debug seed generation"""
import hashlib

# Python side
def get_seed_python(symbol: str) -> int:
    hash_bytes = hashlib.md5(symbol.encode()).digest()
    return int.from_bytes(hash_bytes[:4], 'little')

# C++ side uses std::hash<std::string>
# Let's check Python's seed
symbol = '000001.SH'
seed_py = get_seed_python(symbol)
print(f"Python seed for '{symbol}': {seed_py}")

# Test LCG
seed_state = [seed_py]

def lcg_random(seed_state, min_val, max_val):
    seed_state[0] = (seed_state[0] * 1103515245 + 12345) & 0xFFFFFFFF
    random_val = ((seed_state[0] // 65536) % 32768)
    normalized = random_val / 32768.0
    return min_val + normalized * (max_val - min_val)

print("\nFirst 10 random numbers from Python LCG:")
test_seed = [seed_py]
for i in range(10):
    val = lcg_random(test_seed, -10.0, 10.0)
    print(f"  {i}: {val:.10f}")
