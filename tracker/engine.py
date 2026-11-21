"""Game-independent, monotonic achievement rules. No game files are written."""
import math
import time

def evaluate(rule, metrics, target):
    values = [metrics.get(key) for key in rule['flags']]
    if any(v is None for v in values):
        return None  # Missing/unsupported signals never count as zero or true.
    if any(isinstance(v, (str, list, dict)) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        return None
    op = rule['op']
    if op in ('any', 'all', 'count'):
        if any(v not in (0, 1) for v in values):
            return None
        observed = sum(v == 1 for v in values)
        needed = len(values) if op == 'all' else rule.get('threshold', 1)
    elif op in ('number', 'sum'):
        observed = sum(values) if op == 'sum' else values[0]
        needed = rule['threshold']
    else:
        raise ValueError('Unknown rule operator: ' + op)
    return min(target, int(observed)) if target == needed else (target if observed >= needed else 0)

def apply_rules(previous, manifest, metrics, definitions, observed_at=None):
    result = dict(previous)
    observed_at = observed_at or int(time.time())
    for key, rule in manifest['rules'].items():
        if key not in definitions:
            continue
        target = definitions[key]['target']
        current = evaluate(rule, metrics, target)
        if current is None or current <= 0:
            continue
        old = result.get(key, {})
        current = max(old.get('current', 0), current)
        entry = {'current': current, 'source': 'cloud' if old.get('source') == 'cloud' and current == old.get('current') else 'automatic', 'adapter': manifest['id']}
        if current >= target:
            entry['unlockedAt'] = old.get('unlockedAt', observed_at)
        result[key] = entry
    return result
