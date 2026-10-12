"""Academic performance analysis for an engineering program (one academic period).

Input : grade matrix (.xls/.xlsx/.csv). Required columns: MATERIA, NIVELMALLA, ESTUDIANTE, CORTE 1, CORTE 2,
        EXAMEN FINAL, PORCENTAJE ASISTENCIA, NOTA FINAL, NUM. MATRICULA
Output: aggregated metrics (metrics.json, CSV tables) and charts. Student and teacher identifiers are
        never written to any output file.
Usage : python analysis/academic_performance_analysis.py <grades_file> [output_dir]
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PASS = 7.0   # institutional rule: final grade >= 7/10 passes
src = Path(sys.argv[1]); out = Path(sys.argv[2] if len(sys.argv) > 2 else "assets"); out.mkdir(exist_ok=True, parents=True)
d = pd.read_csv(src) if src.suffix == ".csv" else pd.read_excel(src)
d.columns = [c.strip() for c in d.columns]
d["nf"] = pd.to_numeric(d["NOTA FINAL"], errors="coerce")
d["fail"] = d["nf"] < PASS
d["level"] = d["NIVELMALLA"].str.extract(r"(\d+)")[0].astype(int)
d["att"] = pd.to_numeric(d["PORCENTAJE ASISTENCIA"], errors="coerce")
d["no_final"] = d["EXAMEN FINAL"].isna()

EN = {"ÁLGEBRA LINEAL": "Linear Algebra", "TRATAMIENTOS TÉRMICOS Y SUPERFICIALES": "Heat & Surface Treatments",
      "CÁLCULO DIFERENCIAL": "Differential Calculus", "NEUMATICA E HIDRAULICA": "Pneumatics & Hydraulics",
      "METROLOGÍA E INSTRUMENTACIÓN": "Metrology & Instrumentation", "FÍSICA": "Physics",
      "FUNDAMENTOS DE COMPUTACIÓN": "Computing Fundamentals", "MECÁNICA DE LOS MATERIALES AVANZADA": "Adv. Mechanics of Materials"}

# ---------- metrics ----------
m = {"enrollments": len(d), "students": int(d.ESTUDIANTE.nunique()), "subjects": int(d.MATERIA.nunique()),
     "levels": int(d.level.nunique()), "pass_rate_pct": round(100 * (~d.fail).mean(), 1),
     "mean_final_grade": round(d.nf.mean(), 2), "failed_enrollments": int(d.fail.sum()),
     "students_with_a_fail": int(d[d.fail].ESTUDIANTE.nunique())}
m["students_with_a_fail_pct"] = round(100 * m["students_with_a_fail"] / m["students"], 1)
rep = d[d["NUM. MATRICULA"] >= 2]
m["repeating_students"] = int(rep.ESTUDIANTE.nunique()); m["repeat_enrollments"] = len(rep)
m["repeaters_failing_again"] = int(rep[rep.fail].ESTUDIANTE.nunique())
# grade-formula validation (35% cut 1 + 35% cut 2 + 30% final exam)
calc = 0.35 * d["CORTE 1"] + 0.35 * d["CORTE 2"] + 0.30 * d["EXAMEN FINAL"]
ok = d["EXAMEN FINAL"].notna()
if "NOTA SUPLETORIO" in d:                      # standard path = no make-up exam recorded
    ok &= d["NOTA SUPLETORIO"].isna()
m["formula_checked_enrollments"] = int(ok.sum())
m["formula_match_pct"] = round(100 * ((calc - d.nf).abs()[ok] < 0.02).mean(), 1)
# early warning: first partial below pass mark
low = d["CORTE 1"] < PASS
m["cut1_below7_n"] = int(low.sum())
m["fail_rate_if_cut1_below7_pct"] = round(100 * d.fail[low].mean(), 1)
m["fail_rate_if_cut1_ok_pct"] = round(100 * d.fail[~low].mean(), 1)
m["corr_cut1_final"] = round(d["CORTE 1"].corr(d.nf), 2)
m["corr_attendance_final"] = round(d.att.corr(d.nf), 2)
# missing final exam
m["no_final_exam_enrollments"] = int(d.no_final.sum()); m["no_final_exam_students"] = int(d[d.no_final].ESTUDIANTE.nunique())
m["failed_without_final_exam"] = int((d.no_final & d.fail).sum())
m["share_of_fails_without_final_exam_pct"] = round(100 * m["failed_without_final_exam"] / max(m["failed_enrollments"], 1), 1)

by_level = d.groupby("level").agg(enrollments=("fail", "size"), failed=("fail", "sum"), mean_grade=("nf", "mean")).reset_index()
by_level["fail_rate_pct"] = (100 * by_level.failed / by_level.enrollments).round(1); by_level["mean_grade"] = by_level.mean_grade.round(2)
by_level.to_csv(out / "by_level.csv", index=False)
bands = pd.cut(d.att, [0, 70, 80, 90, 100.1], right=False, labels=["<70%", "70-79%", "80-89%", "90-100%"])
by_att = d.groupby(bands, observed=True).agg(enrollments=("fail", "size"), fail_rate_pct=("fail", lambda s: round(100 * s.mean(), 1))).reset_index()
by_att.columns = ["attendance_band", "enrollments", "fail_rate_pct"]; by_att.to_csv(out / "by_attendance.csv", index=False)
sub = d.groupby("MATERIA").agg(n=("fail", "size"), failed=("fail", "sum")).query("n >= 15")
sub["pct"] = 100 * sub.failed / sub.n
top = sub.sort_values("pct", ascending=False).head(8)
m["top_subjects"] = {EN.get(k, k.title()): {"enrolled": int(r.n), "failed": int(r.failed), "fail_rate_pct": round(r.pct, 1)} for k, r in top.iterrows()}
Path(out / "metrics.json").write_text(json.dumps(m, indent=2, ensure_ascii=False))

# ---------- charts ----------
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
BLUE, RED, GREY = "#2457A6", "#E14B3C", "#B9C3D0"

def save(fig, name): fig.tight_layout(); fig.savefig(out / name); plt.close(fig)

def p_level(ax):
    ax.bar(by_level.level.astype(str), by_level.fail_rate_pct, color=[RED if v == by_level.fail_rate_pct.max() else BLUE for v in by_level.fail_rate_pct])
    for x, v in zip(by_level.level.astype(str), by_level.fail_rate_pct): ax.text(x, v + .3, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_title("Failure rate by curriculum level (%)", loc="left", fontsize=12); ax.set_xlabel("Level")

def p_subject(ax):
    s = top[::-1]; names = [EN.get(k, k.title()) for k in s.index]
    ax.barh(names, s.pct, color=BLUE)
    for i, (p, n, f) in enumerate(zip(s.pct, s.n, s.failed)): ax.text(p + .5, i, f"{p:.1f}%  ({int(f)}/{int(n)})", va="center", fontsize=9)
    ax.set_xlim(0, s.pct.max() * 1.35); ax.set_title("Subjects with the highest failure rate", loc="left", fontsize=12)

def p_att(ax):
    ax.bar(by_att.attendance_band.astype(str), by_att.fail_rate_pct, color=[RED, BLUE, BLUE, BLUE])
    for i, (v, n) in enumerate(zip(by_att.fail_rate_pct, by_att.enrollments)): ax.text(i, v + 1, f"{v:.1f}%\n(n={n})", ha="center", fontsize=9)
    ax.set_ylim(0, 118); ax.set_yticks([0, 25, 50, 75, 100]); ax.set_title("Failure rate by attendance band", loc="left", fontsize=12); ax.set_xlabel("Attendance")

def p_early(ax):
    v = [m["fail_rate_if_cut1_ok_pct"], m["fail_rate_if_cut1_below7_pct"]]
    ax.bar(["First partial ≥ 7", "First partial < 7"], v, color=[BLUE, RED], width=.55)
    for i, x in enumerate(v): ax.text(i, x + .5, f"{x:.1f}%", ha="center", fontsize=11)
    ax.set_title("Early warning: failure rate by first-partial result", loc="left", fontsize=12); ax.set_ylim(0, max(v) * 1.25)

def p_hist(ax):
    ax.hist(d.nf.clip(0, 10), bins=np.arange(0, 10.5, .5), color=GREY, edgecolor="white")
    ax.axvline(PASS, color=RED, ls="--"); ax.text(PASS + .1, ax.get_ylim()[1] * .9, "pass mark = 7", color=RED, fontsize=9)
    ax.set_title("Distribution of final grades", loc="left", fontsize=12); ax.set_xlabel("Final grade (0-10)")

for fn, name, size in [(p_level, "fail_by_level.png", (8, 4.2)), (p_subject, "fail_by_subject.png", (9, 4.6)),
                       (p_att, "fail_by_attendance.png", (7, 4.2)), (p_early, "early_warning.png", (7, 4.2)), (p_hist, "grade_distribution.png", (8, 4.2))]:
    fig, ax = plt.subplots(figsize=size); fn(ax); save(fig, name)

# composite overview
fig = plt.figure(figsize=(14, 9.2)); fig.patch.set_facecolor("white")
fig.suptitle("Academic Performance Dashboard — one academic period, engineering program (anonymized)", x=.04, ha="left", fontsize=15, fontweight="bold")
tiles = [(f"{m['students']}", "students"), (f"{m['enrollments']:,}", "course enrollments"), (f"{m['pass_rate_pct']}%", "enrollment pass rate"),
         (f"{m['students_with_a_fail']} of {m['students']}", "students failed ≥1 course"), (f"{m['repeaters_failing_again']} of {m['repeating_students']}", "repeaters failed again"),
         (f"{m['mean_final_grade']}", "mean final grade")]
for i, (big, small) in enumerate(tiles):
    ax = fig.add_axes([.04 + i * .157, .83, .145, .09]); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, fc="#EEF2F9", ec="none"))
    ax.text(.05, .52, big, fontsize=19, fontweight="bold", color="#173D7A", transform=ax.transAxes); ax.text(.05, .14, small, fontsize=9, color="#5B6B7E", transform=ax.transAxes)
for rect, fn in [([.06, .43, .40, .31], p_level), ([.57, .43, .40, .31], p_early), ([.06, .06, .40, .27], p_att), ([.68, .06, .29, .27], p_subject)]:
    fn(fig.add_axes(rect))
fig.savefig(out / "dashboard_overview.png"); plt.close(fig)
print(json.dumps(m, indent=2, ensure_ascii=False))
