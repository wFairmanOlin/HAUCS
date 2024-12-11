# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT
"""
`lps28`
================================================================================

LPS28 pressure sensor drive for CircuitPython


* Author(s): Jose D. Montoya


"""

from micropython import const
from adafruit_bus_device import i2c_device
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from adafruit_register.i2c_bits import RWBits, ROBits
from adafruit_register.i2c_bit import RWBit

try:
    from busio import I2C
except ImportError:
    pass


__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/jposada202020/CircuitPython_LPS28.git"


_REG_WHOAMI = const(0x0F)
_INTERRUPT_CFG = const(0x0B)
_CTRL_REG1 = const(0x10)
_CTRL_REG2 = const(0x11)
_INT_SOURCE = const(0x24)
_PRESS_OUT_XL = const(0x28)
_TEMP_OUT_L = const(0x2B)
_THS_P_L = const(0x0C)


# Data Rate
ONE_SHOT = const(0b0000)
RATE_1_HZ = const(0b0001)
RATE_4_HZ = const(0b0010)
RATE_10_HZ = const(0b0011)
RATE_25_HZ = const(0b0100)
RATE_50_HZ = const(0b0101)
RATE_75_HZ = const(0b0110)
RATE_100_HZ = const(0b0111)
RATE_200_HZ = const(0b1000)
data_rate_values = (
    ONE_SHOT,
    RATE_1_HZ,
    RATE_4_HZ,
    RATE_10_HZ,
    RATE_25_HZ,
    RATE_50_HZ,
    RATE_75_HZ,
    RATE_100_HZ,
    RATE_200_HZ,
)

# Resolution
RES_4 = const(0b000)
RES_8 = const(0b001)
RES_16 = const(0b010)
RES_32 = const(0b011)
RES_64 = const(0b100)
RES_128 = const(0b101)
RES_512 = const(0b111)
resolution_values = (RES_4, RES_8, RES_16, RES_32, RES_64, RES_128, RES_512)

FULL_SCALE = const(0b1)
NORMAL = const(0b0)
full_scale_values = (NORMAL, FULL_SCALE)


