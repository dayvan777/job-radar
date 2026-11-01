#!/usr/bin/env python3
"""Build a tailored CV PDF.
Usage: python3 build_cv.py --lang en|de --target "Application for X: Role" --summary "2-3 sentences" --out /path/file.pdf
Run from the folder that holds preamble.tex, cv_en.tex, cv_de.tex and (optional) photo.jpg. Needs xelatex.
Empty --target removes the line. Text is LaTeX-escaped automatically."""
import argparse, os, re, shutil, subprocess, sys, tempfile
p = argparse.ArgumentParser()
p.add_argument("--lang", choices=["en", "de"], required=True)
p.add_argument("--target", default="")
p.add_argument("--summary", required=True)
p.add_argument("--out", required=True)
a = p.parse_args()
def esc(s):
    s = s.replace("\u2014", "-").replace("\u2013", "-")
    m = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(m.get(c, c) for c in s)
here = os.path.dirname(os.path.abspath(__file__))
tex = open(os.path.join(here, f"cv_{a.lang}.tex"), encoding="utf-8").read()
tex = tex.replace("%%TARGET%%", esc(a.target)).replace("%%SUMMARY%%", esc(a.summary))
d = tempfile.mkdtemp()
for f in ("preamble.tex", "photo.jpg"):  # photo.jpg is optional
    if os.path.exists(os.path.join(here, f)):
        shutil.copy(os.path.join(here, f), d)
open(os.path.join(d, "cv.tex"), "w", encoding="utf-8").write(tex)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", "cv.tex"], cwd=d, capture_output=True, text=True)
pdf = os.path.join(d, "cv.pdf")
if not os.path.exists(pdf):
    sys.exit("build failed:\n" + r.stdout[-3000:])
pages = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
n = int(re.search(r"Pages:\s+(\d+)", pages).group(1))
shutil.copy(pdf, a.out)
print(f"ok {a.out} pages={n}" + ("  WARNING: more than 1 page, shorten the summary" if n > 1 else ""))
