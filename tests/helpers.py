def has_keys(data, keys):
    return all(map(lambda k: data.has_key(k), keys))

def dict_types(d):
    d = dict(d)
    for key, value in d.items():
        d[key] = type(value)
    return d
