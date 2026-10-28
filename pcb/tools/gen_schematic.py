"""Generate the racebot_main KiCad 10 project (hierarchical schematic)."""
import os, sys, uuid, json, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import Sym, dump, find, getsym, pins, parse

OUT = sys.argv[1]
PROJ = 'racebot_main'
S = Sym
G = 1.27
NS = uuid.UUID('6f1c1a52-3b0e-4c47-9d7e-7b2f0d1e9a11')


def U(*key):
    return str(uuid.uuid5(NS, '/'.join(str(k) for k in key)))


def r2(v):
    return round(v / 0.01) * 0.01


def snap(v):
    return round(round(v / G) * G, 2)


def font(size=1.27, extra=None):
    f = [S('font'), [S('size'), size, size]]
    if extra:
        f += extra
    return f


def effects(justify=None, hide=False, size=1.27):
    e = [S('effects'), font(size)]
    if justify:
        e.append([S('justify')] + [S(j) for j in justify.split()])
    return e


def prop(name, val, x, y, hide=False, justify=None, ang=0):
    p = [S('property'), name, val, [S('at'), r2(x), r2(y), ang]]
    if hide:
        p.append([S('hide'), S('yes')])
    p.append(effects(justify))
    return p


# ---------------------------------------------------------------- custom library
def pin(typ, x, y, a, name, numb, length=5.08, hidden=False):
    p = [S('pin'), S(typ), S('line'), [S('at'), x, y, a], [S('length'), length]]
    if hidden:
        p.append([S('hide'), S('yes')])
    p += [[S('name'), name, effects()], [S('number'), numb, effects()]]
    return p


def libsym(name, ref, value, fp, ds, desc, body, pinlist, kw=''):
    return [S('symbol'), name,
            [S('pin_names'), [S('offset'), 1.016]],
            [S('exclude_from_sim'), S('no')], [S('in_bom'), S('yes')], [S('on_board'), S('yes')],
            prop('Reference', ref, 0, body[1] + 1.27 if False else 0, False),
            prop('Value', value, 0, 0),
            prop('Footprint', fp, 0, 0, True),
            prop('Datasheet', ds, 0, 0, True),
            prop('Description', desc, 0, 0, True),
            prop('ki_keywords', kw, 0, 0, True),
            [S('symbol'), name + '_0_1',
             [S('rectangle'), [S('start'), body[0], body[1]], [S('end'), body[2], body[3]],
              [S('stroke'), [S('width'), 0.254], [S('type'), S('default')]], [S('fill'), [S('type'), S('background')]]]],
            [S('symbol'), name + '_1_1'] + pinlist]


def fix_ref_val_pos(sym, ref_xy, val_xy):
    for p in find(sym, 'property'):
        if p[1] == 'Reference':
            p[3] = [S('at'), ref_xy[0], ref_xy[1], 0]
        if p[1] == 'Value':
            p[3] = [S('at'), val_xy[0], val_xy[1], 0]
    return sym


BTS = fix_ref_val_pos(libsym(
    'BTS7960B', 'U', 'BTS7960B', 'Package_TO_SOT_SMD:TO-263-7_TabPin8',
    'https://www.infineon.com/dgdl/Infineon-BTS7960-DS-v01_01-EN.pdf',
    'Infineon NovalithIC 43 A high-current PN half-bridge, PG-TO263-7 (tab = OUT)',
    (-7.62, 10.16, 7.62, -10.16),
    [pin('power_in', 0, -15.24, 90, 'GND', '1'),
     pin('input', -12.7, 5.08, 0, 'IN', '2'),
     pin('input', -12.7, 2.54, 0, 'INH', '3'),
     pin('passive', 12.7, 2.54, 180, 'OUT', '4'),
     pin('passive', -12.7, -2.54, 0, 'SR', '5'),
     pin('output', -12.7, -5.08, 0, 'IS', '6'),
     pin('power_in', 0, 15.24, 270, 'VS', '7'),
     pin('passive', 12.7, 0, 180, 'OUT(TAB)', '8')], 'half bridge motor driver'),
    (2.54, 11.43), (2.54, -11.43))

# 38-pin ESP32-WROOM-32 DevKit (DevKitC V4 order). Pin 1 of each row is at the antenna end.
ESP_L = ['3V3', 'EN', 'VP/IO36', 'VN/IO39', 'IO34', 'IO35', 'IO32', 'IO33', 'IO25', 'IO26', 'IO27', 'IO14',
         'IO12', 'GND', 'IO13', 'SD2/IO9', 'SD3/IO10', 'CMD/IO11', '5V']
