"""Population-share ledger: reads candidate populations per ledger row and
divides by the lowest standard world-population series, keeping the date
that gives each city its highest share (skill: peak-city-world-share)."""
import csv, glob, sys, os

# Lowest standard world population series, millions.
# McEvedy & Jones before 1700 except where Biraben is lower (700, 900-1100);
# Maddison 1700, 1870, 1913-1940; the skill's 1,547M for 1900;
# UN WPP 2022 for 1950-2020, WPP 2024 for 2024-2025.
KNOTS = [(-4000,7),(-3000,14),(-2000,27),(-1000,50),(-500,100),(-200,150),
 (1,170),(200,190),(500,190),(600,200),(700,206),(800,220),(900,226),
 (1000,254),(1100,301),(1200,360),(1300,360),(1400,350),(1500,425),
 (1600,545),(1700,603),(1750,720),(1800,900),(1850,1200),(1870,1272),
 (1900,1547),(1913,1791),(1920,1860),(1930,2070),(1940,2299),(1950,2499),
 (1955,2746),(1960,3019),(1965,3329),(1970,3695),(1975,4069),(1980,4444),
 (1985,4862),(1990,5316),(1995,5743),(2000,6149),(2005,6558),(2010,6986),
 (2015,7427),(2020,7841),(2024,8162),(2025,8232)]
WORLD_2025 = 8232.0

def world(y):
    if y <= KNOTS[0][0]:
        return float(KNOTS[0][1])
    for (y0,w0),(y1,w1) in zip(KNOTS, KNOTS[1:]):
        if y0 <= y <= y1:
            return w0 + (w1-w0)*(y-y0)/(y1-y0)
    return float(KNOTS[-1][1])

def method(flags):
    f = flags.split(';')
    if 'PR' in f: return 'precedent'
    if 'R' in f: return 'reversed'
    if 'A' in f: return 'area'
    return 'count'

def label(y):
    return f"{-y} BC" if y < 0 else (f"AD {y}" if y < 1000 else str(y))

def main(ledger, datadir, out):
    rows = list(csv.DictReader(open(ledger, encoding='utf-8')))
    byrank = {int(r['rank']): r for r in rows}
    cands = {}
    for f in sorted(glob.glob(os.path.join(datadir, 'b*.csv'))):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if not r.get('rank','').strip():
                continue
            k = int(r['rank'])
            y = int(r['year'])
            w = float(r['world_m']) if r.get('world_m','').strip() else world(y)
            raw = r['pop'].strip()
            if raw.startswith('R'):
                # reversed from the ledger's GDP share at a fixed tier multiple
                M = float(raw[1:])
                gdp = float(byrank[k]['cliff_share_pct'])
                p = gdp / M / 100 * w * 1e6
            else:
                p = float(raw)
            cands.setdefault(k, []).append((p/(w*1e6)*100, y, p, w, r['basis'].strip(), r.get('flags','').strip(), f))
    missing = sorted(set(byrank) - set(cands))
    extra = sorted(set(cands) - set(byrank))
    out_rows = []
    for k, r in byrank.items():
        if k not in cands:
            continue
        share, y, p, w, basis, flags, f = max(cands[k], key=lambda t: t[0])
        gdp = float(r['cliff_share_pct'])
        out_rows.append({
            'city': r['city'], 'ledger_rank': k,
            'pop_date': label(y), 'population': int(round(p)),
            'world_pop_millions': round(w, 1),
            'pop_share_pct': share, 'pop_2025_equiv_millions': share/100*WORLD_2025,
            'gdp_snapshot': r['snapshot'], 'gdp_share_pct': gdp,
            'basis': basis, 'flags': flags})
    out_rows.sort(key=lambda d: -d['pop_share_pct'])
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['pop_rank','city','pop_date','population','world_pop_millions',
                    'pop_share_pct','pop_2025_equiv_millions','method','ledger_rank',
                    'gdp_snapshot','gdp_share_pct','basis','flags'])
        for i, d in enumerate(out_rows, 1):
            w.writerow([i, d['city'], d['pop_date'], d['population'], d['world_pop_millions'],
                        f"{d['pop_share_pct']:.4f}", f"{d['pop_2025_equiv_millions']:.2f}",
                        method(d['flags']), d['ledger_rank'], d['gdp_snapshot'], d['gdp_share_pct'],
                        d['basis'], d['flags']])
    print(f"written {len(out_rows)} rows; missing {len(missing)}; extra {extra}")
    if missing:
        print('missing ranks:', missing[:60], '...' if len(missing) > 60 else '')

if __name__ == '__main__':
    main(*sys.argv[1:4])
