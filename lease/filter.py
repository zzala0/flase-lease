def format_datetime(value, fmt='%Y년 %m월 %d일 %H:%M'):
    return value.strftime(fmt)

def format_month(value, fmt='%Y.%m'):
    return value.strftime(fmt)

def format_percent(value):
    exvalue = round(value * 100, 3)
    return exvalue
