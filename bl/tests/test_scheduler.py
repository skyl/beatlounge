from functools import partial

from twisted.trial.unittest import TestCase

from bl.scheduler import BeatClock, Tempo, Meter, measuresToTicks

import data

class ClockRunner:

    def _runTicks(self, ticks):
        for i in range(ticks):
            self.clock.runUntilCurrent()
            self.clock.tick()


class TestReactor(object):
    running = True

    def __init__(self):
        from twisted.internet import reactor
        self.reactor = reactor
        self.scheduled = []

    def callWhenRunning(self, f, *a, **k):
        f(*a, **k)

    def __getattr__(self, a):
        return getattr(self.reactor, a)


    def callLater(self, later, f, *a, **k):
        self.scheduled.append((later, f, a, k))

class TestInstrument:

    def __init__(self, name, clock, callq):
        self.name = name
        self.clock = clock
        self.callq = callq

    def __call__(self):
        self.callq.append((self.clock.ticks, self.name))


class MeterTests(TestCase):

    def setUp(self):
        self.meterStandard = Meter(4,4)
        self.meter34 = Meter(3,4)
        self.meter54 = Meter(5,4)
        self.meter98 = Meter(9,8)

    def test_beat(self):
        beats = []
        for i in range(96 * 2):
            beats.append(self.meterStandard.beat(i))
        self.assertEquals(beats, data.measure_standard_beats)

        beats = []
        for i in range(96 * 2):
            beats.append(self.meter34.beat(i))
        self.assertEquals(beats, data.measure_34_beats)

        beats = []
        for i in range(96 * 2):
            beats.append(self.meter54.beat(i))
        self.assertEquals(beats, data.measure_54_beats)

        beats = []
        for i in range(96 * 2):
            beats.append(self.meter98.beat(i))
        self.assertEquals(beats, data.measure_98_beats)


class UtilityTests(TestCase):

    def test_measuresToTicks(self):
        ticks = measuresToTicks(0.25)
        self.assertEquals(ticks, 24)
        ticks = measuresToTicks(0.125)
        self.assertEquals(ticks, 12)
        ticks = measuresToTicks(1)
        self.assertEquals(ticks, 96)


    def test_measuresToTicksMeterRelativity(self):
        meter34 = Meter(3,4)
        meter118 = Meter(11,8)
        ticks = measuresToTicks(1.5)
        self.assertEquals(ticks, 144)
        ticks = measuresToTicks(0.25, meter34)
        self.assertEquals(ticks, 24)
        ticks = measuresToTicks(1, meter34)
        self.assertEquals(ticks, 72)
        ticks = measuresToTicks(1.25, meter34)
        self.assertEquals(ticks, 96)
        ticks = measuresToTicks(1, meter118)
        self.assertEquals(ticks, 12 * 11)
        ticks = measuresToTicks(4.25, meter118)
        self.assertEquals(ticks, 12 * 11 * 4 + 24)

    def test_measuresToTicksWithTuples(self):
        meter98 = Meter(9, 8)
        standardMeter = Meter(4, 4)
        ticks = measuresToTicks((1,4), meter98)
        self.assertEquals(ticks, 204)
        ticks = measuresToTicks((1,3), standardMeter)
        self.assertEquals(ticks, 168)
        ticks = measuresToTicks((2,1.5), standardMeter)
        self.assertEquals(ticks, 228)
        ticks = measuresToTicks((2,1.5), meter98)
        self.assertEquals(ticks, 252)