ESP_R = ['GND', 'IO23', 'IO22', 'TX0/IO1', 'RX0/IO3', 'IO21', 'GND', 'IO19', 'IO18', 'IO5', 'IO17', 'IO16',
         'IO4', 'IO0', 'IO2', 'IO15', 'SD1/IO8', 'SD0/IO7', 'CLK/IO6']


def esp_type(n):
    if n == '3V3':
        return 'power_out'
    if n == '5V':
        return 'power_in'
    if n == 'GND':
        return 'passive'
    if n in ('IO34', 'IO35', 'VP/IO36', 'VN/IO39'):
        return 'input'
    return 'bidirectional'


def esp_sym(name, names, right):
    pl = []
    for i, n in enumerate(names):
        y = 22.86 - 2.54 * i
        if right:   # connection on the right side
            pl.append(pin(esp_type(n), 12.7, y, 180, n, str(i + 1)))
        else:
            pl.append(pin(esp_type(n), -12.7, y, 0, n, str(i + 1)))
    return fix_ref_val_pos(libsym(
        name, 'J', name, 'Connector_PinSocket_2.54mm:PinSocket_1x19_P2.54mm_Vertical', '',
        '1x19 female header row for a 38-pin ESP32-WROOM-32 DevKit (DevKitC V4 pin order)',
        (-7.62, 25.4, 7.62, -25.4), pl, 'ESP32 devkit header'), (0, 26.67), (0, -26.67))


CUSTOM = {'BTS7960B': BTS, 'ESP32_DevKit38_L': esp_sym('ESP32_DevKit38_L', ESP_L, True),
          'ESP32_DevKit38_R': esp_sym('ESP32_DevKit38_R', ESP_R, False)}


def get_lib_symbol(lib, name):
    if lib == 'racebot':
        return copy.deepcopy(CUSTOM[name])
    return getsym(lib, name)


# ---------------------------------------------------------------- sheets
POWER_NETS = {'GND': ('power', 'GND'), '+5V': ('power', '+5V'), '+3V3': ('power', '+3V3'),
              'VMOT': ('power', '+12V')}
DIRS = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # pin angle -> outward screen dir


