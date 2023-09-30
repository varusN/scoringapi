import hashlib
import json
import time

class TimeOutException(Exception):
   pass

def get_score(logging, store, phone, email, birthday=None, gender=None, first_name=None, last_name=None):
    key_parts = [
        first_name or "",
        last_name or "",
        phone or "",
        email or "",
        birthday.strftime("%Y%m%d") if birthday is not None else "",
    ]
    key = "uid:" + hashlib.md5("".join(key_parts).encode()).hexdigest()
    # try get from cache,
    # fallback to heavy calculation in case of cache miss
    try:
        score = store.cache_get(key) or 0
    except Exception:
        score = 0
    if score:
        logging.info('Data found in cache')
        return float(score)
    if phone:
        score += 1.5
    if email:
        score += 1.5
    if birthday and gender:
        score += 1.5
    if first_name and last_name:
        score += 0.5
    # cache for 60 minutes
    try:
        store.cache_set(key, score, 60 * 60)
    except Exception:
        pass
    return score

def get_interests(logging, store, cid):
    try:
        r = store.get(cid)
    except Exception:
        logging.info('DB connection issue, request is rejected')
        raise ConnectionError
    return r if r else []


