from pyo import (
    Sine, Port, Sig, Server, Disto, Osc, HarmTable,
    Adsr, SawTable
)

from bl.utils import getClock
from bl.music.structures.notes import twelve_tone_equal_440


def startPyo():
    from pyo import *
    s = Server().boot()
    s.start()
    return s


class MidiAdsrInstrument(object):

    def __init__(self,
            attack=.01, decay=.1, sustain=.1, release=.01, dur=.121, mul=.5):

        self.adsr = Adsr(
            attack=attack, decay=decay, sustain=sustain, release=release,
            dur=dur, mul=mul
        )
        self.noises = {}
        self.frequency = Sig(value=0)

    def addNoise(self, name, klass, **kwargs):
        """
        klass can be like, Sine, Noise, Osc... we'll see.
        """
        try:
            n = klass(freq=self.frequency, mul=self.adsr, **kwargs).out()
        except TypeError:
            # Noise doesn't take frequency @TODO
            n = klass(mul=self.adsr, **kwargs).out()
        self.noises[name] = n

    def playfreq(self, freq):
        """
        Sets the frequency signal to `freq` and
        plays the Adsr envelope.
        """
        #self.frequency.value = freq
        if self.frequency.value != freq:
            self.frequency.set("value", freq, .001)
        self.adsr.play()

    def playnote(self, note, velocity=None):
        if note:
            self.playfreq(twelve_tone_equal_440[note])

    def stopnote(self, note):
        pass


def test_MidiAdsrInstrument():
    from itertools import cycle
    from bl.player import R, N, Player
    s = startPyo()
    mai = MidiAdsrInstrument()
    mai.addNoise("sine", Sine)
    mai.addNoise("saw", Osc, table=SawTable())
    #harml = [1 for e in range(10)]
    #mai.addNoise("harm", Osc, table=HarmTable(harml))
    #mai.frequency.set("value", 220)
    #mai.adsr.play()

    notes = cycle([
        R(24, 24, 27, 24, 24, 25, 24, 29, 31, 36, 12, 24, N),
    ])
    velocity = lambda: 0
    stop = lambda: 0
    player = Player(mai, notes, velocity, stop=stop, interval=.125)
    #player.clock.callLater(96, player.startPlaying)
    #player.clock.callLater(128,
    #    mai.addNoise, "harm", Osc, table=HarmTable(harml)
    #)
    #player = None
    import IPython
    IPython.embed()
    return s, mai, player

if __name__ == "__main__":
    s, m, p = test_MidiAdsrInstrument()
    p.startPlaying()

class MidiWavesInstrument(object):
    """
    A multi-generator Instrument
    with playnote / stopnote interface.
    Creates wave generator for each 0-127 note played,
    as defined by init_wave in subclasses

    You must pass a Pyo server or one will be created. (fixme?)

    init_wave method returns a dictionary with at least
    "wave", "signal" and "portamento".

    self.waves = {
        60: {
            "wave": Sine(),
            "signal": Sig()
            "portamento": Port()
        },
        67: {
        ...
        },
        ...
    }
    """

    def __init__(self, server=None, risetime=.01, falltime=.01):
        self.waves = {}
        self.effects = {}
        self.risetime = risetime
        self.falltime = falltime
        if not server:
            server = Server().boot()
            server.start()
        self.server = server
        self.clock = getClock()

    def init_wave(self, freq, mul):
        """
        Creates an audio chain for the frequency (Hz) and volume (0-1).
        Returns a dictionary like
        {
            "wave": Sine(),
            "signal": Sig()
            "portamento": Port()
        },
        """
        raise NotImplementedError("Subclasses implement.")

    def playnote(self, note, velocity=10):
        """
        Plays a `note` defined by 0-127 midi 12TET.
        If the sine is already instantiated,
        playnote will set the Sine's frequency
        back to the default and set the velocity
        to what was passed.
        """

        freq = twelve_tone_equal_440[note]
        if velocity:
            mul = 127. / velocity
        else:
            mul = 0

        if note in self.waves:
            waved = self.waves[note]
            waved["signal"].value = mul
            #waved["wave"].out()
        else:
            waved = self.init_wave(freq, mul)
            self.waves[note] = waved
            for name, d in self.effects.iteritems():
                instance = d["klass"](waved["wave"], **d["kwargs"]).out()
                d["instances"].append(instance)

    def stopnote(self, note):
        """
        note: the midi note to stop.
        """
        waved = self.waves[note]
        waved["signal"].value = 0
        #waved["wave"].stop()

    def stopall(self):
        for waved in self.waves.values():
            waved["signal"].value = 0
            #waved["wave"].stop()

    def setRiseFall(self, risetime, falltime):
        """
        risetime: num seconds for note to fade in
        set for all existing notes.
        """
        self.risetime = risetime
        self.falltime = falltime
        for waved in self.waves.values():
            waved["portamento"].setRiseTime(risetime)
            waved["portamento"].setFallTime(falltime)

    def addEffectToAll(self, name, klass, **kwargs):
        instances = []
        # if you already have this name
        if name in self.effects:
            raise ValueError("already have that name.")
        for waved in self.waves.values():
            instance = klass(waved["wave"], **kwargs).out()
            instances.append(instance)
        self.effects[name] = {
            "instances": instances,
            "klass": klass,
            "kwargs": kwargs,
        }