class Sheet:
    def __init__(self, name, fname, paper='A3', page=1):
        self.name, self.fname, self.paper, self.page = name, fname, paper, page
        self.uuid = U('sheetfile', fname)
        self.libs = {}
        self.items = []
        self.path = None          # instance path, set by root
        self.pwr = 0
        self.hier = {}            # name -> shape
        self.comps = []

    # -- primitives
    def wire(self, a, b):
        self.items.append([S('wire'), [S('pts'), [S('xy'), r2(a[0]), r2(a[1])], [S('xy'), r2(b[0]), r2(b[1])]],
                           [S('stroke'), [S('width'), 0], [S('type'), S('default')]],
                           [S('uuid'), U(self.fname, 'w', a, b)]])

    def nc(self, p):
        self.items.append([S('no_connect'), [S('at'), r2(p[0]), r2(p[1])], [S('uuid'), U(self.fname, 'nc', p)]])

    def label(self, name, p, d, kind='label'):
        ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
        if kind == 'label':
            just = 'left bottom' if ang in (0, 90) else 'right bottom'
            self.items.append([S('label'), name, [S('at'), r2(p[0]), r2(p[1]), ang], effects(just),
                               [S('uuid'), U(self.fname, 'lbl', name, p)]])
        else:
            just = 'left' if ang in (0, 90) else 'right'
            self.items.append([S('hierarchical_label'), name, [S('shape'), S(self.hier[name])],
                               [S('at'), r2(p[0]), r2(p[1]), ang], effects(just),
                               [S('uuid'), U(self.fname, 'hl', name, p)]])

    def text(self, s, x, y, size=1.27):
        self.items.append([S('text'), s, [S('exclude_from_sim'), S('no')], [S('at'), x, y, 0],
                           [S('effects'), font(size), [S('justify'), S('left'), S('top')]],
                           [S('uuid'), U(self.fname, 'txt', s[:40], x, y)]])

    def uselib(self, lib, name):
        key = lib + ':' + name
        if key not in self.libs:
            s = get_lib_symbol(lib, name)
            s[1] = key
            self.libs[key] = s
        return self.libs[key]

    # -- symbol instance
    def place(self, ref, lib, name, x, y, value, fp='', nets=None, fields=None, rot=0, hide_val=False):
        key = lib + ':' + name
        x, y = snap(x), snap(y)
        ls = self.uselib(lib, name)
        is_power = bool(find(ls, 'power'))
        cu = U(self.fname, 'sym', ref, x, y)
        refpos = (x + 3.81, y - 1.27) if not is_power else (x, y + 3.81)
        valpos = (x + 3.81, y + 1.27) if not is_power else (x, y - 3.81 if name != 'GND' else y + 5.08)
        lpr = {p[1]: p for p in find(ls, 'property')}
        if 'Reference' in lpr and not is_power:
            at = lpr['Reference'][3]
            refpos = (x + float(at[1]), y - float(at[2]))
            at = lpr['Value'][3]
            valpos = (x + float(at[1]), y - float(at[2]))
            if name in ('R', 'C', 'C_Polarized', 'L', 'Fuse'):
                refpos, valpos = (x + 2.54, y - 1.27), (x + 2.54, y + 1.27)
        inst = [S('symbol'), [S('lib_id'), key], [S('at'), r2(x), r2(y), rot], [S('unit'), 1],
                [S('exclude_from_sim'), S('no')],
                [S('in_bom'), S('no') if is_power else S('yes')],
                [S('on_board'), S('no') if is_power else S('yes')], [S('dnp'), S('no')],
                [S('uuid'), cu],
                prop('Reference', ref, *refpos, hide=is_power, justify=None if is_power else 'left'),
                prop('Value', value, *valpos, hide=hide_val, justify=None if is_power else 'left'),
                prop('Footprint', fp, x, y, True),
                prop('Datasheet', lpr.get('Datasheet', [0, 0, ''])[2], x, y, True),
                prop('Description', lpr.get('Description', [0, 0, ''])[2], x, y, True)]
        for k, v in (fields or {}).items():
            inst.append(prop(k, v, x, y, True))
        plist = pins(ls)
        for pnum in sorted({p['num'] for p in plist}, key=lambda s: (len(s), s)):
            inst.append([S('pin'), pnum, [S('uuid'), U(self.fname, cu, 'pin', pnum)]])
        inst.append([S('instances'), [S('project'), PROJ,
                                      [S('path'), '@PATH@', [S('reference'), ref], [S('unit'), 1]]]])
        self.items.append(inst)
        if not is_power:
            self.comps.append(dict(ref=ref, value=value, fp=fp, fields=fields or {}, sheet=self.name))
        # connections
        done = set()
        for p in plist:
            if not nets or p['num'] not in nets:
                continue
            px, py = x + p['x'], y - p['y']
            if (px, py) in done:
                continue
            done.add((px, py))
            self.connect(nets[p['num']], (px, py), DIRS[int(p['a']) % 360])
        if nets:
            missing = {p['num'] for p in plist} - set(nets)
            if missing and not is_power:
                raise SystemExit('%s: pins without net: %s' % (ref, sorted(missing)))

    def power(self, net, p, d):
        lib, name = POWER_NETS[net]
        self.pwr += 1
        up = name != 'GND'
        # rotate so the graphic points away from the stub
        if up:
            rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d]
        else:
            rot = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[d]
        self.place('#PWR%s%02d' % (self.page, self.pwr), lib, name, p[0], p[1], net, rot=rot)

    def connect(self, net, p, d, stub=2.54):
        if net == 'NC':
            self.nc(p)
            return
        e = (p[0] + d[0] * stub, p[1] + d[1] * stub)
        self.wire(p, e)
        if net in POWER_NETS:
            self.power(net, e, d)
        elif net.startswith('H:'):
            self.label(net[2:], e, d, 'hier')
        else:
            self.label(net, e, d)

    def flag(self, net, x, y):
        self.pwr += 1
        self.place('#FLG%s%02d' % (self.page, self.pwr), 'power', 'PWR_FLAG', x, y, 'PWR_FLAG', nets={'1': net})

    def render(self, root_uuid, extra_items=(), is_root=False, path=None):
        body = [S('kicad_sch'), [S('version'), 20250610], [S('generator'), 'eeschema'],
                [S('generator_version'), '10.0'], [S('uuid'), self.uuid], [S('paper'), self.paper],
                [S('title_block'), [S('title'), 'racebot_main - ' + self.name], [S('date'), '2026-10-28'],
                 [S('rev'), 'A'], [S('company'), 'racebot']],
                [S('lib_symbols')] + list(self.libs.values())]
        body += self.items
        body += list(extra_items)
        if is_root:
            body.append([S('sheet_instances'), [S('path'), '/', [S('page'), '1']]])
        body.append([S('embedded_fonts'), S('no')])
        txt = dump(body) + '\n'
        return txt.replace('"@PATH@"', '"%s"' % path)


