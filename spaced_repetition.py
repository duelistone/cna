# The algorithm below is a blend of the SM-2 algorithm and chessable's 
# starting intervals, along with whatever tweaks I deem appropriate.

# The SM-2 algorithm was created by P.A. Wozniak and is described at
# https://www.supermemo.com/english/ol/sm2.htm
# with the following copyright:
# Algorithm SM-2, (C) Copyright SuperMemo World, 1991.
# http://www.supermemo.com

# Again, though, this algorithm isn't an exact replica, so it may be
# more or less (probably less) efficient. Hopefully, though, it is 
# also more tailored for chess openings. 

import time

def update_spaced_repetition_values(e, c, n, q):
    # e - easiness
    # c - previous number of consecutive correct answers (before this update)
    # n - next time to train, given in minutes after unix epoch
    # q - quality of answer in attempt, from 0-5

    # Update e
    e += 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
    if e < 1: e = 1
    if e > 3.047: e = 3.047

    # Update c
    if q >= 3:
        c += 1
        if c > 15: c = 15
    else:
        c = 0

    # Update n
    now = time.time() / 60
    if q >= 3 and c >= 2:
        n = int(now + 1440 * e ** (c - 2))
        # Max 1 year interval, so that everything is reviewed at least once per year
        if n > now + 1440 * 365:
            n = int(now + 1440 * 365)
    elif c == 1:
        n = int(now + 240)
    # Otherwise, c is 0, and the problem should be repeated, so n is unchanged

    return e, c, n

def read_values(bits):
    # Parses e, c, and n values from polyglot binary data
    n = bits & 0xFFFFFFFF
    bits >>= 32
    c = bits & 15
    bits >>= 4
    e = 1 + bits * 0.001
    return e, c, n

def export_values(e, c, n):
    # Exports value into the correct "weight" and "learn" for polyglot
    # weight - 16 bits, contains e and c values
    # learn - 32 bits, contains n value

    e_steps = int((e - 1) / 0.001)

    # These should never happen, just being careful
    if e_steps > 2047:
        e_steps = 2047 
    if c > 15:
        c = 15
    if n >= 2 ** 32:
        print("Something is wrong with the updating of deadline values.")
        n = 2 ** 32 - 1

    return (e_steps << 4) | c, n

