"""Small reference checker for the theory supplement, not a search variant.

The checker trusts a COMPLETE abstract channel table and certified child upper
bounds. It does not certify SAT enumeration or discover a polynomial-size proof.
Hall witnesses can be checked without rerunning a maximum-flow computation.
"""
from dataclasses import dataclass


def submasks(mask):
    value = mask
    while True:
        yield value
        if not value:
            return
        value = (value - 1) & mask


def hall_cut_upper(remaining, buckets, witness):
    """Upper bound on matching, for ANY subset witness of remaining names.

    buckets contains (eligible bitmask, certified child upper capacity).
    Each name outside witness may be used once. Names in witness can only use
    adjacent buckets, whose combined child upper capacities bound their count.
    """
    if remaining < 0 or witness < 0 or witness & ~remaining:
        raise ValueError('Hall witness must be a subset of remaining names')
    total = (remaining & ~witness).bit_count()
    for eligible, upper in buckets:
        if eligible < 0 or upper < 0 or type(upper) is not int:
            raise ValueError('Invalid eligibility or integer upper capacity')
        if eligible & witness:
            total += upper
    return min(remaining.bit_count(), total)


def exhaustive_hall_cut(remaining, buckets):
    """TEST ONLY: exponential witness discovery, not the proposed runtime."""
    return min((hall_cut_upper(remaining, buckets, witness), witness)
               for witness in submasks(remaining))


@dataclass(frozen=True)
class ActionUpper:
    goals: int
    buckets: tuple
    witness: int | None = None


def node_upper(mask, actions, *, complete, mode='lineage'):
    """One proof-DAG step, conditional on valid child upper bounds.

    An incomplete action/channel enumeration always returns the trivial ceiling.
    A matching action without a cut also uses the trivial action ceiling.
    No partial maximum over actions is ever treated as a rejection certificate.
    """
    if mask < 0 or mode not in ('lineage', 'matching'):
        raise ValueError('Invalid mask or mode')
    cap = mask.bit_count()
    if not complete:
        return cap
    upper = 0
    for action in actions:
        if action.goals < 0:
            raise ValueError('Invalid goal mask')
        immediate = mask & action.goals
        remaining = mask & ~action.goals
        buckets = []
        for eligible, child_upper in action.buckets:
            if eligible < 0 or type(child_upper) is not int or child_upper < 0:
                raise ValueError('Invalid child bound')
            child_mask = remaining & eligible
            buckets.append((child_mask, min(child_upper, child_mask.bit_count())))
        if mode == 'lineage':
            tail = sum(c for _, c in buckets)
        elif action.witness is None:
            tail = remaining.bit_count()
        else:
            tail = hall_cut_upper(remaining, buckets, action.witness)
        upper = max(upper, min(cap, immediate.bit_count() + tail))
    return upper