# ======================================================================= POWER
def lcsc(c, mpn=''):
    d = {'LCSC': c}
    if mpn:
        d['MPN'] = mpn
    return d


R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
LED0603 = 'LED_SMD:LED_0603_1608Metric'
RES = {'10k': ('C25804', '0603WAF1002T5E'), '100k': ('C25803', '0603WAF1003T5E'),
       '22k': ('C31850', '0603WAF2202T5E'), '1k': ('C21190', '0603WAF1001T5E'),
       '4.7k': ('C23162', '0603WAF4701T5E'), '5.1k': ('C23186', '0603WAF5101T5E'),
       '470': ('C23179', '0603WAF4700T5E')}


def R(sh, ref, val, x, y, n1, n2, note=''):
    f = lcsc(*RES[val])
    if note:
        f['Note'] = note
    sh.place(ref, 'Device', 'R', x, y, val, R0603, {'1': n1, '2': n2}, f)


def C100n(sh, ref, x, y, n1, n2):
    sh.place(ref, 'Device', 'C', x, y, '100nF 50V X7R', C0603, {'1': n1, '2': n2}, lcsc('C14663', 'CC0603KRX7R9BB104'))


def build_power():
    sh = Sheet('Power', 'power.kicad_sch', page=2)
    sh.hier = {'VBAT_SENSE': 'output'}
    sh.text('POWER INPUT / PROTECTION\n'
            'XT60 (battery 3S, 9.0-12.6 V) -> 30 A ATO fuse -> VBAT_F -> J102 power switch / kill link -> VMOT.\n'
            'Q101: low-side N-MOSFET reverse-polarity protection in the ground return (D=battery -, S=GND).\n'
            'Gate fed from VMOT (after the switch) so nothing drains the battery when switched off.', 20, 20)
    sh.place('J101', 'Connector_Generic', 'Conn_01x02', 35, 60, 'XT60 BATTERY',
             'Connector_AMASS:AMASS_XT60-M_1x02_P7.20mm_Vertical', {'1': 'BAT_NEG', '2': 'BAT_POS'},
             {**lcsc('C19268037', 'XT60PB-M.G.Y'), 'Note': 'vertical; pin1 (bevelled end) = -, pin2 = +. Check against battery plug'})
    sh.place('F101', 'Device', 'Fuse', 60, 62, '30A ATO',
             'Fuse:FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165', {'1': 'BAT_POS', '2': 'VBAT_F'},
             {**lcsc('C207061', '178.6165.0002'), 'Note': 'ATO holder; fit 30 A ATO blade fuse'})
    sh.place('J102', 'Connector_Generic', 'Conn_01x02', 90, 60, 'PWR SWITCH / KILL LINK',
             'Connector_AMASS:AMASS_XT60-F_1x02_P7.20mm_Vertical', {'1': 'VMOT', '2': 'VBAT_F'},
             {**lcsc('C19268038', 'XT60PB-F.G.Y'),
              'Note': 'Plug a shorted XT60 link, or a >=30 A switch on an XT60 lead. See LAYOUT_NOTES.md'})
    sh.place('Q101', 'Transistor_FET', 'CSD18540Q5B', 125, 62, 'CSD18540Q5B', 'Package_TO_SOT_SMD:TDSON-8-1',
             {'1': 'GND', '2': 'GND', '3': 'GND', '4': 'Q_GATE', '5': 'BAT_NEG'}, lcsc('C86513', 'CSD18540Q5B'))
    R(sh, 'R101', '10k', 145, 62, 'VMOT', 'Q_GATE')
    R(sh, 'R102', '100k', 162, 62, 'Q_GATE', 'GND')
    sh.place('D101', 'Diode', 'BZT52Bxx', 185, 62, 'BZT52C12', 'Diode_SMD:D_SOD-123',
             {'1': 'Q_GATE', '2': 'GND'}, lcsc('C12747', 'LBZT52C12T1G'))
    sh.place('D102', 'Device', 'D_Zener', 220, 62, 'SMCJ15A', 'Diode_SMD:D_SMC',
             {'1': 'VMOT', '2': 'GND'}, {**lcsc('C135138', 'SMCJ15A-13-F'),
                                         'Note': 'Unidirectional TVS 15 V standoff, clamps ~24.4 V'})
    sh.flag('VMOT', 250, 55)
    sh.flag('GND', 265, 55)
    sh.flag('+5V', 280, 55)

    sh.text('5 V BUCK (LM2596S-5.0)  -> ESP32 5V pin, ELRS receiver, 74HCT244\n'
            'Keep VIN cap - U101 - D103 - C103 loop tight (see LAYOUT_NOTES.md).', 20, 100)
    sh.place('C101', 'Device', 'C_Polarized', 35, 130, '220uF 35V', 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',
             {'1': 'VMOT', '2': 'GND'}, lcsc('C346959', 'NXH35V220M8*11.5 3.5TP'))
    C100n(sh, 'C102', 52, 130, 'VMOT', 'GND')
    sh.place('U101', 'Regulator_Switching', 'LM2596S-5', 85, 130, 'LM2596S-5.0',
             'Package_TO_SOT_SMD:TO-263-5_TabPin3',
             {'1': 'VMOT', '2': 'SW_5V', '3': 'GND', '4': '+5V', '5': 'GND'}, lcsc('C116713', 'LM2596S-5.0/NOPB'))
    sh.place('D103', 'Diode', 'SS34', 115, 145, 'SS34', 'Diode_SMD:D_SMA',
             {'1': 'SW_5V', '2': 'GND'}, lcsc('C8678', 'SS34'))
    sh.place('L101', 'Device', 'L', 130, 130, '33uH 4.6A', 'Inductor_SMD:L_Bourns_SRR1260',
             {'1': 'SW_5V', '2': '+5V'}, lcsc('C840528', 'SRR1260-330M'))
    sh.place('C103', 'Device', 'C_Polarized', 147, 130, '220uF 16V low-ESR', 'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',
             {'1': '+5V', '2': 'GND'}, lcsc('C88757', '16YXJ220M6.3X11'))
    C100n(sh, 'C104', 165, 130, '+5V', 'GND')

    sh.text('BATTERY SENSE: VMOT -> 100k/22k (2.27 V @ 12.6 V) -> GPIO33 (ADC1_CH5)', 185, 100)
    R(sh, 'R103', '100k', 200, 120, 'VMOT', 'H:VBAT_SENSE')
    R(sh, 'R104', '22k', 200, 155, 'H:VBAT_SENSE', 'GND')
    C100n(sh, 'C105', 220, 155, 'H:VBAT_SENSE', 'GND')

    sh.text('POWER LEDs', 255, 112)
    R(sh, 'R105', '1k', 255, 125, '+5V', 'LED5_A')
    sh.place('D104', 'Device', 'LED', 262, 145, 'RED 5V', LED0603, {'1': 'GND', '2': 'LED5_A'},
             lcsc('C2286', 'KT-0603R'))
    R(sh, 'R106', '4.7k', 285, 125, 'VMOT', 'LEDV_A')
    sh.place('D105', 'Device', 'LED', 292, 145, 'RED VMOT', LED0603, {'1': 'GND', '2': 'LEDV_A'},
             lcsc('C2286', 'KT-0603R'))
    return sh


