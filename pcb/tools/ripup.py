import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); n = 0
for t in list(b.GetTracks()):
    if not t.IsLocked() and t.GetNetname() in sys.argv[2:]:
        b.Delete(t); n += 1
b.Save(sys.argv[1]); print('ripped', n)