class LPS28:
    """Driver for the LPS28 Sensor connected over I2C.

    :param ~busio.I2C i2c_bus: The I2C bus the LPS28 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x5D`

    :raises RuntimeError: if the sensor is not found

    **Quickstart: Importing and using the device**

    Here is an example of using the :class:`LPS28` class.
    First you will need to import the libraries to use the sensor

    .. code-block:: python

        import board
        import lps28

    Once this is done you can define your `board.I2C` object and define your sensor object

    .. code-block:: python

        i2c = board.I2C()  # uses board.SCL and board.SDA
        lps28 = LPS28.lps28(i2c)

    Now you have access to the attributes

    .. code-block:: python

        press = lps28.pressure

    """

    _device_id = ROUnaryStruct(_REG_WHOAMI, "B")

    _raw_temperature = ROUnaryStruct(_TEMP_OUT_L, "<h")
    _raw_pressure = ROBits(24, _PRESS_OUT_XL, 0, 3)

    _pressure_threshold = UnaryStruct(_THS_P_L, "<H")

    # INT_SOURCE(0x24)
    # | BOOT-ON | 0 | 0 | 0 | 0 | IA | PL | PH |
    _pressure_low = RWBit(_INTERRUPT_CFG, 1)
    _pressure_high = RWBit(_INTERRUPT_CFG, 0)

    # INT status registers (0xB0)
    # | AUTOREFP | RESET_ARP | AUTOZERO | RESET_AZ | ---- | LIR | PLE | PHE |
    _interrupt_low = RWBit(_INTERRUPT_CFG, 1)
    _interrupt_high = RWBit(_INTERRUPT_CFG, 0)

    # Register CTRL_REG1 (0x10)
    # | ---- | ODR(3) | ODR(2) | ODR(1) | ODR(0) | AVG(2) | AVG(1) | AVG(0)|
    _resolution = RWBits(3, _CTRL_REG1, 0)
    _data_rate = RWBits(4, _CTRL_REG1, 3)

    # Register CTRL_REG2 (0x11)
    # | BOOT | FS_MODE | LFPF_CFG | EN_LPFP | BDU | SWRESET | ---- | ONESHOOT|
    _full_scale = RWBits(1, _CTRL_REG2, 6)
    _one_shot = RWBits(1, _CTRL_REG2, 0)

    def __init__(self, i2c_bus: I2C, address: int = 0x5D) -> None:
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)

        if self._device_id != 0xB4:
            raise RuntimeError("Failed to find LPS28")

        self._data_rate = RATE_10_HZ
        self._resolution = RES_4

    @property
    def data_rate(self) -> str:
        """
        Sensor data_rate

        +-------------------------------+--------------------+
        | Mode                          | Value              |
        +===============================+====================+
        | :py:const:`lps28.ONE_SHOT`    | :py:const:`0b0000` |
        +-------------------------------+--------------------+
        | :py:const:`lps28.RATE_1_HZ`   | :py:const:`0b0001` |
        +-------------------------------+--------------------+
        | :py:const:`lps28.RATE_4_HZ`   | :py:const:`0b0010` |
        +-------------------------------+--------------------+
        | :py:const:`lps28.RATE_10_HZ`  | :py:const:`0b0011` |
        +-------------------------------+--------------------+
        | :py:const:`lps28.RATE_25_HZ`  | :py:const:`0b0100` |
        +-------------------------------+--------------------+
        | :py:const:`lps28.RATE_50_HZ`  | :py:const:`0b0101` |
        +-------------------------------+--------------------+
        | :py:const:`lps28.RATE_75_HZ`  | :py:const:`0b0110` |
        +-------------------------------+--------------------+
        | :py:const:`lps28.RATE_100_HZ` | :py:const:`0b0111` |
        +-------------------------------+--------------------+
        | :py:const:`lps28.RATE_200_HZ` | :py:const:`0b1000` |
        +-------------------------------+--------------------+
        """
        values = (
            "ONE_SHOT",
            "RATE_1_HZ",
            "RATE_4_HZ",
            "RATE_10_HZ",
            "RATE_25_HZ",
            "RATE_50_HZ",
            "RATE_75_HZ",
            "RATE_100_HZ",
            "RATE_200_HZ",
        )
        return values[self._data_rate]

    @data_rate.setter
    def data_rate(self, value: int) -> None:
        if value not in data_rate_values:
            raise ValueError("Value must be a valid data_rate setting")
        self._data_rate = value

    @property
    def resolution(self) -> None:
        """
        Sensor resolution

        +---------------------------+-------------------+
        | Mode                      | Value             |
        +===========================+===================+
        | :py:const:`lps28.RES_4`   | :py:const:`0b000` |
        +---------------------------+-------------------+
        | :py:const:`lps28.RES_8`   | :py:const:`0b001` |
        +---------------------------+-------------------+
        | :py:const:`lps28.RES_16`  | :py:const:`0b010` |
        +---------------------------+-------------------+
        | :py:const:`lps28.RES_32`  | :py:const:`0b011` |
        +---------------------------+-------------------+
        | :py:const:`lps28.RES_64`  | :py:const:`0b100` |
        +---------------------------+-------------------+
        | :py:const:`lps28.RES_128` | :py:const:`0b101` |
        +---------------------------+-------------------+
        | :py:const:`lps28.RES_512` | :py:const:`0b111` |
        +---------------------------+-------------------+
        """
        values = (
            "RES_4",
            "RES_8",
            "RES_16",
            "RES_32",
            "RES_64",
            "RES_128",
            "",
            "RES_512",
        )
        return values[self._resolution]

    @resolution.setter
    def resolution(self, value: int) -> None:
        if value not in resolution_values:
            raise ValueError("Value must be a valid resolution setting")
        self._resolution = value

    @property
    def full_scale(self) -> None:
        """
        Sensor full_scale
        (0: mode 1, full scale up to 1260 hPa; 1: mode 2, full scale up to 4060 hPa)

        +--------------------------------+-------------------+
        | Mode                           | Value             |
        +================================+===================+
        | :py:const:`lps28.FULL_SCALE`   | :py:const:`0b1`   |
        +--------------------------------+-------------------+
        | :py:const:`lps28.NORMAL`       | :py:const:`0b0`   |
        +--------------------------------+-------------------+

        """
        values = ("NORMAL", "FULL_SCALE")
        return values[self._full_scale]

    @full_scale.setter
    def full_scale(self, value: int) -> None:
        if value not in full_scale_values:
            raise ValueError("Value must be a valid scale setting")
        self._full_scale = value

    @property
    def pressure(self) -> float:
        """
        Pressure value in hPa
        """
        if self._data_rate == ONE_SHOT:
            self._one_shot = 0b1
            #wait for one shot sample to finish
            while self._one_shot == 0b1:
                pass

        pressure_scale = 4096 if self._full_scale == 0 else 2048
        pressure_reading = self._raw_pressure
        pressure = self._twos_comp(pressure_reading, 24) / pressure_scale

        return pressure

    @property
    def temperature(self) -> float:
        """The current temperature measurement in Celsius"""
        if self._data_rate == ONE_SHOT:
            self._one_shot = 0b1
            #wait for one shot sample to finish
            while self._one_shot == 0b1:
                pass

        return self._raw_temperature / 100

    @property
    def pressure_temperature(self) -> Tuple[float, float]:
        if self._data_rate == ONE_SHOT:
            self._one_shot = 0b1
            #wait for one shot sample to finish
            while self._one_shot == 0b1:
                pass

        pressure_scale = 4096 if self._full_scale == 0 else 2048
        pressure_reading = self._raw_pressure
        pressure = self._twos_comp(pressure_reading, 24) / pressure_scale
        temperature = self._raw_temperature / 100

        return pressure, temperature


    @property
    def high_threshold_enabled(self) -> bool:
        """Set to `True` or `False` to enable or disable the high pressure threshold"""
        value = {0: False, 1: True}
        return value[self._interrupt_high]

    @high_threshold_enabled.setter
    def high_threshold_enabled(self, value: bool) -> None:
        if value not in (True, False):
            raise ValueError("value must be a valid setting")
        self._interrupt_high = value

    @property
    def low_threshold_enabled(self) -> bool:
        """Set to `True` or `False` to enable or disable the low pressure threshold."""
        value = {0: False, 1: True}
        return value[self._interrupt_low]

    @low_threshold_enabled.setter
    def low_threshold_enabled(self, value: bool) -> None:
        if value not in (True, False):
            raise ValueError("value must be a valid setting")
        self._interrupt_low = value

    @property
    def high_threshold_exceeded(self) -> bool:
        """Returns `True` if the pressure high threshold has been exceeded.
        Must be enabled by setting :attr:`high_threshold_enabled` to `True`
        and setting a :attr:`pressure_threshold`."""
        return self._pressure_high

    @property
    def low_threshold_exceeded(self) -> bool:
        """Returns `True` if the pressure low threshold has been exceeded.
        Must be enabled by setting :attr:`high_threshold_enabled`
        to `True` and setting a :attr:`pressure_threshold`."""
        return self._pressure_low

    @property
    def pressure_threshold(self) -> float:
        """The high pressure threshold. Use :attr:`high_threshold_enabled`
        or :attr:`high_threshold_enabled` to use it"""
        options = (16, 8)
        return self._pressure_threshold / options[self._full_scale]

    @pressure_threshold.setter
    def pressure_threshold(self, value: float) -> None:
        """The high value threshold"""
        options = (16, 8)
        self._pressure_threshold = value * options[self._full_scale]

    @staticmethod
    def _twos_comp(val: int, bits: int) -> int:

        if val & (1 << (bits - 1)) != 0:
            return val - (1 << bits)
        return val
