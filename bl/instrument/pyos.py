from twisted.python import log

from pyo import (
    Sine,
    #Port,
    SigTo, Server, Disto,
    Osc, HarmTable,
    Adsr, SawTable, Noise,
)

#from bl.utils import getClock
from bl.music.structures.notes import twelve_tone_equal_440


def startPyo():
    from pyo import *
    s = Server().boot()
    s.start()
    return s


class MidiAdsrInstrument(object):

    def __init__(self, attack=.01, decay=.1, sustain=.1, release=.01,
                 dur=.121, mul=.5, freq_time=.03, mul_time=.03):

        self.freq = SigTo(value=0, time=freq_time)
        self.mul = SigTo(value=mul, time=mul_time)
        self.adsr = Adsr(
            attack=attack, decay=decay, sustain=sustain, release=release,
            dur=dur, mul=self.mul
        )
        self.noises = {}
        self.effects = {}

    def addNoise(self, name, klass, **kwargs):
        """
        klass can be like, Sine, Noise, Osc... we'll see.
        """
        try:
            n = klass(freq=self.freq, mul=self.adsr, **kwargs).out()
        except TypeError:
            # Noise doesn't take frequency @TODO
            n = klass(mul=self.adsr, **kwargs).out()
        self.noises[name] = n

        # add the effects to the new noise.
        for name, effect in self.effects.iteritems():
            klass = effect["klass"]
            instance = klass(n, **effect["kwargs"]).out()
            self.effects[name]["instances"].append(instance)

    def addEffect(self, name, klass, **kwargs):
        """
        An effect `klass` gets instantiated with each noise as src.
        And gets sent .out().
        """
        if name in self.effects:
            log.msg("Already an effect of that name.")
            return None
            #raise ValueError("Already and effect with that name.")

        effect = {
            "klass": klass,
            "kwargs": kwargs,
            "instances": [],
        }
        for noise in self.noises.values():
            instance = klass(noise, **kwargs).out()
            effect["instances"].append(instance)

        self.effects[name] = effect

    def playfreq(self, freq, mul):
        """
        Sets the frequency signal to `freq` and
        plays the Adsr envelope.
        """
        #self.frequency.value = freq
        if self.freq.value != freq:
            self.freq.value = freq
        if mul != self.mul.value:
            self.mul.value = mul
        self.adsr.play()

    def playnote(self, note, velocity=None):
        if velocity is None:
            mul = self.adsr.mul.value
        else:
            mul = velocity / 127.
        self.playfreq(twelve_tone_equal_440[note], mul)

    def stopnote(self, note):
        """
        Stop is defined in the ADSR.
        """
        pass


def test_MidiAdsrInstrument():
    import random
    from itertools import cycle
    from bl.player import R, N, Player
    s = startPyo()
    mai = MidiAdsrInstrument()
    mai.addNoise("sine", Sine)
    mai.addNoise("saw", Osc, table=SawTable())

    notes = cycle([
        R(24, 24, 27, 24, 24, 25, 24, 29, 31, 36, 12, 24, N),
    ])
    velocity = lambda: random.choice([80, 60, 120, 20, 30, 10, 5, 1])
    player = Player(mai, notes, velocity, interval=.0625)

    mai.adsr.decay = .01
    mai.adsr.sustain = .01
    clock = player.clock
    clock.callLater(128, player.startPlaying)
    clock.callLater(512, mai.adsr.setDecay, .07)
    clock.callLater(2048, mai.addNoise, "noise", Noise)
    clock.callLater(2560, mai.adsr.setSustain, .05)
    harml = [1, .5, .5, .5, .5]
    clock.callLater(1024,
        mai.addNoise, "harm", Osc, table=HarmTable(harml)
    )
    dist_sig = SigTo(value=0, time=4)
    mai.addEffect("disto", Disto, drive=dist_sig, slope=.8, mul=.5)
    clock.callLater(500, dist_sig.setValue, 1)
    clock.callLater(800, dist_sig.setValue, 0)
    clock.callLater(1300, dist_sig.setValue, 1)
    clock.callLater(1800, dist_sig.setValue, 0)
    clock.callLater(2300, dist_sig.setValue, 1)
    clock.callLater(2800, dist_sig.setValue, .5)
    return s, dist_sig, mai, player
