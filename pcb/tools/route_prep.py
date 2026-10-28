"""Pre-route fixed copper (BTS pin 4 -> tab) and export Specctra DSN for Freerouting."""
import os, sys
import pcbnew

pcb = os.path.join(sys.argv[1], 'racebot_main.kicad_pcb')


def set_netclasses(pro):
    """Write the Power / Supply5V net classes. Saving a board from Python (or the KiCad MCP autoroute)
    resets them to Default only, so this must run right before the board is loaded for DSN export."""
    import json, copy
    d = json.load(open(pro))
    ns = d['net_settings']
    base = [c for c in ns['classes'] if c['name'] == 'Default'][0]
    base['track_width'] = 0.25

    def cls(name, tw, cl, vd, vdr, prio):
        c = copy.deepcopy(base)
        c.update(name=name, track_width=tw, clearance=cl, via_diameter=vd, via_drill=vdr, priority=prio)
        return c
    ns['classes'] = [base, cls('Power', 0.8, 0.3, 1.0, 0.5, 0), cls('Supply5V', 0.5, 0.25, 0.8, 0.4, 1)]
    pats = [('Power', p) for p in ['VMOT', 'GND', '*BAT_NEG', '*BAT_POS', '*VBAT_F', '*_OUT_A', '*_OUT_B']] +            [('Supply5V', p) for p in ['+5V', '*SW_5V', '+3V3']]
    ns['netclass_patterns'] = [{'netclass': c, 'pattern': p} for c, p in pats]
    json.dump(d, open(pro, 'w'), indent=2)


set_netclasses(os.path.join(sys.argv[1], 'racebot_main.kicad_pro'))
board = pcbnew.LoadBoard(pcb)
mm = pcbnew.FromMM

for fp in board.GetFootprints():
    if fp.GetValue() != 'BTS7960B':
        continue
    p4 = [p for p in fp.Pads() if p.GetNumber() == '4'][0]
    tab = [p for p in fp.Pads() if p.GetNumber() == '8'][0]
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(p4.GetPosition())
    t.SetEnd(pcbnew.VECTOR2I(tab.GetPosition().x, p4.GetPosition().y))
    t.SetWidth(mm(0.8))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(p4.GetNet())
    t.SetLocked(True)
    board.Add(t)

board.Save(pcb)
dsn = os.path.join(sys.argv[1], 'racebot_main.dsn')
print('DSN export:', pcbnew.ExportSpecctraDSN(board, dsn), dsn)
