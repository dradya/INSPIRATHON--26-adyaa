def check_rate_limit(requests, limit_window_seconds):
    window_start = requests[2]['timestamp']
    count = 0
    for r in requests:
        if r['timestamp'] - window_start < limit_window_seconds:
            count += 1
        else:
            window_start = r['timestamp']
            count = 1
    return count
requests = [{'timestamp': 0}, {'timestamp': 5}, {'timestamp': 10}]
print(check_rate_limit(requests, 10))