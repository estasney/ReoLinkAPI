def c__motions2intervals_idx(list motions):
    cdef list motion_intervals = []
    cdef (int, int) motion_idx = (0, 0)
    cdef int x_idx = -1
    cdef bint x = False
    cdef int motion_list_size = len(motions)
    cdef int i = 0


    while i < motion_list_size:
        x = motions[i]
        if x_idx == -1:  # Looking for start of interval
            if x:
                x_idx = i
            i += 1
            continue
        if x:  # Don't close interval, continue
            i += 1
            continue
        if not x:
            motion_idx = (x_idx, i)
            motion_intervals.append(motion_idx)
            x_idx = -1
            i += 1
            continue

    return motion_intervals












