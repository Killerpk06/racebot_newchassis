"""Import the Freerouting session, then add power pours, BTS ground pads and stitching vias."""
import os, sys
import pcbnew

D = sys.argv[1]
pcb = os.path.join(D, 'racebot_main.kicad_pcb')
board = pcbnew.LoadBoard(pcb)
mm = pcbnew.FromMM
W, H, OX, OY = 108.0, 76.0, 100.0, 100.0

if len(sys.argv) > 2 and sys.argv[2] == 'import':
    ok = pcbnew.ImportSpecctraSES(board, os.path.join(D, 'racebot_main.ses'))
    print('SES import:', ok, 'items', len(list(board.GetTracks())))

nets = board.GetNetsByName()


def net(n):
    return nets[n]


def fp(ref):
    return board.FindFootprintByReference(ref)


# --- right terminals: pin1 = OUT_B, pin2 = OUT_A (schematic changed to match the mirrored layout)
for ref in ('J501', 'J502'):
    for p in fp(ref).Pads():
        p.SetNet(net('/Motor Bridge R/R_OUT_B' if p.GetNumber() == '1' else '/Motor Bridge R/R_OUT_A'))
# OUT nets are carried by pours: drop their autorouted copper (keep the locked pin4->tab stubs)
# (board.Delete, not board.Remove: Remove leaves the KiCad 10 SWIG track list unusable)
for t in [t for t in board.GetTracks()
          if t.GetNetname().startswith('/Motor Bridge') and '_OUT_' in t.GetNetname() and not t.IsLocked()]:
    board.Delete(t)



def _dangling_pass():
    pads = [(p, p.GetNetname()) for f in board.GetFootprints() for p in f.Pads()]
    tr = list(board.GetTracks())
    gone = []
    for t in tr:
        if t.Type() == pcbnew.PCB_VIA_T or t.IsLocked():
            continue
        for e in (t.GetStart(), t.GetEnd()):
            ok = False
            for o in tr:
                if o.m_Uuid.AsString() == t.m_Uuid.AsString() or o.GetNetname() != t.GetNetname():
                    continue
                if o.Type() == pcbnew.PCB_VIA_T:
                    ok = (o.GetPosition() - e).EuclideanNorm() < mm(0.05)
                elif o.GetLayer() == t.GetLayer():
                    ok = (o.GetStart() - e).EuclideanNorm() < mm(0.02) or (o.GetEnd() - e).EuclideanNorm() < mm(0.02)
                if ok:
                    break
            if not ok:
                ok = any(n == t.GetNetname() and p.IsOnLayer(t.GetLayer()) and p.HitTest(e, mm(0.01)) for p, n in pads)
            if not ok:
                gone.append(t)
                break
    for t in gone:
        board.Delete(t)
    return len(gone)


for t in [t for t in board.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and t.GetLength() < mm(0.01)]:
    board.Delete(t)
def _on_line(o, pt):
    """True if pt lies on o's centre line (within 0.01 mm)."""
    ax, ay, bx, by = o.GetStart().x, o.GetStart().y, o.GetEnd().x, o.GetEnd().y
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    s = 0 if L == 0 else max(0.0, min(1.0, ((pt.x - ax) * dx + (pt.y - ay) * dy) / L))
    return ((pt.x - ax - s * dx) ** 2 + (pt.y - ay - s * dy) ** 2) ** 0.5 < mm(0.01)


# redundant copies: tracks lying entirely on another same-net, same-layer track's centre line
for t in list(board.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T or t.IsLocked():
        continue
    tid = t.m_Uuid.AsString()
    for o in board.GetTracks():
        oid = o.m_Uuid.AsString()
        if oid == tid or o.Type() == pcbnew.PCB_VIA_T or o.GetNetname() != t.GetNetname() \
                or o.GetLayer() != t.GetLayer():
            continue
        if _on_line(o, t.GetStart()) and _on_line(o, t.GetEnd()) and \
                (o.GetLength() > t.GetLength() or oid < tid):
            board.Delete(t)
            break
while _dangling_pass():
    pass
print('after OUT + dangling cleanup', len(list(board.GetTracks())))
# --- remove any zones from a previous run so the script is repeatable
for z in list(board.Zones()):
    board.Delete(z)


def zone(netname, layer, pts, prio, name=''):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net(netname))
    z.SetAssignedPriority(prio)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    z.SetZoneName(name or netname)
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(mm(OX + x), mm(OY + y))
    board.Add(z)
    return z


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def mirror(pts):
    return [(W - x, y) for x, y in pts]


E = 0.3  # inset from the board edge
# planes: bottom = GND, top = VMOT, with a top GND island under the logic/ESP32 area
zone('GND', pcbnew.B_Cu, rect(E, E, W - E, H - E), 0, 'GND_bottom')
zone('VMOT', pcbnew.F_Cu, rect(E, E, W - E, H - E), 0, 'VMOT_top')
zone('GND', pcbnew.F_Cu, rect(39.6, E, 68.4, 48.6), 1, 'GND_logic_top')

