#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Poisson / Dixon-Coles Asian-Handicap Calculator —— football-match-deep-analysis / tools

从「1X2 赔率」或「期望进球 λ」用 Dixon-Coles(独立泊松+低分平局修正)逐案反算
公平亚盘 / 大小球 / 比分分布。是 playbook §4.1 速查表的精算版。

模型 MODEL
  P(i,j) = τ(i,j;λ,μ,ρ) · Poisson(i;λ) · Poisson(j;μ)   再整体归一化
  Dixon-Coles τ 仅修正 4 个低分格（ρ<0 时增多 0-0/1-1、减少 1-0/0-1，
  以贴合真实足球「低分平局偏多」）：
    τ(0,0)=1-λμρ   τ(0,1)=1+λρ   τ(1,0)=1+μρ   τ(1,1)=1-ρ   其余=1
  默认 ρ=-0.13（Dixon&Coles 1997 经验值）；`--poisson` 等价 ρ=0（退回独立泊松）。

用法 USAGE
  python handicap.py --odds -180 365 540 --total 2.62   # 美式1X2(+可选总进球更准)
  python handicap.py --decimal 1.56 4.50 6.40
  python handicap.py --lambdas 1.90 0.80                 # 直接给期望进球(最精确)
  python handicap.py --probs 0.634 0.212 0.154
  可选： --rho -0.13   --poisson   --total 2.62   --topscores 6   --selftest

说明
  * 实盘对热门常再深约 1/4 球（热门贴水）；反算后对热门向更深 1/4 取整。
  * 仅用于研究/分析，非投注建议。
