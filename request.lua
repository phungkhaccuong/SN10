wrk.method = "POST"
json_input = [[
{
    "assets_and_pools": {
        "total_assets": 2.0,
        "pools": {
            "0": {
                "pool_id": "0",
                "base_rate": 0.04,
                "base_slope": 0.012,
                "kink_slope": 0.312,
                "optimal_util_rate": 0.9,
                "borrow_amount": 0.6,
                "reserve_size": 1.0
            },
            "1": {
                "pool_id": "1",
                "base_rate": 0.05,
                "base_slope": 0.065,
                "kink_slope": 0.456,
                "optimal_util_rate": 0.75,
                "borrow_amount": 0.75,
                "reserve_size": 1.0
            },
            "2": {
                "pool_id": "2",
                "base_rate": 0.03,
                "base_slope": 0.036,
                "kink_slope": 0.665,
                "optimal_util_rate": 0.7,
                "borrow_amount": 0.85,
                "reserve_size": 1.0
            },
            "3": {
                "pool_id": "3",
                "base_rate": 0.04,
                "base_slope": 0.082,
                "kink_slope": 0.936,
                "optimal_util_rate": 0.85,
                "borrow_amount": 0.65,
                "reserve_size": 1.0
            },
            "4": {
                "pool_id": "4",
                "base_rate": 0.02,
                "base_slope": 0.071,
                "kink_slope": 0.566,
                "optimal_util_rate": 0.75,
                "borrow_amount": 0.7,
                "reserve_size": 1.0
            },
            "5": {
                "pool_id": "5",
                "base_rate": 0.01,
                "base_slope": 0.012,
                "kink_slope": 0.803,
                "optimal_util_rate": 0.7,
                "borrow_amount": 0.8,
                "reserve_size": 1.0
            },
            "6": {
                "pool_id": "6",
                "base_rate": 0.03,
                "base_slope": 0.05,
                "kink_slope": 0.665,
                "optimal_util_rate": 0.75,
                "borrow_amount": 0.8,
                "reserve_size": 1.0
            },
            "7": {
                "pool_id": "7",
                "base_rate": 0.01,
                "base_slope": 0.012,
                "kink_slope": 0.606,
                "optimal_util_rate": 0.9,
                "borrow_amount": 0.9,
                "reserve_size": 1.0
            },
            "8": {
                "pool_id": "8",
                "base_rate": 0.05,
                "base_slope": 0.024,
                "kink_slope": 0.852,
                "optimal_util_rate": 0.7,
                "borrow_amount": 0.9,
                "reserve_size": 1.0
            },
            "9": {
                "pool_id": "9",
                "base_rate": 0.05,
                "base_slope": 0.044,
                "kink_slope": 0.402,
                "optimal_util_rate": 0.65,
                "borrow_amount": 0.85,
                "reserve_size": 1.0
            }
        }
    },
    "allocations": {
        "0": 0.039,
        "1": 0.085,
        "2": 0.071,
        "3": 0.044,
        "4": 0.032,
        "5": 0.063,
        "6": 0.038,
        "7": 0.012,
        "8": 0.046,
        "9": 0.074
    },
    "name": "AllocateAssets",
    "large": "PLACEHOLDER"
}
]]
local large_string = string.rep("a", 100000)
wrk.body = json_input:gsub('"PLACEHOLDER"', '"' .. large_string .. '"')
local headers = {
    ["content-type"] = "application/json",
    ["name"] = "AllocateAssets",
    ["timeout"] = "12.0",
    ["bt_header_axon_ip"] = "178.162.164.32",
    ["bt_header_axon_port"] = "8210",
    ["bt_header_axon_hotkey"] = "",
    ["bt_header_dendrite_ip"] = "14.248.67.26",
    ["bt_header_dendrite_version"] = "710",
    ["bt_header_dendrite_nonce"] = "3764294269428166",
    ["bt_header_dendrite_uuid"] = "b7d4b2ba-1596-11ef-bd94-caeff55321f6",
    ["bt_header_dendrite_hotkey"] = "5D5CP5jL1MseaWcY7GsJXRYhTjAYkaLwaHEtiqu7PzWCcEjz",
    ["bt_header_dendrite_signature"] = "0x621ca3bf18e8ca4bb403d0b60cc6c98e4505dfa49cac28e895eea9efceca45615fd77d92c8dfa0979ff73d818fcda286b450336a755680687e777cab18b62f80",
    ["bt_header_input_obj_assets_and_pools"] = "e30=",
    ["header_size"] = "640",
    ["total_size"] = "9895",
    ["computed_body_hash"] = "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a"
}
-- Convert the headers table to a format wrk can use
wrk.headers = {}
for k, v in pairs(headers) do
    wrk.headers[k] = v
end

-- AxonInfo( /ipv4/178.162.164.32:8210, 5Ehu9LizP2jdKm7RfBfgnikmG32PAEwuqtyJXJpoPS9dooSW, 5F4z13uHuyhMGHRiS2uBf1tCY8NTLKvxEpPq7K1okhz9z2Dp, 710 )