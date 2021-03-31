def has_keys(data, keys):
    return all(map(lambda k: k in data, keys))


def dict_types(d):
    d = dict(d)
    for key, value in d.items():
        d[key] = type(value)
    return d