# ======================================================================= MCU + RX
def build_mcu():
    sh = Sheet('MCU+RX', 'mcu_rx.kicad_sch', page=3)
    out = ['L_INA', 'L_INB', 'L_EN', 'R_INA', 'R_INB', 'R_EN']
    sh.hier = {n: 'output' for n in out}
    sh.hier.update({n: 'input' for n in ['L_IS_A', 'L_IS_B', 'R_IS_A', 'R_IS_B', 'VBAT_SENSE']})
    sh.text('ESP32 38-pin DevKit (ESP-WROOM-32, DevKitC V4 pin order) on 2x 1x19 female headers.\n'
            'Pin 1 of each row = antenna end. VERIFY against the board silkscreen before ordering.\n'
            'Board is powered through its 5V pin from the LM2596. 3V3 pin = board LDO output (clamps only).', 20, 20)
    left = {1: '+3V3', 2: 'NC', 3: 'H:R_IS_A', 4: 'H:R_IS_B', 5: 'H:L_IS_A', 6: 'H:L_IS_B', 7: 'NC',
            8: 'H:VBAT_SENSE', 9: 'H:L_INA', 10: 'H:L_INB', 11: 'H:L_EN', 12: 'NC', 13: 'NC', 14: 'GND', 15: 'NC',
            16: 'NC', 17: 'NC', 18: 'NC', 19: '+5V'}
    right = {1: 'GND', 2: 'H:R_EN', 3: 'NC', 4: 'NC', 5: 'NC', 6: 'NC', 7: 'GND', 8: 'H:R_INB', 9: 'H:R_INA',
             10: 'NC', 11: 'CRSF_TX', 12: 'CRSF_RX', 13: 'STATUS_LED', 14: 'NC', 15: 'NC', 16: 'NC', 17: 'NC',
             18: 'NC', 19: 'NC'}
    sock = lcsc('C319202', '2.54-1*19PFemale')
    sh.place('J201', 'racebot', 'ESP32_DevKit38_L', 90, 100, 'ESP32 DevKit left row',
             'Connector_PinSocket_2.54mm:PinSocket_1x19_P2.54mm_Vertical',
             {str(k): v for k, v in left.items()}, sock)
    sh.place('J202', 'racebot', 'ESP32_DevKit38_R', 180, 100, 'ESP32 DevKit right row',
             'Connector_PinSocket_2.54mm:PinSocket_1x19_P2.54mm_Vertical',
             {str(k): v for k, v in right.items()}, sock)

    sh.text('ELRS RECEIVER (SpeedyBee ELRS, CRSF @ 420k baud on UART2)\n'
            'Receiver TX -> GPIO16 (ESP RX2), Receiver RX <- GPIO17 (ESP TX2)', 240, 70)
    sh.place('J203', 'Connector_Generic', 'Conn_01x04', 265, 95, 'ELRS RX (5V GND TX RX)',
             'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
             {'1': '+5V', '2': 'GND', '3': 'CRSF_RX', '4': 'CRSF_TX'}, lcsc('C492403', 'PZ254V-11-04P'))
    sh.text('STATUS LED (GPIO4)', 240, 130)
    R(sh, 'R201', '1k', 250, 145, 'STATUS_LED', 'STAT_A')
    sh.place('D201', 'Device', 'LED', 262, 160, 'RED STATUS', LED0603, {'1': 'GND', '2': 'STAT_A'},
             lcsc('C2286', 'KT-0603R'))
    return sh


