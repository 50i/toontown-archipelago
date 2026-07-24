def get_ap_mark_scope():
    av = getattr(base, 'localAvatar', None)
    slot_data = getattr(av, 'slotData', {}) or {}
    seed = slot_data.get('seed')
    slot_name = getattr(av, 'slotName', '') or slot_data.get('name', '')
    if seed is None and hasattr(av, 'getLastSeed'):
        seed = av.getLastSeed()
    if seed is None:
        seed = 'no-seed'
    return f"{seed}:{slot_name}"


def get_marked_hoods(setting_key):
    raw = base.settings.get(setting_key)
    if isinstance(raw, dict):
        return list(raw.get(get_ap_mark_scope(), []))
    return []


def set_marked_hoods(setting_key, hoods):
    raw = base.settings.get(setting_key)
    scoped = dict(raw) if isinstance(raw, dict) else {}
    scoped[get_ap_mark_scope()] = sorted({int(hood) for hood in hoods})
    base.settings.set(setting_key, scoped)
    base.settings.write()


def is_hood_marked(setting_key, hood_id):
    return int(hood_id) in get_marked_hoods(setting_key)
