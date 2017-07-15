#cython: boundscheck=False
#cython: wraparound=False

from libc.stdlib cimport abs as c_abs

cimport cpython.array


# TODO: I don't know how can I not return any value (void doesn't work)
cpdef int undo_filter_sub(int filter_unit, unsigned char[:] scanline,
                          unsigned char[:] previous, unsigned char[:] result) nogil:
    """Undo sub filter."""

    cdef int l = result.shape[0]
    cdef int ai = 0
    cdef unsigned char x, a

    # Loops starts at index fu.  Observe that the initial part
    # of the result is already filled in correctly with
    # scanline.
    for i in range(filter_unit, l):
        x = scanline[i]
        a = result[ai]
        result[i] = (x + a) & 0xff
        ai += 1
    return 0


cpdef int undo_filter_up(int filter_unit, unsigned char[:] scanline,
                         unsigned char[:] previous, unsigned char[:] result) nogil:
    """Undo up filter."""

    cdef int i
    cdef int l = result.shape[0]
    cdef unsigned char x, b

    for i in range(l):
        x = scanline[i]
        b = previous[i]
        result[i] = (x + b) & 0xff
    return 0


cpdef int undo_filter_average(int filter_unit, unsigned char[:] scanline,
                              unsigned char[:] previous, unsigned char[:] result) nogil:
    """Undo up filter."""

    cdef int i, ai
    cdef int l = result.shape[0]
    cdef unsigned char x, a, b

    ai = -filter_unit
    for i in range(l):
        x = scanline[i]
        if ai < 0:
            a = 0
        else:
            a = result[ai]
        b = previous[i]
        result[i] = (x + ((a + b) >> 1)) & 0xff
        ai += 1
    return 0


cpdef int undo_filter_paeth(int filter_unit, unsigned char[:] scanline,
                            unsigned char[:] previous, unsigned char[:] result) nogil:
    """Undo Paeth filter."""

    # Also used for ci.
    cdef int ai = -filter_unit
    cdef int l = result.shape[0]
    cdef int i, pa, pb, pc, p
    cdef unsigned char x, a, b, c, pr

    for i in range(l):
        x = scanline[i]
        if ai < 0:
            a = c = 0
        else:
            a = result[ai]
            c = previous[ai]
        b = previous[i]
        p = a + b - c
        pa = c_abs(p - a)
        pb = c_abs(p - b)
        pc = c_abs(p - c)
        if pa <= pb and pa <= pc:
            pr = a
        elif pb <= pc:
            pr = b
        else:
            pr = c
        result[i] = (x + pr) & 0xff
        ai += 1
    return 0


cpdef int convert_rgb_to_rgba(unsigned char[:] row, unsigned char[:] result) nogil:
    cdef int i, l, j, k
    l = min(row.shape[0] / 3, result.shape[0] / 4)
    for i in range(l):
        j = i * 3
        k = i * 4
        result[k] = row[j]
        result[k + 1] = row[j + 1]
        result[k + 2] = row[j + 2]
    return 0


cpdef int convert_l_to_rgba(unsigned char[:] row, unsigned char[:] result) nogil:
    cdef int i, l, j, k, lum
    l = min(row.shape[0], result.shape[0] / 4)
    for i in range(l):
        j = i
        k = i * 4
        lum = row[j]
        result[k] = lum
        result[k + 1] = lum
        result[k + 2] = lum
    return 0


cpdef int convert_la_to_rgba(unsigned char[:] row, unsigned char[:] result) nogil:
    cdef int i, l, j, k, lum
    l = min(row.shape[0] / 2, result.shape[0] / 4)
    for i in range(l):
        j = i * 2
        k = i * 4
        lum = row[j]
        result[k] = lum
        result[k + 1] = lum
        result[k + 2] = lum
        result[k + 3] = row[j + 1]
    return 0