class MidiSinesInstrument(MidiWavesInstrument):

    def init_wave(self, freq, mul):
        ft = self.falltime
        rt = self.risetime
        signal = Sig(value=mul)
        portamento = Port(signal, risetime=rt, falltime=ft)
        wave = Sine(freq, mul=portamento)
        wave.out()
        waved = {
            "wave": wave,
            "portamento": portamento,
            "signal": signal,
        }
        return waved


class MidiHarmonicPortamentoInstrument(MidiWavesInstrument):

    table = [1, .5, .33, .2, .2, 0, .143, .01, .111]

    def init_wave(self, freq, mul):
        ft = self.falltime
        rt = self.risetime
        signal = Sig(value=mul)
        portamento = Port(signal, risetime=rt, falltime=ft)

        t = HarmTable(self.table)
        wave = Osc(table=t, freq=freq, mul=portamento).out()

        waved = {
            "wave": wave,
            "portamento": portamento,
            "signal": signal,
        }
        return waved

    def replace(self, l):
        """
        Replace the harmonic table for existing and future waves.
        Doesn't work well while sound is playing ...
        """
        #clock = self.clock
        self.table = l
        self.stopall()
        for note, d in self.waves.iteritems():
            #clock.callLater(4, d["wave"].table.replace, l)
            d["wave"].table.replace(l)
            #clock.callLater(8, self.playnote, note)


def test_MidiHarmonicPortamentoInstrument():
    import random
    from bl.player import R, N, Player
    from itertools import cycle

    mhpi = MidiHarmonicPortamentoInstrument()
    notes = cycle([
        30, 42, 37, R(N, 28),
    ])
    velocity = lambda: random.randint(20, 100)
    stop = lambda: random.randint(1, 24)
    player = Player(mhpi, notes, velocity, stop=stop, interval=0.25)
    player.startPlaying()
    r = lambda: [random.random() for i in range(random.randint(1, 20))]
    for i in range(1, 100):
        mhpi.clock.callLater((128 * i) - 5, mhpi.replace, r())
    return mhpi, player


def main():
    import random
    from itertools import cycle
    from bl.player import R, N, Player
    msi = MidiSinesInstrument()
    mhpi = MidiHarmonicPortamentoInstrument(msi.server)
    notes = cycle([
        R(24),
        #R(48, 51, 58, N),
        #R(36, 41, 43, 45, N),
        #R(39, 36, N),
        R(36, 41, 48, N),
        R(N),
        R(N),

        R(24),
        R(N, 36, 29),
        #R(36, 39, 41, N),
        #R(48, 51, 52, 58, N),
        R(43, N, 40),
        R(43, 41, N, 24, 36, N, 40, 38, 45, 46, 48),

        R(24),
        R(N),
        R(N),
        R(N),

        R(36),
        R(N),
        R(N),
        R(N),

    ])

    def velocity_gen():
        i = 0
        while True:
            i += 1
            if not i % 8:
                yield 100
            else:
                yield random.choice([60, 80, 90, 40, 70, 60, 50, 60])

    velocity = velocity_gen().next
    #velocity = cycle([100, 80, 90, 40, 70, 0, 50, 0]).next
    stop = lambda: random.randint(1, 24)
    interval = .0625
    player = Player(msi, notes, velocity, stop=stop, interval=interval)
    player2 = Player(mhpi, notes, velocity, stop=stop, interval=.125)
    player2.startPlaying()
    player.startPlaying()
    msi.clock.callLater(256, msi.setRiseFall, .1, .1)
    msi.clock.callLater(512, msi.setRiseFall, 1, 1)
    msi.clock.callLater(512 + 256, msi.setRiseFall, .01, .01)
    msi.clock.callLater(1024, msi.setRiseFall, 0, .01)
    msi.clock.callLater(2048, msi.setRiseFall, 0, .5)
    msi.clock.callLater(3072, msi.setRiseFall, 0, .1)
    level = Sig(value=0)
    drive = Sig(value=0)
    portamento = Port(drive, risetime=.5, falltime=.5)
    portamentol = Port(level, risetime=.5, falltime=.5)
    msi.clock.callLater(512, msi.addEffectToAll,
        "disto", Disto, drive=portamento, slope=.8, mul=portamentol
    )
    msi.clock.callLater(800, level.setValue, .5)
    msi.clock.callLater(1000, drive.setValue, 1)
    msi.clock.callLater(1500, drive.setValue, .5)
    msi.clock.callLater(10000, msi.server.stop)
    return msi, mhpi, player, drive