# motor outputs: top-layer pour per half-bridge + bottom strip that joins the two A pads
for side, mir in (('L', False), ('R', True)):
    f = mirror if mir else (lambda p: p)
    a, b = '/Motor Bridge %s/%s_OUT_A' % (side, side), '/Motor Bridge %s/%s_OUT_B' % (side, side)
    zone(a, pcbnew.F_Cu, f(rect(E, E, 23.3, 13.9)), 2, side + '_OUT_A_top')
    zone(b, pcbnew.F_Cu, f(rect(E, 14.5, 23.3, 30.0)), 2, side + '_OUT_B_top')
    zone(a, pcbnew.B_Cu, f(rect(E, 7.5, 11.8, 25.5)), 2, side + '_OUT_A_bottom')

# BTS GND pin 1: top-layer GND pad + vias into the bottom plane
vias = []
for ref in ('U401', 'U402', 'U501', 'U502'):
    m = fp(ref)
    p1 = [p for p in m.Pads() if p.GetNumber() == '1'][0]
    x = pcbnew.ToMM(p1.GetPosition().x) - OX
    y = pcbnew.ToMM(p1.GetPosition().y) - OY
    p7 = [p for p in m.Pads() if p.GetNumber() == '7'][0]
    s = 1 if x < W / 2 else -1                     # pins point toward the board centre
    sy = 1 if p1.GetPosition().y > p7.GetPosition().y else -1   # pin 1 is the outer end of the pin row
    x0, x1 = sorted((x - s * 1.6, x + s * 4.6))
    y0, y1 = sorted((y - sy * 0.6, y + sy * 2.9))
    zone('GND', pcbnew.F_Cu, rect(x0, y0, x1, y1), 3, ref + '_GND')
    for dx in (1.0, 2.7):
        vias.append((x + s * dx + s * 1.0, y + sy * 2.0))

# power entry: BAT_NEG (XT60 - to Q101 drain), BAT_POS (XT60 + to fuse), VBAT_F (fuse to switch)
zone('/Power/BAT_NEG', pcbnew.F_Cu, rect(12.4, 64.6, 23.2, H - E), 2)
zone('/Power/BAT_POS', pcbnew.F_Cu, rect(23.8, 57.8, 30.6, H - E), 2)
zone('/Power/VBAT_F', pcbnew.F_Cu, rect(33.0, 57.8, 41.6, H - E), 2)
zone('GND', pcbnew.F_Cu, rect(E, 66.2, 9.6, H - E), 3, 'Q101_source_GND')
u = fp('U101')
u.SetDuplicatePadNumbersAreJumpers(True)   # LM2596 pin 3 and tab are the same GND inside the part
tab = [p for p in u.Pads() if p.GetNumber() == '3' and p.GetSize().x > mm(5)][0]
tx, ty = pcbnew.ToMM(tab.GetPosition().x) - OX, pcbnew.ToMM(tab.GetPosition().y) - OY
# covers the narrow pin 3 too (pins 1/2/4/5 are other nets and get cleared by the fill)
zone('GND', pcbnew.F_Cu, rect(tx - 11.6, ty - 7.2, tx + 6.8, ty + 7.2), 3, 'U101_tab_GND')
vias += [(tx + 5.7, ty + dy) for dy in (-4.0, 0.0, 4.0)]
vias += [(tx + dx, ty + dy) for dx in (-2.0, 1.0, 4.0) for dy in (-6.4, 6.4)]
vias += [(1.5, 67.5), (6.5, 67.5), (8.0, 74.5), (1.5, 69.5)]

fixed, vias = vias, []

# stitching vias for the top GND island: grid points that clear every other-net item by 0.35 mm
def clear_at(x, y, r):
    pt = pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))
    for t in board.GetTracks():
        if t.GetNetname() == 'GND':
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            if (t.GetPosition() - pt).EuclideanNorm() < mm(r + t.GetWidth(pcbnew.F_Cu) / 2e6):
                return False
        elif t.HitTest(pt, mm(r) + t.GetWidth() // 2):
            return False
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == 'GND' and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and                         (p.GetPosition() - pt).EuclideanNorm() < p.GetDrillSize().x // 2 + mm(0.8):
                    return False          # keep hole-to-hole spacing to same-net PTH pads
                continue
            if p.HitTest(pt, mm(r)) or (p.GetPosition() - pt).EuclideanNorm() < mm(r) + max(p.GetSize().x, p.GetSize().y) // 2:
                return False
    for x0, y0 in vias:
        if abs(x0 - x) < 2.0 and abs(y0 - y) < 2.0:
            return False
    return True


placed = 0
for x, y in fixed:
    if clear_at(x, y, 0.85):
        vias.append((x, y))
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))
        v.SetWidth(mm(1.0))
        v.SetDrill(mm(0.5))
        v.SetNet(net('GND'))
        board.Add(v)
        placed += 1
print('power GND vias placed %d of %d' % (placed, len(fixed)))

stitch = []
gx = 40.6
while gx < 68.0:
    gy = 1.6
    while gy < 48.0:
        if clear_at(gx, gy, 0.85):
            stitch.append((gx, gy))
            vias.append((gx, gy))
        gy += 3.0
    gx += 3.0
for x, y in stitch:
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(OX + x), mm(OY + y)))
    v.SetWidth(mm(0.8))
    v.SetDrill(mm(0.4))
    v.SetNet(net('GND'))
    board.Add(v)
print('stitching vias', len(stitch))

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(pcb)
print('zones', len(list(board.Zones())), 'tracks', len(list(board.GetTracks())))
