
-- Cube and Matek autopilots typically make I2C bus 0 available
-- some Pixhawk (and other) autopilots only expose I2C bus 1
-- set the I2C_BUS variable as appropriate for your board
local I2C_BUS           =    0
local RUN_INTERVAL_MS   =  1000
local DO_ADDR        = 0x09
local MAV_SEVERITY_INFO =    6
local LPS_ADDR = 0x5D
local LPS_WHOAMI = 0x0F
local LPS_CTRL_REG2 = 0x11
local LPS_PRES_OUT_XL = 0x28
local LPS_TEMP_OUT_L = 0x2B


local do_i2c = i2c.get_device(I2C_BUS, DO_ADDR)
do_i2c:set_retries(10)

local lps_i2c = i2c.get_device(I2C_BUS, LPS_ADDR)
lps_i2c:set_retries(10)


local function send_DO_data(RETRIES)
    local bytes = {}
    local do_val = -1

    -- get size of DO register
    local size = do_i2c:read_registers(0)
    if not size then 
        gcs:send_text(MAV_SEVERITY_INFO, 'no response from DO device')
        return nil 
    end

    -- retrieve and store register data
    for idx = 1, size do
        bytes[idx - 1] = do_i2c:read_registers(idx)
    end
    
    if bytes then
        do_val = 0
        for x = 0, #bytes do
            do_val = do_val | bytes[x] << (x * 8)
        end
    end

    -- scale do value to voltage
    do_val = do_val * 3300 / 1024 / 11

    if do_val == 0 then
        RETRIES = RETRIES - 1
        if RETRIES <= 0 then
            gcs:send_named_float('p_DO', do_val)
        else
            send_DO_data(RETRIES)
        end
    else
        gcs:send_named_float('p_DO', do_val)
    end

end

local function read_LPS_WHOAMI()

    local byte = lps_i2c:read_registers(LPS_WHOAMI)

    if not byte then
        gcs:send_text(MAV_SEVERITY_INFO, 'no response from LPS device')
        return nil
    end
    return byte
end

local function send_LPS_data()
    local bytes = {}

    -- initiate one shot
    lps_i2c:write_register(LPS_CTRL_REG2, 1)
    -- wait for measurement
    while (lps_i2c:read_registers(LPS_CTRL_REG2) == 1) do
    end
    -- retrieve and store register data
    bytes = lps_i2c:read_registers(LPS_PRES_OUT_XL, 5)

    -- if bytes then
    --     for x = 0, #bytes do
    --         gcs:send_text(MAV_SEVERITY_INFO, 'byte: ' .. tostring(x) .. ': ' .. tostring(bytes[x]))
    --     end
    -- end

    if bytes then
        -- calculate temperature
        temp = 0
        temp = (bytes[5] << 8) | (bytes[4])
        if ((temp & 0x8000) == 0x8000) then
            temp = temp - 0xFFFF
        end
        temp = temp / 100
        gcs:send_named_float('p_temp', temp)

        -- calculate pressure
        pres = 0
        pres = (bytes[3] << 16) | (bytes[2] << 8) | bytes[1]
        if ((pres & 0x800000) == 0x800000) then
            pres = pres - 0xFFFFFF
        end
        pres = pres / 4096
        gcs:send_named_float('p_pres', pres)
    end
end


function update()

    send_LPS_data()

    send_DO_data(10)

    return update, RUN_INTERVAL_MS
end

gcs:send_text(MAV_SEVERITY_INFO, 'Basic I2C_Slave: Script active')

return update, RUN_INTERVAL_MS