"""
import argparse
import math
from collections import defaultdict

DEFAULT_RHO = -0.13


def poisson_pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _dc_tau(i, j, lH, lA, rho):
    """Dixon-Coles 低分修正因子（仅 4 格非 1）。"""
    if i == 0 and j == 0:
        return 1.0 - lH * lA * rho
    if i == 0 and j == 1:
        return 1.0 + lH * rho
    if i == 1 and j == 0:
        return 1.0 + lA * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_dist(lH, lA, maxg=15, rho=DEFAULT_RHO):
    """返回 P主/平/客、净胜球分布 diff、总进球分布 tot、BTTS、归一化比分网格。"""
    ph = [poisson_pmf(i, lH) for i in range(maxg + 1)]
    pa = [poisson_pmf(j, lA) for j in range(maxg + 1)]
    raw = {}
    Z = 0.0
    for i in range(maxg + 1):
        for j in range(maxg + 1):
            p = ph[i] * pa[j] * _dc_tau(i, j, lH, lA, rho)
            if p < 0:
                p = 0.0  # 极端 ρ 的数值保护
            raw[(i, j)] = p
            Z += p
    pH = pD = pA = btts = 0.0
    diff = defaultdict(float)
    tot = defaultdict(float)
    grid = {}
    for (i, j), p in raw.items():
        q = p / Z
        grid[(i, j)] = q
        diff[i - j] += q
        tot[i + j] += q
        if i > j:
            pH += q
        elif i == j:
            pD += q
        else:
            pA += q
        if i > 0 and j > 0:
            btts += q
    return pH, pD, pA, diff, tot, btts, grid


def cover_wpl(diff, line):
    """backing HOME -line（line 为 0.5 整数倍）的 (赢, 走水, 输) 概率。"""
    w = pu = l = 0.0
    for d, p in diff.items():
        x = d - line
        if x > 1e-12:
            w += p
        elif abs(x) < 1e-12:
            pu += p
        else:
            l += p
    return w, pu, l


def _even_prob(diff, h):
    a = math.floor(h * 2) / 2
    b = math.ceil(h * 2) / 2

    def half(line):
        w, _, l = cover_wpl(diff, line)
        return w / (w + l) if (w + l) > 0 else 0.5

    if abs(a - b) < 1e-9:
        return half(h)
    return 0.5 * (half(a) + half(b))


def fair_handicap(diff, lo=0.0, hi=4.0, step=0.25):
    """公平主盘 = 免抽水赢盘概率最接近 50% 的让球档。"""
    best = None
    h = lo
    while h <= hi + 1e-9:
        s = abs(_even_prob(diff, h) - 0.5)
        if best is None or s < best[1]:
            best = (h, s, _even_prob(diff, h))
        h += step
    return best[0], best[2]


def fair_ou(tot, lo=0.5, hi=8.5, step=0.5):
    best = None
    line = lo
    while line <= hi + 1e-9:
        over = sum(p for t, p in tot.items() if t > line)
        under = sum(p for t, p in tot.items() if t < line)
        ev = over / (over + under) if (over + under) > 0 else 0.5
        s = abs(ev - 0.5)
        if best is None or s < best[1]:
            best = (line, s, ev)
        line += step
    return best[0], best[2]


# ---- 赔率 / 概率工具 ----
def american_to_prob(o):
    return abs(o) / (abs(o) + 100) if o < 0 else 100 / (o + 100)


def decimal_to_prob(o):
    return 1.0 / o


def devig(ps):
    s = sum(ps)
    return [p / s for p in ps]


def solve_fixed_total(pH_target, total, maxg=15, rho=DEFAULT_RHO):
    """已知总进球 T，二分求 λ主（λ客=T-λ主）使 P(主胜)=目标。"""
    lo, hi = total * 0.5, total
    for _ in range(80):
        lH = (lo + hi) / 2
        lA = max(total - lH, 1e-6)
        pH = score_dist(lH, lA, maxg, rho)[0]
        lo, hi = (lH, hi) if pH < pH_target else (lo, lH)
    lH = (lo + hi) / 2
    return lH, max(total - lH, 1e-6)


def fit_lambdas(pH_t, pD_t, maxg=15, rho=DEFAULT_RHO):
    """无总进球约束时，拟合 (λ主,λ客) 同时逼近 P主 与 P平（粗网格+局部精修）。"""
    def err(lH, lA):
        pH, pD = score_dist(lH, lA, maxg, rho)[:2]
        return (pH - pH_t) ** 2 + (pD - pD_t) ** 2

    best = None
    grid = [x / 20 for x in range(1, 81)]
    for lH in grid:
        for lA in grid:
            e = err(lH, lA)
            if best is None or e < best[0]:
                best = (e, lH, lA)
    _, lH, lA = best
    d = 0.05
    for _ in range(60):
        improved = False
        for dH in (-d, 0, d):
            for dA in (-d, 0, d):
                nH, nA = max(0.01, lH + dH), max(0.01, lA + dA)
                e = err(nH, nA)
                if e < best[0] - 1e-15:
                    best, lH, lA, improved = (e, nH, nA), nH, nA, True
        if not improved:
            d /= 2
        if d < 1e-4:
            break
    return lH, lA, best[0] ** 0.5


def infer_lambdas(probs, total=None, maxg=15, rho=DEFAULT_RHO):
    if total is not None:
        lH, lA = solve_fixed_total(probs[0], total, maxg, rho)
        return lH, lA, None
    return fit_lambdas(probs[0], probs[1], maxg, rho)


def pct(x):
    return f"{100 * x:.1f}%"


def report(lH, lA, probs=None, resid=None, src="", topn=6, maxg=15, rho=DEFAULT_RHO):
    pH, pD, pA, diff, tot, btts, grid = score_dist(lH, lA, maxg, rho)
    h, emp = fair_handicap(diff)
    ouline, overp = fair_ou(tot)
    model = "独立泊松" if abs(rho) < 1e-9 else f"Dixon-Coles ρ={rho:g}"
    out = [f"输入 | {src}", f"模型 | {model}"]
    if probs is not None:
        out.append(f"概率(去抽水) | 主胜 {pct(probs[0])}  平局 {pct(probs[1])}  客胜 {pct(probs[2])}")
    rtxt = "" if resid is None else f"  (拟合残差 {pct(resid)})"
    out.append(f"期望进球     | λ主={lH:.2f}  λ客={lA:.2f}  总={lH + lA:.2f}{rtxt}")
    out.append(f"模型胜平负   | 主胜 {pct(pH)}  平局 {pct(pD)}  客胜 {pct(pA)}")
    out.append("-" * 56)
    out.append(f"亚洲盘口     | 公平主盘  主 -{h:.2f}   (赢盘净概率 {pct(emp)})")
    for line in [h - 0.5, h, h + 0.5]:
        if line < 0:
            continue
        w, pu, l = cover_wpl(diff, round(line * 2) / 2)
        out.append(f"   主 -{line:.2f}: 赢 {pct(w)}  走水 {pct(pu)}  输 {pct(l)}")
    out.append(f"大小球       | 公平主线  {ouline:.1f}   (大球概率 {pct(overp)})")
    out.append(f"双方进球BTTS | 是 {pct(btts)}   否 {pct(1 - btts)}")
    top = sorted(grid.items(), key=lambda kv: kv[1], reverse=True)[:topn]
    sc = "  ".join(f"{i}-{j} ({pct(p)})" for (i, j), p in top)
    out.append(f"最可能比分   | {sc}")
    out.append("-" * 56)
    out.append("提示 | 实盘对热门常再深约¼球(贴水)；ρ 可经联赛数据拟合。仅研究用，非投注建议。")
    return "\n".join(out)


def run_selftest():
    r = DEFAULT_RHO
    cases = []
    # 0) 对称 → 平手
    h0, _ = fair_handicap(score_dist(1.3, 1.3, rho=r)[3])
    cases.append(("对称 λ=1.3/1.3 → 平手", abs(h0) <= 0.25, f"得 -{h0:.2f}"))
    # A) 德国（市场 -1.25/-1.5），总进球约束
    lH, lA = solve_fixed_total(devig([american_to_prob(x) for x in (-180, 365, 540)])[0], 2.62, rho=r)
    hG, _ = fair_handicap(score_dist(lH, lA, rho=r)[3])
    cases.append(("德国 P~.63 总2.62 → ~-1.0", -1.5 <= -hG <= -0.75, f"得 -{hG:.2f}"))
    # B) 巴西（市场 -2/-2.5），总进球约束
    lH, lA = solve_fixed_total(devig([american_to_prob(x) for x in (-800, 1000, 2200)])[0], 3.38, rho=r)
    hB, _ = fair_handicap(score_dist(lH, lA, rho=r)[3])
    cases.append(("巴西 P~.87 总3.38 → ~-2.25", -2.75 <= -hB <= -2.0, f"得 -{hB:.2f}"))
    # C) Dixon-Coles 确实增多平局（vs 独立泊松）
    pD_dc = score_dist(1.3, 1.3, rho=r)[1]
    pD_po = score_dist(1.3, 1.3, rho=0.0)[1]
    cases.append((f"DC 平局({pct(pD_dc)}) > 泊松({pct(pD_po)})", pD_dc > pD_po, f"Δ={pct(pD_dc - pD_po)}"))
    print("=== selftest ===")
    ok = True
    for name, passed, got in cases:
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}  ({got})")
    print("=== 全部通过 ===" if ok else "=== 有失败项 ===")
    return ok


def main():
    ap = argparse.ArgumentParser(description="Poisson/Dixon-Coles Asian-Handicap Calculator")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--odds", nargs=3, type=float, metavar=("H", "D", "A"), help="美式 1X2 赔率")
    g.add_argument("--decimal", nargs=3, type=float, metavar=("H", "D", "A"), help="小数 1X2 赔率")
    g.add_argument("--probs", nargs=3, type=float, metavar=("H", "D", "A"), help="去抽水概率(0-1)")
    g.add_argument("--lambdas", nargs=2, type=float, metavar=("LH", "LA"), help="期望进球")
    g.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--total", type=float, default=None, help="总进球主线约束(更准)")
    ap.add_argument("--rho", type=float, default=DEFAULT_RHO, help=f"Dixon-Coles ρ (默认 {DEFAULT_RHO})")
    ap.add_argument("--poisson", action="store_true", help="退回独立泊松 (ρ=0)")
    ap.add_argument("--topscores", type=int, default=6)
    ap.add_argument("--maxg", type=int, default=15)
    args = ap.parse_args()

    if args.selftest:
        raise SystemExit(0 if run_selftest() else 1)

    rho = 0.0 if args.poisson else args.rho

    if args.lambdas:
        lH, lA = args.lambdas
        print(report(lH, lA, src=f"期望进球 λ主={lH} λ客={lA}", topn=args.topscores, maxg=args.maxg, rho=rho))
        return

    if args.odds:
        ps = [american_to_prob(o) for o in args.odds]
        src = f"美式赔率 {args.odds}"
    elif args.decimal:
        ps = [decimal_to_prob(o) for o in args.decimal]
        src = f"小数赔率 {args.decimal}"
    else:
        ps = list(args.probs)
        src = f"概率 {args.probs}"
    probs = devig(ps)
    if args.total:
        src += f" | 总进球约束 {args.total}"
    lH, lA, resid = infer_lambdas(probs, total=args.total, maxg=args.maxg, rho=rho)
    print(report(lH, lA, probs=probs, resid=resid, src=src, topn=args.topscores, maxg=args.maxg, rho=rho))


if __name__ == "__main__":
    main()
