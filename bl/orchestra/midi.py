from itertools import cycle

from bl.utils import getClock
from bl.instrument.interfaces import IMIDIInstrument
from bl.orchestra.base import SchedulePlayer


class CallMemo(object):

    def __init__(self, ugen):
        self.ugen = ugen

    def __call__(self):
        self.value = self.ugen()
        return self.value

    def lastValue(self):
        return self.value


def schedule(time, func, args):
    def gen():
        while 1:
            yield (time, func, args)
    return gen()


class OneSchedulePlayerMixin(object):

    schedulePlayer = None

    def resumePlaying(self):
        self.schedulePlayer.resumePlaying()

    def pausePlaying(self):
        self.schedulePlayer.pausePlaying()


class Player(OneSchedulePlayerMixin):

    def __init__(self, instr, notes, velocity=None, release=None,
                 interval=(1,8), time=None, clock=None):
        self.instr = IMIDIInstrument(instr)
        self.clock = getClock(clock)
        if velocity is None:
            velocity = cycle([127]).next
        self.notes = notes
        self.velocity = velocity
        self.release = release
        if time is None:
            if type(interval) in (list, tuple):
                interval = self.clock.meter.dtt(*interval)
            def time():
                current = 0
                while 1:
                    yield current
                    current += interval
            time = time().next
        timeMemo = CallMemo(time)
        noteMemo = CallMemo(notes)
        noteon = lambda note, velocity: self.instr.noteon(note, velocity)
        noteonSchedule = schedule(timeMemo, noteon,
                                  {'note': noteMemo, 'velocity': velocity})
        self.schedulePlayer = SchedulePlayer(noteonSchedule, self.clock)
        if self.release:
            self.noteoff = lambda note: self.instr.noteoff(note)
            self.schedulePlayer.addChild(((self._scheduleNoteoff,
                                     {'note': noteMemo.lastValue,
                                      'when': self.release})
                                     for i in cycle([1])))

    def _scheduleNoteoff(self, note, when):
        if when is None:
            return
        self.clock.callLater(when, self.noteoff, note)