# ======================================================================= LOGIC BUFFER
def build_logic():
    sh = Sheet('Logic Buffer', 'logic_buffer.kicad_sch', page=4)
    ins = ['L_INA', 'L_INB', 'L_EN', 'R_INA', 'R_INB', 'R_EN']
    sh.hier = {n: 'input' for n in ins}
    sh.hier.update({n + '_5V': 'output' for n in ins})
    sh.text('74HCT244: 3.3 V ESP32 logic in (VIH 2.0 V) -> 5 V logic out to the BTS7960B IN/INH.\n'
            '/1OE and /2OE tied low (always enabled). 10k pull-downs keep the bridges off while the ESP32 boots.\n'
            'Unused inputs 1A3/2A3 tied to GND, unused outputs left open.', 20, 20)
    sh.place('U301', '74xx', '74HCT244', 140, 100, '74HCT244', 'Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm',
             {'2': 'H:L_INA', '18': 'H:L_INA_5V', '4': 'H:L_INB', '16': 'H:L_INB_5V',
              '6': 'H:L_EN', '14': 'H:L_EN_5V', '8': 'GND', '12': 'NC',
              '17': 'H:R_INA', '3': 'H:R_INA_5V', '15': 'H:R_INB', '5': 'H:R_INB_5V',
              '13': 'H:R_EN', '7': 'H:R_EN_5V', '11': 'GND', '9': 'NC',
              '1': 'GND', '19': 'GND', '10': 'GND', '20': '+5V'}, lcsc('C5978', '74HCT244D,653'))
    C100n(sh, 'C301', 175, 100, '+5V', 'GND')
    for i, n in enumerate(ins):
        R(sh, 'R%d' % (301 + i), '10k', 60 + 15 * i, 165, 'H:' + n, 'GND', 'boot pull-down')
    return sh


