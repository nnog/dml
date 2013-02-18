import colorsys

HUES = {'r': 0, 'o': 30, 'y': 60, 'g': 120, 'b': 240, 'v': 270}
LUMS = {'D': 0.30, 'd': 0.40, 'n': 0.50, 'l': 0.60, 'L': 0.70}
ADDSAT = 0.2

     
class Palette(object):
    def __init__(self, sat=0.5):
        self.sat = sat

    def decode(self, hue, value_mod=None):
        
        hue = hue.lower()
        assert hue in HUES
        hueval = float(HUES[hue.lower()])/360

        if value_mod==None:
            value_mod = 'n'

        assert value_mod in LUMS
        lum = LUMS[value_mod]

        addsat = ADDSAT if hue.isupper() else 0
        return colorsys.hls_to_rgb(hueval, lum, self.sat+addsat)

    def decodeint(self, hue, value_mod=None):
        col = self.decode(hue, value_mod)
        return [int(x * 100) for x in col]
