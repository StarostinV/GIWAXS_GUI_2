from typing import List, Tuple
import logging


class Intervals(object):
    log = logging.getLogger(__name__)

    def __init__(self, size: int):
        self.fitted: List[int] = []
        self.size: int = size
        self.intervals: List[Tuple[int, int]] = []

    def in_interval(self, key: int) -> bool:
        for s, e in self.intervals:
            if s <= key <= e:
                return True
        return False

    def closest(self, key: int):
        min_key, min_distance = None, None
        for k in self.fitted:
            distance = abs(k - key)
            if min_distance is None or distance < min_distance:
                min_distance = distance
                min_key = k
        return min_key

    def add_interval(self, start: int = 0, end: int = -1):
        if end < 0:
            end = self.size + end
        if end <= start or start < 0 or end >= self.size:
            self.log.error(f'Wrong interval: [{start}:{end}].')
            return

        new_intervals = []
        for interval in self.intervals:
            if not (interval[0] > end or interval[1] < start):
                start = min(start, interval[0])
                end = max(end, interval[1])
            else:
                new_intervals.append(interval)
        new_intervals.append((start, end))
        self.intervals = sorted(new_intervals, key=lambda x: x[0])

    def add_key(self, key: int, bottom: bool = True):
        if key < 0 or key >= self.size:
            self.log.error(f'Wrong key {key}')
            return

        self.fitted.append(key)

        if bottom:
            for i, interval in enumerate(self.intervals):
                if interval[0] <= key <= interval[1]:
                    return
                if key < interval[0]:
                    self.intervals[i] = (key, interval[1])
                    return
            self.add_interval(key)
        else:
            for i, interval in enumerate(reversed(self.intervals)):
                if interval[0] <= key <= interval[1]:
                    return
                if key > interval[1]:
                    self.intervals[len(self.intervals) - i - 1] = (interval[0], key)
                    return
            self.add_interval(0, key)

    def del_key(self, key: int, bottom: bool = True):

        for i, interval in enumerate(self.intervals):
            if interval[0] <= key <= interval[1]:
                break
        else:
            return

        if bottom:
            self.intervals[i] = (interval[0], key - 1)
        else:
            self.intervals[i] = (key - 1, interval[1])

        if self.intervals[i][0] > self.intervals[i][1]:
            del self.intervals[i]

        try:
            self.fitted.remove(key)
        except ValueError:
            pass

    def __repr__(self):
        return repr(self.intervals)


if __name__ == '__main__':
    intervals = Intervals(100)
    print(intervals)
    intervals.add_key(0)
    print(intervals)
    intervals.del_key(10)
    print(intervals)
    intervals.add_key(20)
    print(intervals)
    intervals.add_key(15, False)
    print(intervals)
    print(intervals.fitted)