# ======================================================================= MOTOR BRIDGE
def build_bridge(side, page, base):
    P = side
    sh = Sheet('Motor Bridge ' + side, 'motor_bridge_%s.kicad_sch' % side, page=page)
    sh.hier = {P + '_INA_5V': 'input', P + '_INB_5V': 'input', P + '_EN_5V': 'input',
               P + '_IS_A': 'output', P + '_IS_B': 'output'}
    sh.text('MOTOR BRIDGE %s - 2x BTS7960B full H-bridge, %s-side motors (2 in parallel). Plan ~20 A stall.\n'
            'IS: 470R to GND (7 mA fault -> 3.3 V, ~1.1 V at 20 A with kILIS 8500), 1k + 10nF RC, BAT54S clamp to GND/3V3.\n'
            'SR 5.1k sets slew rate (0603: swap 0R = fastest / 51k = slowest).' % (side, 'left' if side == 'L' else 'right'),
            20, 20)
    n = {}

    def ref(pfx):
        n[pfx] = n.get(pfx, base) + 1
        return '%s%d' % (pfx, n[pfx])

    for k, (half, inn, isn, y0) in enumerate([('A', 'INA', 'IS_A', 75), ('B', 'INB', 'IS_B', 165)]):
        h = '%s_%s' % (P, half)
        sh.text('Half-bridge %s' % half, 20, y0 - 25)
        sh.place(ref('U'), 'racebot', 'BTS7960B', 115, y0, 'BTS7960B', 'Package_TO_SOT_SMD:TO-263-7_TabPin8',
                 {'1': 'GND', '2': h + '_IN', '3': h + '_INH', '4': '%s_OUT_%s' % (P, half), '5': h + '_SR',
                  '6': h + '_IS', '7': 'VMOT', '8': '%s_OUT_%s' % (P, half)}, lcsc('C5122776', 'BTS7960B'))
        R(sh, ref('R'), '10k', 40, y0 - 8, 'H:%s_%s_5V' % (P, inn), h + '_IN', 'IN series')
        R(sh, ref('R'), '10k', 52, y0 - 8, 'H:%s_EN_5V' % P, h + '_INH', 'INH series')
        R(sh, ref('R'), '5.1k', 40, y0 + 20, h + '_SR', 'GND', 'slew: fit 0R / 51k to tune')
        R(sh, ref('R'), '470', 55, y0 + 20, h + '_IS', 'GND', 'IS load')
        R(sh, ref('R'), '1k', 70, y0 + 20, h + '_IS', 'H:%s_%s' % (P, isn), 'IS RC filter')
        sh.place(ref('C'), 'Device', 'C', 82, y0 + 20, '10nF 50V X7R', C0603,
                 {'1': 'H:%s_%s' % (P, isn), '2': 'GND'}, lcsc('C57112', '0603B103K500NT'))
        sh.place(ref('D'), 'Diode', 'BAT54S', 160, y0 + 25, 'BAT54S', 'Package_TO_SOT_SMD:SOT-23',
                 {'1': 'GND', '2': '+3V3', '3': 'H:%s_%s' % (P, isn)}, lcsc('C8592', 'BAT54S'))
        sh.place(ref('C'), 'Device', 'C', 145, y0 - 15, '470nF 50V X7R', C0805,
                 {'1': 'VMOT', '2': 'GND'}, lcsc('C13967', 'CL21B474KBFNNNE'))
        C100n(sh, ref('C'), 170, y0 - 15, 'VMOT', 'GND')

    sh.text('VMOT BULK (place at the bridge, star GND point)', 200, 60)
    for i in range(2):
        sh.place(ref('C'), 'Device', 'C_Polarized', 215 + 25 * i, 80, '470uF 25V low-ESR',
                 'Capacitor_THT:CP_Radial_D10.0mm_P5.00mm', {'1': 'VMOT', '2': 'GND'},
                 lcsc('C51018322', 'GA25V470M10X12'))
    sh.text('MOTOR TERMINALS (2 motors in parallel)', 200, 120)
    for i in range(2):
        sh.place(ref('J'), 'Connector', 'Screw_Terminal_01x02', 230, 140 + 20 * i, 'M_%s%d' % (P, i + 1),
                 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',
                 # right side is mirrored on the PCB: swap pins so the front pad is OUT_A on both sides
                 {'1': P + '_OUT_A', '2': P + '_OUT_B'} if side == 'L' else {'1': P + '_OUT_B', '2': P + '_OUT_A'},
                 {**lcsc('C7509570', '1729128'), 'Note': 'front pad = %s_OUT_A' % P})
    return sh


