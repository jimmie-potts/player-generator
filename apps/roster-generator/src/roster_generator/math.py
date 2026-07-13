def clamp_int(value: float, minimum: int = 25, maximum: int = 99) -> int:
    return int(max(minimum, min(maximum, round(float(value)))))
