import random
# from .models import User

def generate_otp_code(length: int = 6) -> str:
    """
    Returns a numeric OTP code as a string.
    Default: 6 digits.
    """
    # 100000 to 999999 for 6-digit OTP
    if length == 6:
        return str(random.randint(100000, 999999))

    # generic fallback for other lengths
    start = 10 ** (length - 1)
    end = (10 ** length) - 1
    return str(random.randint(start, end))

