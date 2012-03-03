from pyo import Sine, Port, Sig, Server, Disto

from bl.utils import getClock
from bl.music.structures.notes import twelve_tone_equal_440


class MidiSinesInstrument(object):
    """
    A simple multi-Sine Instrument
    with playnote / stopnote interface.

    You must pass a Pyo server or one will be created. (fixme?)

    self.sineds = {
        60: {
            "sine": Sine(),
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
        self.sineds = {}
        self.effects = {}
        self.risetime = risetime
        self.falltime = falltime
        if not server:
            server = Server().boot()
            server.start()
        self.server = server
        self.clock = getClock()

    def init_sine(self, freq, mul):
        ft = self.falltime
        rt = self.risetime
        signal = Sig(value=mul)
        portamento = Port(signal, risetime=rt, falltime=ft)
        sine = Sine(freq, mul=portamento)
        sine.out()
        sined = {
            "sine": sine,
            "portamento": portamento,
            "signal": signal,
        }
        return sined

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

        if note in self.sineds:
            sined = self.sineds[note]
            sined["signal"].value = mul
            #sined["sine"].out()
        else:
            sined = self.init_sine(freq, mul)
            self.sineds[note] = sined

    def stopnote(self, note):
        """
        note: the midi note to stop.
        """
        sined = self.sineds[note]
        sined["signal"].value = 0
        #sined["sine"].stop()

    def stopall(self):
        for sined in self.sineds.values():
            sined["signal"].value = 0
            sined["sine"].stop()

    def setRiseFall(self, risetime, falltime):
        """
        risetime: num seconds for note to fade in
        set for all existing notes.
        """
        self.risetime = risetime
        self.falltime = falltime
        for sined in self.sineds.values():
            sined["portamento"].setRiseTime(risetime)
            sined["portamento"].setFallTime(falltime)

    def addEffect(self, name, klass, **kwargs):
        effects = []
        if name in self.effects:
            raise ValueError("already have that name.")
        for sined in self.sineds.values():
            effect = klass(sined["sine"], **kwargs).out()
            effects.append(effect)
        self.effects[name] = effects


def main():
    import random
    from itertools import cycle
    from bl.player import R, N, Player
    msi = MidiSinesInstrument()
    notes = cycle([
        R(60, 58, 48, 36, N),
        R(36, 39, 41, N),
        R(48, 51, 58, N),
        R(36, 41, 43, 45, N),
        R(39, 36, N),
        R(36, 41, 48, N),
        R(N),
        R(N, 34),
        R(N, 36, 39),
        R(36, 39, 41, N),
        R(48, 51, 52, 58, N),
        R(43, N, 38),
        R(43, 41, N),
    ])
    velocity = cycle([100, 80, 90, 40, 70, 0, 50, 0]).next
    stop = lambda: random.randint(1, 24)
    interval = .0625
    player = Player(msi, notes, velocity, stop=stop, interval=interval)
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
    msi.clock.callLater(512, msi.addEffect,
        "disto", Disto, drive=portamento, slope=.8, mul=portamentol
    )
    msi.clock.callLater(800, level.setValue, .5)
    msi.clock.callLater(1000, drive.setValue, 1)
    msi.clock.callLater(1500, drive.setValue, .5)
    msi.clock.callLater(4096, msi.server.stop)
    return msi, player, drive
