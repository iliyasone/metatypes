---
title: "A Meta-Type System for Python: An Expressive Library for Static Typing"
author: "Ilias Dzhabbarov"
date: "May 2026"
geometry: margin=2.5cm
fontsize: 11pt
linkcolor: blue
header-includes:
  - \usepackage{tikz}
  - \usetikzlibrary{arrows.meta, positioning, shapes.geometric, fit, calc, backgrounds}
  - \usepackage{caption}
  - \captionsetup[figure]{name=Fig., labelsep=period, font=small, labelfont=bf}
  - \usepackage{float}
  - \floatplacement{figure}{H}
  - \usepackage{xcolor}
  - \usepackage{framed}
  - \definecolor{shadecolor}{HTML}{EFEFEF}
  - \renewenvironment{Shaded}{\begin{snugshade}}{\end{snugshade}}
---


## 0. Pre-writing (do before chapters)
**Research problem**: Python's type system cannot express types produced by metaprogramming. E.g. the results of many SQL/ORM queries resolve to `Any` or incorrectly-typed attributes. PEP 827 adds type manipulation facilities to close this gap, but exact limits of these tools are unknown.


- Define the **research problem**: locate a gap; answer the Context/Background + Relevance/Specificity questions.
- Formulate **research question(s)** using FINER (Feasible, Interesting, Novel, Ethical, Relevant); use the X→Y phrasing; avoid yes/no, vague, and subjective questions.
- State **hypothesis** with: independent variable, dependent variable, population, relation between them.
- For type 2 specifically: describe the goals of the investigation and the criteria/metrics to assess the outcome.

---

## Front matter
- **Title** — concise, informative, searchable; apply capitalization rules.
- **Abstract** *(write last)* — one paragraph, ≤400 words, EN + RU. Must contain: research gap, limitations of previous research, novelty, objective, method, results, implications. Same structure/sequence as thesis. Tense: match chapters or use present only.
- Table of contents (+ optional: tables of figures, dedication, acknowledgements).

---

## 1. Introduction — *"Why did you do it?"*
Answer:
- What is the problem? Why is it important?
- What is known / not known (research gap)?
- Why must it be researched further?
- Your hypotheses/solutions.
- Your research questions, purpose, objectives.

Structure: Background → Novelty/Gap → Questions/Purpose → (optional) Approach, Results/Conclusions, Significance, Paper Structure Outline.
Tense: Present Simple for aims; Present Perfect for background; Past Simple for results; Present Simple for implications/outline.
*Write this chapter near the end.*

---

## 2. Literature Review — *"What is the state of knowledge?"*
Do: show expertise, respect prior researchers, relate your work to current debates, choose & justify your methods.
Answer: relevant prior work, its relevance to your RQ, citations, whether anyone tried your approach, why do it differently, which methods/metrics to mention, how to classify/evaluate them.
Structure: **Preamble → Body (classify & evaluate prior solutions) → Conclusion (justify your chosen method)**.
Tense: Past Simple (past research), Present Simple (recent/ongoing), Present Perfect (past but still relevant).

---

## 3. Design and Methodology — *"How did you do it? Why that way?"*
Do: describe methods/approaches/processes; link methodology to aims and literature.
Answer: why this method/technology, how theory relates to implementation, underlying assumptions, what you neglected/simplified, what tools/methods, why those.
Tense: Past Simple. *(If math/proof-based, this becomes Analysis using Present Simple.)*

---

## 4. Implementation and Results — *"What did you find? / How did it work?"*
For type 2, describe:
- Results presented to make their relationship to the RQ explicit.
- Estimate of error/reliability + comparison to other systems (Section 3.5) or benchmark metrics.
Answer: Did you build it? How/why did you test it that way?
Tense: Past Simple only. *(Present Simple for math results.)*

---

## 5. Analysis and Discussion — *"What does it mean and so what?"*
Do: interpret findings (don't recapitulate), tie to RQ, discuss accuracy/relevance, compare with other researchers, acknowledge limitations/flaws, show external validity, suggest future directions.
Structure:
1. Interpret key findings (re: purpose)
2. Show how results support them
3. Compare with previous research
4. Explain discrepancies
5. Describe limitations
6. Interpret unexpected findings
7. Show external application

Tense: Present Simple + modals (might/could/may).

---

## 6. Conclusion — *"What are your major findings and their significance?"*
Structure:
1. Restate research purpose/question
2. Summarize main findings
3. Describe significance
4. Describe contribution to the field
5. List limitations
6. Suggest future research

Tense: Present Perfect (looking back), Past Simple (methods/results), Present Simple (significance), Future/modals (implications).

---

## Back matter
- **Bibliography** — IEEE style; no plagiarism (≥70% authenticity); avoid Wikipedia/blogs/non-peer-reviewed; correct in-text citation format ([1], et al.).
- **Appendixes** — extra info not required to follow the thesis; label figures/tables in sequence.

---

## Cross-cutting requirements
- English, **40+ pages** (ToC + chapters; excludes title, appendices, references).
- Follow visuals rules (figures captioned below, tables above, interpret every visual).
- Number/digit rules, list-formatting rules, equation rules as specified.

---

*One note: your guidelines also offer "Alternative contents #2 (research-based / Math thesis): Introduction → Problem and Discussion → Methods and Results → Concluding Discussion." If your work is heavily theoretical/proof-based rather than empirical, that condensed structure may fit better than the 6-chapter default above. Worth confirming with your supervisor which one they expect.*