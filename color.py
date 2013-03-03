import colorsys

#2char color code constants
HUES = {'r': 0, 'o': 30, 'y': 60, 'g': 120, 'b': 240, 'v': 270}
LUMS = {'D': 0.40, 'd': 0.50, 'n': 0.60, 'l': 0.70, 'L': 0.80}
ADDSAT = 0.2

     
class Palette(object):
    def __init__(self, sat=1):
        self.sat = sat
        self.palette = {}
        self.namecounter = 0

    def register(self, rgb, name=None):
        if name==None:
            self.palette['palette_%s'%self.namecounter] = rgb
        else:
            self.palette[name] = rgb

    def decode_2char(self, hue, value_mod=None):
        hue = hue.lower()
        assert hue in HUES
        hueval = float(HUES[hue.lower()])/360

        if value_mod==None:
            value_mod = 'n'

        assert value_mod in LUMS
        lum = LUMS[value_mod]

        addsat = ADDSAT if hue.isupper() else 0
        return colorsys.hls_to_rgb(hueval, lum, self.sat+addsat)

    def register_2char(self, hue, value_mod=None):
        col = self.decode_2char(hue, value_mod)
        name = hue if value_mod==None else value_mod+hue
        self.register(col, name)
        return name

    def define_colors(self):
        for name, col in self.palette.items():
            print "\\definecolor{%s}{rgb}{%s,%s,%s}" % (name, col[0], col[1], col[2])