class ClockTests(TestCase, ClockRunner):


    def setUp(self):
        self.meters = [ Meter(4,4), Meter(3,4) ]
        self.meterStandard = self.meters[0]
        self.meter34 = self.meters[1]
        self.clock = BeatClock(Tempo(135), meters=self.meters, reactor=TestReactor())


    def test_defaultMeterIsStandard(self):
        clock = BeatClock(Tempo(120))
        self.assertEquals(len(clock.meters), 1)
        meter = clock.meters[0]
        self.assertEquals(meter.length, 4)
        self.assertEquals(meter.division, 4)
        self.assertEquals(meter.number, 1)


    def test_startLater(self):
        called = []

        instr1 = TestInstrument('f1', self.clock, called)

        self.clock.schedule(instr1).startLater(0, 0.25)
        self._runTicks(96 * 2)

        expected = [(0, 'f1'), (24, 'f1'), (48, 'f1'), (72, 'f1'), (96, 'f1'),
                    (120, 'f1'), (144, 'f1'), (168, 'f1'), (192, 'f1')]
        self.assertEquals(called, expected)

        called[:] = []

        instr2 = TestInstrument('f2', self.clock, called)

        self.clock.schedule(instr2).startLater(1.0, 1.0 / 3)
        self._runTicks(96 * 2)
        expected = [(216, 'f1'), (240, 'f1'), (264, 'f1'), (288, 'f2'), (288, 'f1'),
                    (312, 'f1'), (320, 'f2'), (336, 'f1'), (352, 'f2'), (360, 'f1'),
                    (384, 'f2'), (384, 'f1')]
        self.assertEquals(called, expected)


    def test_startLaterWithMeter(self):
        called = []

        instr1 = TestInstrument('f1', self.clock, called)
        instr2 = TestInstrument('f2', self.clock, called)

        self.clock.schedule(instr1).startLater(1.0, 0.25, meter=self.meterStandard)
        self.clock.schedule(instr2).startLater(1.0, 0.25, meter=self.meter34)

        self._runTicks(96 * 2)

        expected = [(72, 'f2'), (96, 'f2'), (96, 'f1'), (120, 'f2'), (120, 'f1'),
                    (144, 'f2'), (144, 'f1'), (168, 'f2'), (168, 'f1'),
                    (192, 'f2'), (192, 'f1')]
        self.assertEquals(len(called), len(expected))
        self.assertEquals(set(called), set(expected))

    def test_stopLater(self):
        called = []

        instr1 = TestInstrument('f1', self.clock, called)
        instr2 = TestInstrument('f2', self.clock, called)

        self.clock.schedule(instr1).startLater(1.0, 0.25, meter=self.meterStandard).stopLater(3.5)
        self._runTicks(96 * 5)
        expected = [
            (96,  'f1'),
            (120, 'f1'),
            (144, 'f1'),
            (168, 'f1'),
            (192, 'f1'),
            (216, 'f1'),
            (240, 'f1'),
            (264, 'f1'),
            (288, 'f1'),
            (312, 'f1')]


        self.assertEquals(len(called), len(expected))
        self.assertEquals(called, expected)

        called[:] = []

        self.clock.schedule(instr2).startLater(0, 0.25, meter=self.meter34).stopLater(2.5, meter=self.meter34)
        self._runTicks(96 * 5)
        expected = [(504, 'f2'), (528, 'f2'), (552, 'f2'), (576, 'f2'), (600, 'f2')]
        self.assertEquals(called, expected)

    def test_bindMeter(self):
        called = []

        instr1 = TestInstrument('f1', self.clock, called)
        instr2 = TestInstrument('f2', self.clock, called)

        self.clock.schedule(instr1).bindMeter(self.meterStandard).startLater(1.0, 0.25).stopLater(3.5)
        self._runTicks(96 * 5)
        expected = [
            (96,  'f1'),
            (120, 'f1'),
            (144, 'f1'),
            (168, 'f1'),
            (192, 'f1'),
            (216, 'f1'),
            (240, 'f1'),
            (264, 'f1'),
            (288, 'f1'),
            (312, 'f1')]


        self.assertEquals(len(called), len(expected))
        self.assertEquals(called, expected)

        called[:] = []

        self.clock.schedule(instr2).bindMeter(self.meter34).startLater(0, 0.25).stopLater(2.5)
        self._runTicks(96 * 5)
        expected = [(504, 'f2'), (528, 'f2'), (552, 'f2'), (576, 'f2'), (600, 'f2')]
        self.assertEquals(called, expected)


    def test_setTempo(self):
        self.clock.setTempo(Tempo(60))
        interval_before = 60. / self.clock.tempo.tpm
        called = []
        self.clock.startTicking()
        self.clock.on_stop.addCallback(called.append)
        self.clock.setTempo(Tempo(120))
        self.assertEquals(len(called), 1)
        self.assertEquals(60. / self.clock.tempo.tpm, interval_before / 2.)
        self.clock.task.stop()


    def test_nudge(self):
        self.clock.startTicking()
        self.clock.nudge()
        self.assertEquals(self.clock.reactor.scheduled,
            [(0.1, self.clock.task.start, (60. / self.clock.tempo.tpm, True), {})])
        self.clock.task.start(1, True)
        self.clock.nudge(pause=0.5)
        self.assertEquals(self.clock.reactor.scheduled,
            [(0.1, self.clock.task.start, (60. / self.clock.tempo.tpm, True), {}),
             (0.5, self.clock.task.start, (60. / self.clock.tempo.tpm, True), {})])


class TempoTests(TestCase):

    def test_basic_tempo(self):

        tempo = Tempo()
        self.assertEquals(tempo.bpm, 120)
        self.assertEquals(tempo.tpb, 24)
        self.assertEquals(tempo.tpm, 2880)

        tempo.reset(bpm=150)
        self.assertEquals(tempo.bpm, 150)
        self.assertEquals(tempo.tpb, 24)
        self.assertEquals(tempo.tpm, 3600)

        tempo.reset(tpb=48)
        self.assertEquals(tempo.bpm, 150)
        self.assertEquals(tempo.tpb, 48)
        self.assertEquals(tempo.tpm, 7200)

        tempo.reset(tpb=24, bpm=60)
        self.assertEquals(tempo.bpm, 60)
        self.assertEquals(tempo.tpb, 24)
        self.assertEquals(tempo.tpm, 1440)

        tempo.reset(tpm=14400)
        self.assertEquals(tempo.bpm, 600)
        self.assertEquals(tempo.tpb, 24)
        self.assertEquals(tempo.tpm, 14400)