# ======================================================================= ROOT
def build():
    os.makedirs(OUT, exist_ok=True)
    root = Sheet('Root', PROJ + '.kicad_sch', paper='A3', page=1)
    root.uuid = U('root')
    sheets = [build_power(), build_mcu(), build_logic(), build_bridge('L', 5, 400), build_bridge('R', 6, 500)]
    layout = {  # x, y, w, h, left pins, right pins
        'Power': (40, 60, 45, 25, [], ['VBAT_SENSE']),
        'MCU+RX': (120, 60, 50, 45, ['VBAT_SENSE', 'L_IS_A', 'L_IS_B', 'R_IS_A', 'R_IS_B'],
                   ['L_INA', 'L_INB', 'L_EN', 'R_INA', 'R_INB', 'R_EN']),
        'Logic Buffer': (215, 60, 45, 45, ['L_INA', 'L_INB', 'L_EN', 'R_INA', 'R_INB', 'R_EN'],
                         ['L_INA_5V', 'L_INB_5V', 'L_EN_5V', 'R_INA_5V', 'R_INB_5V', 'R_EN_5V']),
        'Motor Bridge L': (305, 60, 50, 25, ['L_INA_5V', 'L_INB_5V', 'L_EN_5V'], ['L_IS_A', 'L_IS_B']),
        'Motor Bridge R': (305, 110, 50, 25, ['R_INA_5V', 'R_INB_5V', 'R_EN_5V'], ['R_IS_A', 'R_IS_B']),
    }
    sheet_blocks = []
    for sh in sheets:
        x, y, w, h, lp, rp = [snap(v) if not isinstance(v, list) else v for v in layout[sh.name]]
        su = U('sheetsym', sh.fname)
        sh.path = '/%s/%s' % (root.uuid, su)
        blk = [S('sheet'), [S('at'), x, y], [S('size'), w, h], [S('exclude_from_sim'), S('no')],
               [S('in_bom'), S('yes')], [S('on_board'), S('yes')], [S('dnp'), S('no')],
               [S('stroke'), [S('width'), 0.1524], [S('type'), S('solid')]],
               [S('fill'), [S('color'), 0, 0, 0, 0.0]], [S('uuid'), su],
               [S('property'), 'Sheetname', sh.name, [S('at'), x, r2(y - 0.71), 0],
                [S('effects'), font(1.27, [[S('bold'), S('yes')]]), [S('justify'), S('left'), S('bottom')]]],
               [S('property'), 'Sheetfile', sh.fname, [S('at'), x, r2(y + h + 0.6), 0], [S('hide'), S('yes')],
                [S('effects'), font(), [S('justify'), S('left'), S('top')]]]]
        for side, names in (('L', lp), ('R', rp)):
            for i, nm in enumerate(names):
                py = y + 5.08 + 2.54 * i
                px = x if side == 'L' else x + w
                shape = sh.hier[nm]
                blk.append([S('pin'), nm, S(shape), [S('at'), px, py, 180 if side == 'L' else 0],
                            [S('uuid'), U(sh.fname, 'spin', nm)],
                            [S('effects'), font(), [S('justify'), S('left' if side == 'L' else 'right')]]])
                root.connect(nm, (px, py), (-1, 0) if side == 'L' else (1, 0), stub=5.08)
        blk.append([S('instances'), [S('project'), PROJ, [S('path'), '/' + root.uuid, [S('page'), str(sh.page)]]]])
        sheet_blocks.append(blk)
    root.text('racebot_main - ESP32 + ELRS + 2x BTS7960B H-bridge main board (3S LiPo)\n'
              'Power nets: VMOT (switched, fused battery), +5V (LM2596), +3V3 (ESP32 board LDO), GND.\n'
              'Logic path: ESP32 GPIO (3.3 V) -> 74HCT244 (5 V) -> 10k -> BTS7960B IN/INH.\n'
              'Current sense: BTS IS -> 470R -> 1k/10nF -> BAT54S clamp -> ESP32 ADC1.', 40, 160)
    hier_check(sheets)

    files = {root.fname: root.render(root.uuid, sheet_blocks, is_root=True, path='/' + root.uuid)}
    for sh in sheets:
        files[sh.fname] = sh.render(root.uuid, path=sh.path)
    for k, v in files.items():
        open(os.path.join(OUT, k), 'w', encoding='utf8', newline='\n').write(v)

    lib = [S('kicad_symbol_lib'), [S('version'), 20251024], [S('generator'), 'racebot_gen'],
           [S('generator_version'), '10.0']] + [copy.deepcopy(v) for v in CUSTOM.values()]
    open(os.path.join(OUT, 'racebot.kicad_sym'), 'w', encoding='utf8', newline='\n').write(dump(lib) + '\n')
    open(os.path.join(OUT, 'sym-lib-table'), 'w', encoding='utf8', newline='\n').write(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "racebot")(type "KiCad")(uri "${KIPRJMOD}/racebot.kicad_sym")'
        '(options "")(descr "racebot project symbols"))\n)\n')
    comps = [c for sh in sheets for c in sh.comps]
    json.dump(comps, open(os.path.join(OUT, '..', 'gen_comps.json') if False else
                          os.path.join(os.path.dirname(os.path.abspath(__file__)), 'comps.json'), 'w'), indent=1)
    print('wrote', len(files), 'sheets,', len(comps), 'components')


def hier_check(sheets):
    for sh in sheets:
        used = set()
        for it in sh.items:
            if it[0] == 'hierarchical_label':
                used.add(it[1])
        if used != set(sh.hier):
            raise SystemExit('%s hier mismatch: %s vs %s' % (sh.name, sorted(used), sorted(sh.hier)))


if __name__ == '__main__':
    build()
