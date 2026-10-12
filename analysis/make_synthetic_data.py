"""Generate a SYNTHETIC grade matrix with the same structure as the real one.
No real person, course section or institution is represented. Seeded for reproducibility.
Usage: python analysis/make_synthetic_data.py data/synthetic_grades.csv
"""
import sys
import numpy as np, pandas as pd
rng = np.random.default_rng(42)
LEVELS = [f"{i}º LEVEL" for i in range(1, 11)]
rows = []
for lv_i, lv in enumerate(LEVELS):
    n_students = int(rng.integers(26, 42))
    subjects = [f"SUBJECT L{lv_i+1}-{k+1}" for k in range(int(rng.integers(5, 8)))]
    base = 8.3 + 0.03 * lv_i - (0.6 if lv_i == 0 else 0)      # first level is harder
    for s in range(n_students):
        sid = f"S{lv_i+1:02d}{s+1:03d}"
        ability = rng.normal(0, 0.7)
        for sub in subjects:
            c1 = np.clip(rng.normal(base + ability, 1.1), 0, 10).round(1)
            c2 = np.clip(rng.normal(base + 0.15 + ability, 1.2), 0, 10).round(1)
            att = float(np.clip(rng.normal(92 + 2 * ability, 9), 8, 100).round(0))
            dropped = rng.random() < 0.012 + (0.04 if c2 < 3 else 0)
            fin = np.nan if dropped else np.clip(rng.normal(base + ability - 0.4, 1.5), 0, 10).round(1)
            exam = 0.0 if np.isnan(fin) else fin
            nf = round(0.35 * c1 + 0.35 * c2 + 0.30 * exam, 2)
            rows.append(dict(MATERIA=sub, NIVELMALLA=lv, PARALELO="A", PROFESOR="TEACHER", ESTUDIANTE=sid,
                             **{"CORTE 1": c1, "CORTE 2": c2, "EXAMEN FINAL": fin, "PORCENTAJE ASISTENCIA": att,
                                "NOTA FINAL": nf, "NUM. MATRICULA": int(rng.choice([1, 2, 3], p=[.985, .012, .003]))}))
df = pd.DataFrame(rows)
df["ESTADO"] = np.where(df["NOTA FINAL"] >= 7, "APROBADO", "REPROBADO")
df.to_csv(sys.argv[1], index=False)
print(len(df), "rows,", df.ESTUDIANTE.nunique(), "students")
