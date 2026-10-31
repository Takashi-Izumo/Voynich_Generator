#!/usr/bin/env python3
"""Build two fully standalone English LaTeX books from attested corpus tables.
No dependency on the former statistical/simulation generator. Python standard library only.
"""
import csv
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'

def tab(name):
    with (DATA/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def texplain(s):
    """Escape user supplied text for a LaTeX table cell, one char at a time."""
    escapes = {
        '\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '#': r'\#',
        '_': r'\_', '$': r'\$', '{': r'\{', '}': r'\}',
        '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
        '\n': r'\newline ',
    }
    return ''.join(escapes.get(ch, ch) for ch in str(s))
def eva(s):return '\\EVA{'+s+'}'

COMMON=r'''\documentclass[11pt,a4paper]{article}
\usepackage{fontspec}
\setmainfont{Noto Serif}
\setsansfont{Noto Sans}[Scale=0.94]
\setmonofont{DejaVu Sans Mono}[Scale=0.78]
\usepackage[margin=23mm,headheight=16pt,footskip=13mm]{geometry}
\usepackage{amsmath,amssymb,booktabs,array,tabularx,longtable,multicol,pdflscape}
\usepackage{enumitem,microtype,xcolor,hyperref,fancyhdr,lastpage,titlesec,fancyvrb,needspace}
\definecolor{ink}{HTML}{25384A}
\definecolor{accent}{HTML}{335C73}
\definecolor{soft}{HTML}{657783}
\hypersetup{hidelinks,pdfauthor={Voynich Herbal A Research Project}}
\newcommand{\EVA}[1]{{\ttfamily\detokenize{#1}}}
\newcommand{\STATUS}[1]{\textsf{\bfseries #1}}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\setlist[itemize]{leftmargin=18pt,itemsep=2pt,topsep=4pt}
\setlist[enumerate]{leftmargin=18pt,itemsep=3pt,topsep=4pt}
\titleformat{\section}{\Large\sffamily\bfseries\color{ink}}{}{0pt}{}
\titleformat{\subsection}{\large\sffamily\bfseries\color{accent}}{}{0pt}{}
\titleformat{\subsubsection}{\normalsize\sffamily\bfseries\color{ink}}{}{0pt}{}
\titlespacing*{\section}{0pt}{18pt plus 2pt}{8pt}
\titlespacing*{\subsection}{0pt}{12pt plus 2pt}{5pt}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\footnotesize\sffamily VOYNICH A / OBSERVED GRAMMAR}\fancyhead[R]{\footnotesize\sffamily 31 OCT 2026}\fancyfoot[C]{\footnotesize\thepage\ / \pageref{LastPage}}\renewcommand{\headrulewidth}{0.3pt}
\newcommand{\Evidence}[1]{\par\smallskip{\color{soft}\footnotesize\textit{Evidence note.} #1}\par\smallskip}
'''

BODY=r'''
\begin{document}
\begin{titlepage}
\vspace*{30mm}
{\sffamily\Large\color{accent} VOYNICH HERBAL A\par}
\vspace{10mm}
{\sffamily\Huge\bfseries\color{ink} An Induced\par Compositional\par Surface Grammar\par}
\vspace{11mm}
{\Large\color{ink} Rules inferred from attested Voynich word forms and manuscript positions\par}
\vspace{15mm}
\hrule\vspace{8mm}
{\large Corpus-first English reference edition\par}
{\large 31 October 2026\par}
\vfill
{\bfseries Purpose: to write new, freely composed Voynich-A-style passages while following explicit, auditable surface rules.}\par\vspace{9mm}
{\small This is not a decipherment. There is no verified translation, phonology, part-of-speech system, or sentence semantics. The rules describe observed graphic and positional organization and define a deliberately conservative, usable composition standard.}\par
\end{titlepage}
\tableofcontents
\clearpage

\section{What This Book Is For}
This book starts with \emph{attested Voynich forms}, not a simulation algorithm. It gives a compositional grammar which a human writer can use to create entirely new paragraphs with independently chosen words. The rules are inferred from the supplied line-annotated transcription of \emph{pure Herbal A}, a defined subgroup of the Voynich manuscript. They do not purport to cover every section of the manuscript.

\textbf{There are two different senses of ``grammar.''} In ordinary historical linguistics a grammar may state which expressions convey meanings. Those functions are not recoverable here. This book instead states an \emph{auditable surface grammar}: which glyph sequences occur, how complete word forms are related, what word types occur in different positions, and how lines and paragraphs are arranged. It licenses new \emph{texts}, not proven meaningful utterances.

\subsection{Three evidence labels}
\begin{tabularx}{\textwidth}{@{}p{27mm}Y@{}}\toprule
\STATUS{OBSERVED} & Direct counts, attested glyph sequences, attested word forms, manuscript-position frequencies. \\
\STATUS{LICENSED} & An explicit conservative composition convention. It allows free writing within the observed inventory; it is not claimed to be a historical categorical prohibition. \\
\STATUS{EXPLORATORY} & A recurrent pattern or a new analogical form supported by distributions, not a proven rule of the original script. \\
\bottomrule\end{tabularx}

\subsection{The central principle of free composition}
Choose any topic for yourself; choose any number of paragraphs and any arrangement of the permitted words within the described slots. The slots are \emph{positional}, not semantic. You are not required to copy or paraphrase an existing Voynich line. Word-family carryover, repetition, and morphographic alternation are available as \emph{options}, not obligatory sentence meanings. Where corpus evidence is probabilistic, this manual does not convert it into a universal law.

\section{Source Corpus, Scope, and Reproducibility}
The source is the project-supplied, position-annotated EVA transcription, restricted to the current 85-page pure Herbal A set (Currier A). The file is bundled so that the lexical tables can be recalculated independently. The tables in this edition were made \emph{directly from observed tokens}, without importing any VSL simulation model, candidate ranking, or generated outputs.

\begin{center}\begin{tabular}{@{}lr@{}}\toprule
Observable unit & Count \\\midrule
Surfaces (pages) & \textbf{85}\\
Physical bifolia & \textbf{22}\\
Paragraphs & \textbf{165}\\
Lines & \textbf{1,090}\\
Word tokens & \textbf{6,836}\\
Attested distinct surface words & \textbf{1,971}\\
Observed glyph units & \textbf{23}\\
Observed word-internal bigrams & \textbf{229}\\
Observed word-internal trigrams & \textbf{881}\\
Shared 4--6-glyph routes (operational definition) & \textbf{715}\\
\bottomrule\end{tabular}\end{center}

The 6,836-token basis is the \emph{position-annotated, clean, 23-glyph} corpus and must not be silently exchanged with a separately normalized 6,853-token/28-glyph version. For slot statistics we use the 164 paragraphs containing at least three lines (6,816 word tokens); a two-line paragraph with 20 tokens is in the lexicon but excluded from the canonical three-stage positional analysis. The underlying EVA transcription embodies scribal and editorial choices. Counts of zero mean \emph{not observed here}, never a proven impossibility.

\section{Glyphs and Word Construction}
\subsection{The 23 glyphs}
A word is displayed as an EVA string. The six composite units \EVA{cfh}, \EVA{ckh}, \EVA{cph}, \EVA{cth}, \EVA{ch}, and \EVA{sh} each count as \emph{one glyph} for this study. The other units are single letters of the transliteration. The complete working inventory is:

\begin{quote}\ttfamily\small
q  cfh  ch  cph  cth  p  sh  ckh  f  k  o  t\par
a  d  e  s  i  l  y  r  m  n  g
\end{quote}

Illustrations:
\begin{center}\begin{tabular}{@{}lll@{}}\toprule
Written form & Segmented glyphs & Length\\\midrule
\EVA{chol} & \EVA{ch-o-l} & 3\\
\EVA{daiin} & \EVA{d-a-i-i-n} & 5\\
\EVA{qotchy} & \EVA{q-o-t-ch-y} & 5\\
\EVA{qotchody} & \EVA{q-o-t-ch-o-d-y} & 7\\
\bottomrule\end{tabular}\end{center}

\subsection{The conservative word licence}
\STATUS{Grade A:} every emitted word must be one of the 1,971 \emph{attested} surface types. This is the safest and easiest way to write freely without accidentally inventing impossible-looking local glyph joins. The annotated lexicon makes all types searchable by frequency, glyph length, and manuscript position.

\STATUS{Grade B:} a non-attested form may be licensed by \emph{one} local analogical edit of an attested word that is itself observed in the intended positional slot. The four supported substitution axes are \EVA{ch/sh}, \EVA{k/t}, \EVA{l/r}, and \EVA{o/a}. Single \EVA{i}-run expansion or contraction is also provisionally admitted. The resulting form must still use only the 23 units, have length 1--10 glyphs, and contain only \emph{observed} word-internal bigrams \emph{and} trigrams. These safeguards create a productive analogical sublanguage; they do not prove that the new form was historically legal.

\STATUS{Grade C:} experimental combinations using attested local n-grams without a one-edit parent. They are not part of the conservative grammar and must not be presented as attested vocabulary.

\subsection{The importance of the first \EVA{q}}
In the analyzed sample, 603 word tokens contain \EVA{q}; 600 begin with it, and 597 contain the immediate pair \EVA{q-o}. A writer looking for a typical form should prefer initial \EVA{qo-} to arbitrary placement of \EVA{q}. These are observed proportions, \emph{not} an absolute \EVA{qo} command: all recorded exceptions remain part of the evidence.

\subsection{What is not justified}
A glyph has \emph{not} thereby been shown to encode a sound, an inflection, a tense, a vowel, a digit, or an operation by a historical machine. A legal word-form does not acquire a known translation because it fits this chapter.

\section{A Formal, Productive Paragraph Grammar}
This is the \emph{composition core}: a deliberately conservative, learnable subset. It is narrower than the manuscript (for example, exceptional one-word lines and two-line paragraphs exist) but not a memorized collection of sentences. A passage conforming to this grammar may use arbitrary choices from its role-indexed vocabulary.

\subsection{Nonterminals}
\begin{Verbatim}[fontsize=\small]
PARAGRAPH   := FIRST_LINE NEWLINE INNER_LINE
               (NEWLINE INNER_LINE)* NEWLINE FINAL_LINE
FIRST_LINE  := PHW F1_BODY* F1_LF
INNER_LINE  := HEAD W2 BODY* LF
FINAL_LINE  := PF_HEAD PF_BODY* PF_LF
DOCUMENT    := PARAGRAPH (BLANKLINE PARAGRAPH)*
\end{Verbatim}

Words are separated by spaces. In the print examples, a period may be used as an alternative EVA word separator. A newline terminates a physical line; a blank line terminates the paragraph. The asterisk in the schematic grammar means \emph{any number}, including zero. The core requires at least three lines per paragraph; it does \emph{not} prescribe a maximum number of inner lines. The number of BODY words is freely chosen.

\subsection{What each nonterminal means}
\begin{tabularx}{\textwidth}{@{}p{26mm}Y@{}}\toprule
Slot & Corpus-based meaning\\\midrule
\EVA{PHW} & First word of the paragraph's first line; heavily biased toward gallows starts.\\
\EVA{F1_BODY} & Any interior word of the first line (including its W2).\\
\EVA{F1_LF} & The first line's final word.\\
\EVA{HEAD} & The first word of a noninitial, nonfinal line.\\
\EVA{W2} & Its second word, empirically distinguishable as Post-Head.\\
\EVA{BODY} & Interior words following W2 on a nonfinal line.\\
\EVA{LF} & The line's final word.\\
\EVA{PF_HEAD} & First word of the paragraph's last line.\\
\EVA{PF_BODY} & Interior words on that last line.\\
\EVA{PF_LF} & Final word of the entire paragraph.\\
\bottomrule\end{tabularx}

Unlike an abstract statistical generator, this grammar does not require a hidden \texttt{SETUP} instruction, a latent probability mode, or a prescribed candidate list. Its terminals are plain observed words. The writer can independently select \emph{any} word that appears in the chosen slot's corpus inventory. With this simple rule, whole sentences and paragraphs can be newly written; the particular sequences do not have to be manuscript quotations.

\subsection{The slot-selection rule is conservative, not historical}
For Grade A, require evidence that a word has occurred at least once in \emph{that exact slot}. This produces an easily checked writing standard. It is not the claim that a word never observed at W2 could never have been written at W2 in the 15th century. A supplementary checker can relax the slot rule and report deviations as advisories rather than hard failures.

\subsection{Compositional freedom}
There is no imposed ordering of nouns and verbs, no subject--object template, no finite state that forces particular lexical items, and no requirement that \EVA{daiin} or any other frequent word appear in every paragraph. A writer may choose a line about an arbitrary private subject by associating a label with a word family \emph{for their own composition}; such labels are not translations of the Voynich manuscript.

\section{Observed Preferences that Improve Manuscript-Like Style}
These preferences can guide a writer but are not additional pass/fail rules. Two grade-A compositions can both be formally licensed while differing greatly in their closeness to corpus tendencies.

\subsection{First-line beginnings}
Within the 164 paragraphs with at least three lines, 136 of 164 PHW tokens begin with a gallows glyph \EVA{p/f/k/t}: \textbf{82.9\%}. Ordinary inner HEAD positions show only about \textbf{5.4\%} such starts, and final-line PF-HEAD positions about \textbf{3.2\%}. Thus it is advisable, not mandatory, to start a new paragraph with \EVA{pchor}, \EVA{tchor}, \EVA{tshol}, or another attested PHW form.

\subsection{Length and line space}
The observed average words per physical line is approximately 6.27, with a median of 6; the 25th to 75th percentiles are 5--8, and the full observed range is 1--13. A practical free-writing default is five to eight words per line. It is not a ban on longer or shorter lines. Space constraints arise from handwriting and illustration geometry; they cannot be transformed into a precise mechanical character cap using this text corpus alone.

\subsection{Ends and closure}
The most common word-final glyphs are \EVA{y} (2,202 observed word tokens), \EVA{n} (1,213), \EVA{l} (1,147), and \EVA{r} (1,112). Their distribution changes across line positions. In the core positional sample the mean glyph length is about 4.02 for ordinary LF and 4.63 for PF-LF. A final-line end can therefore sound visually more emphatic through attested terminal choices and length. Nothing establishes that it is a tense or predicate ending.

\subsection{W2 and the ordinary line}
Noninitial middle lines are advantageously written as \EVA{HEAD W2 BODY ... LF}. W2 is a \emph{position}, not a fixed lexeme. Frequently observed W2 forms include \EVA{chol}, \EVA{chor}, \EVA{daiin}, \EVA{shol}, \EVA{chy}, and \EVA{cthy}. We do not impose a separate obligatory lexical class at the second \emph{line}; evidence for a unique L2-W2 board is weaker than evidence for common W2/Post-Head behavior across lines.

\section{Lexical Relatedness Without Imaginary Meanings}
A writer can make new, coherent-looking local series by alternating members of attested graphic paradigms. For example:

\begin{center}\begin{tabularx}{\textwidth}{@{}p{37mm}p{34mm}Y@{}}\toprule
Pair of attested words & Observed token counts & Graphical contrast\\\midrule
\EVA{chol / chor} & 206 / 144 & final \EVA{l/r}\\
\EVA{chol / shol} & 206 / 95 & initial \EVA{ch/sh}\\
\EVA{qokchy / qotchy} & 37 / 44 & interior \EVA{k/t}\\
\EVA{daiin / dain} & 369 / 77 & one \EVA{i} fewer\\
\EVA{dol / dor} & 40 / 33 & final \EVA{l/r}\\
\EVA{chor / char} & 144 / 27 & interior \EVA{o/a}\\
\bottomrule\end{tabularx}\end{center}

The corpus contains 136 distinct \EVA{l>r} attested pairs, 162 \EVA{ch>sh} pairs, 179 \EVA{k>t} pairs, and 153 \EVA{o>a} pairs under the recorded one-glyph substitution test. These are \emph{pairs of existing complete forms}; the figures are not counts of conjugations or semantic agreement.

A form such as \EVA{chol} differs from \EVA{chor} in one terminal glyph. No causal direction of derivation follows: the change might encode a function, reflect a generative branch, or simply be a consequence of dense local letter constraints. This is why the dictionary uses \emph{surface forms} instead of invented noun and verb lemmas.

\section{The Optional Family-Continuity Construction}
\subsection{How to make a topic-like graphic passage}
A \emph{route} is a contiguous sequence of four to six glyphs present inside multiple complete words. For this edition we catalog a route only if it occurs within at least two distinct complete forms, on at least two manuscript surfaces, and in at least three tokens. This editorial definition recovers \textbf{715} routes from the observed sample.

The composition technique is voluntary:
\begin{enumerate}
\item Select one registered route in the route index, for example \EVA{q.o.t.ch} or \EVA{a.i.i.n}.
\item On line 2, choose one or more attested carrier words containing that route, from the corresponding permitted slots.
\item On line 3, choose one or more \emph{different} carrier words containing the same route.
\item On later lines you may maintain the route, change routes, interleave others, or abandon the repetition entirely.
\end{enumerate}

This makes new texts with visible family continuity and does not prescribe an invented meaning for the family. A complete surface word may contain several registered routes, and a word with fewer than four glyphs (such as \EVA{chol}) need not belong to any 4--6-glyph route, despite its high frequency and obvious graphical relationships.

\subsection{What the continuity evidence actually says}
In the 142 four-or-more-line paragraphs, a simple independent re-tabulation of the distinct four-glyph routes shared by line 2 and line 3 gives \textbf{161} observed intersection entries. A 5,000-shuffle comparison that preserves the paragraph and its first and last lines but redistributes the interior words among interior line positions gives mean \textbf{142.1}; 177 of 5,000 randomizations reach or exceed 161 (one-sided plus-one $p\approx0.0356$). This is \emph{exploratory}, not evidence of semantic coreference. Alternative definitions of eligible shared paths have yielded other counts, so the numerical definitions must be kept separate.

Therefore a composition \emph{without} a shared L2--L3 four-glyph route is not ungrammatical. Likewise, no evidence requires a route to make its first-ever appearance precisely on line 2.

\section{How to Write Freely: A Practical Protocol}
\begin{enumerate}
\item \textbf{Choose the scale.} Decide how many paragraphs and how many lines you want. Use at least three lines per paragraph for the conservative classroom grammar; the number of inner lines and BODY tokens is open.
\item \textbf{Choose a first-line entrance.} Consult the lexicon's \EVA{PHW} column. A gallows-initial form is typical, but non-gallows forms occur in the corpus too.
\item \textbf{Fill the first line freely.} Pick any attested \EVA{F1_BODY} forms and end with an attested \EVA{F1_LF} form. You need not reuse any known manuscript phrase.
\item \textbf{Compose line 2.} Pick a \EVA{HEAD}, a \EVA{W2}, any number of \EVA{BODY} forms, and an \EVA{LF}. Optionally elect a four- to six-glyph family to recur later.
\item \textbf{Compose additional ordinary lines.} Keep the slot shape, but vary words. Repeat/contrast forms if stylistically useful; optional family continuity may be present or absent.
\item \textbf{Close the paragraph.} Choose a \EVA{PF_HEAD}, optional \EVA{PF_BODY} words, and a \EVA{PF_LF}. Terminate the paragraph by a blank line.
\item \textbf{Optional creative word-formation.} Switch to Grade B only if you deliberately want new surface forms; apply exactly one supported graphic edit and check the word-internal bigram and trigram lists.
\item \textbf{Check before sharing.} Run the accompanying \EVA{check_composition.py}. Record whether your work is Grade A, B, or C and keep any private semantic glosses explicitly separate.
\end{enumerate}

\subsection{A fully free model of a line}
The key to freedom is the unbounded \EVA{BODY*}. For example, \EVA{HEAD W2 LF} and \EVA{HEAD W2 BODY BODY BODY LF} are both permitted intermediate-line structures. No list of complete sentence templates is stored in the grammar. You select every word yourself from the lexicon, and you may independently choose its frequency level, length, and graphical family.

\section{Two Completely New Grade-A Paragraphs}
The following paragraphs were \emph{newly composed for this book}, using only actual corpus words in the same observed positional roles. They are \textbf{not} quoted from the manuscript and have \textbf{no validated translation}. All 49 tokens pass the accompanying strict Grade-A checker. Their line lengths, lexical makeup, and optional family repetitions are examples, not compulsory templates.

\subsection{Composition I: a \EVA{q.o.t.ch} sequence}
\begin{Verbatim}[fontsize=\small]
pchor shol daiin chor chody shor
qotchy chol qotchor qotchol qotchody
qotchor qotshy daiin qotchol qotchody
qotchol chol dain dy daiin
\end{Verbatim}

Line 1 starts with the attested paragraph head \EVA{pchor}. On line 2, the head \EVA{qotchy} and the words \EVA{qotchor}, \EVA{qotchol}, \EVA{qotchody} share \EVA{q.o.t.ch}. That four-glyph path continues on line 3 through different carrier words. Line 4 selects \EVA{qotchol} as its final-line head and \EVA{daiin} as its paragraph-final word. These are evidence-based \emph{positions}, not sentence meanings.

\subsection{Composition II: an \EVA{a.i.i.n} sequence}
\begin{Verbatim}[fontsize=\small]
tshol shol shor chor chody dy
shodaiin daiin dchor chol shodaiin chaiin
daiin shodaiin chol chody dain daiin
qokchy chor daiin shol cthy
sho chol dy chor daiin
\end{Verbatim}

Here the second and third lines share several four-glyph routes, including \EVA{a.i.i.n}. The fourth line introduces different forms without erasing the paragraph-level surface pattern. The final line ends with an attested paragraph-final \EVA{daiin}. The reader is free to create an unrelated composition that still has the same grammatical status.

\section{A New Grade-B Form, Properly Labelled}
Grade B permits limited, explicitly analogical novel words. For example, \EVA{doin} is \emph{not attested in this 1,971-form pure-A sample}. It is one substitution \EVA{a>o} away from attested \EVA{dain}; the resulting glyph sequence \EVA{d-o-i-n} uses recorded word-internal bigrams/trigrams, and the parent occurs in the relevant BODY slot. In the second example, \EVA{doin} may replace the interior \EVA{dain} on line 3. The supplied \EVA{grade_B_one_edit_original.eva} shows this single substitution and passes Grade B but \emph{fails Grade A}.

This example demonstrates productive \emph{graphic} composition only. Nothing is known about the meanings of \EVA{dain} and \EVA{doin}; the new word must not be presented as a discovered Voynich inflection or a word found in the manuscript.

\section{How to Read the Lexicon and the Checker}
The companion concordance contains all 1,971 attested surface types, indexed by empirical frequency. Each row gives the EVA form, segmented glyphs, glyph length, observed count, number of surfaces and bifolia, a source locus, and the positional evidence. The raw CSV includes ten separate positional-count columns; the printed concordance compacts the columns to the set of observed role labels.

\begin{tabularx}{\textwidth}{@{}p{73mm}Y@{}}\toprule
File or action & Purpose\\\midrule
\EVA{attested_lexicon.csv} & All observed words with exact slot counts and reproducible loci.\\
\EVA{shared_routes.csv} & All 715 registered four- to six-glyph route families and representative carriers.\\
\EVA{word_internal_bigrams.csv} & The 229 observed adjacency types, with counts.\\
\EVA{word_internal_trigrams.csv} & The 881 observed three-glyph paths, with counts.\\
\EVA{attested_single_substitutions.csv} & Empirically co-attested analogical form pairs for four substitution axes.\\
\EVA{check_composition.py} & Check a human-authored text; no automatic text-generation operation.\\
\bottomrule\end{tabularx}

\subsection{The three checker grades}
\begin{Verbatim}[fontsize=\small]
python tools/check_composition.py examples/grade_A_original.eva --level A
python tools/check_composition.py examples/grade_B_one_edit_original.eva --level B
python tools/check_composition.py examples/grade_A_original.eva --level A --json
python tools/check_composition.py --list-role PHW
\end{Verbatim}

For Grade A, a word must be attested \emph{and} attested in the corresponding role. For Grade B, the same is required of the parent of any newly created word, in addition to one analogical edit and observed local glyph connections. Grade C is a flagged research extension. A checker \STATUS{PASS} is never equivalent to ``Voynich meaning confirmed'' or ``authentic manuscript sentence''.

\section{Limitations, Falsifiability, and Responsible Use}
\begin{enumerate}
\item \textbf{No decipherment claim.} The names \EVA{PHW}, \EVA{W2}, \EVA{LF}, and \EVA{PF_LF} describe positions, not nouns, verbs, cases, discourse particles, or tenses.
\item \textbf{No fixed word semantics.} The lexicon contains no English translations because none have been established. A private translation for a creative story remains a convention invented by the writer.
\item \textbf{Finite observation is not universal prohibition.} An unattested trigram, role, or word could appear in a lost page or a different manuscript section. Grade A is a \emph{conservative writing standard}, not a comprehensive historical grammar.
\item \textbf{No claim of universal paragraph staging.} The first line has strong positional anomalies; ``line 2 activates a topic'' is a useful proposed interpretation, not a syntactic fact. Family carryover is weak and nonmandatory.
\item \textbf{No arbitrary n-gram language masquerading as historical proof.} Grade B demands a local attested analogue; Grade C is deliberately flagged. This prevents fictitious words from being silently promoted to evidence.
\item \textbf{One manuscript register.} Pure Herbal A is not identical to Herbal B, the biological/balneological section, or the zodiac and starred texts. Corpus limits must be preserved.
\item \textbf{Drawing geometry is absent.} Positions are obtained from the annotated transcription; botanical boundaries, page width, original writing order, and all scribal readings require independent image checks.
\end{enumerate}

The rules are falsifiable: additional transcriptions could change the 23-glyph alphabet or the observed positional inventories, and new blinded comparisons could challenge the usefulness of the family-continuity construction. The writing guide should then be updated rather than retroactively reinterpreted as a proven ancient syntax.

\section{A One-Page Composition Checklist}
\begin{center}\begin{tabularx}{\textwidth}{@{}p{7mm}Y@{}}\toprule
 & Before calling a new passage Grade A\\\midrule
$\square$ & Every word is present in \EVA{attested_lexicon.csv}.\\
$\square$ & Every word occupies a role in which that exact form was observed.\\
$\square$ & Every paragraph has a first line, at least one inner line, and a final line.\\
$\square$ & First line: \EVA{PHW ... F1_LF}.\\
$\square$ & Ordinary line: \EVA{HEAD W2 ... LF}.\\
$\square$ & Final line: \EVA{PF_HEAD ... PF_LF}.\\
$\square$ & Newlines mark lines; blank lines separate paragraphs.\\
$\square$ & No form or word order is described as a verified meaning, tense, or part of speech.\\
\bottomrule\end{tabularx}\end{center}

\textbf{Optional stylistic goals:} gallows-first paragraph head; about 5--8 words per line; varied but related surface forms; shared four-glyph route on lines 2--3; measured terminal choices. These are not necessary for a formal Grade-A pass.

\clearpage
\appendix
\section{Most Frequent Observed Forms (an Index, Not a Semantic Dictionary)}
The entries below are rank-ordered by observed token count in the 85-page corpus. The exact position counts are supplied in the complete companion concordance and CSV.

% AUTO_TOP_WORDS

\section{Role-Specific Word Banks for Immediate Composition}
Each bank lists the most frequently observed forms in its own slot; you may use any other lexicon entry with a positive count in that same role.

% AUTO_ROLE_BANKS

\section{High-Support Shared Paths for Optional Continuity}
A route is a contiguous sequence of \emph{glyphs}, so a dot in the following index is a glyph boundary, not a space between complete words. These are form-level recurrence inventories, not translations or topics.

% AUTO_ROUTE_BANK

\section{Documented Corpus Example (not a Composition)}
For comparison, the first paragraph of \EVA{f1v} in the bundled annotated dataset begins with these words, preserving line boundaries but replacing EVA separators with spaces:
\begin{Verbatim}[fontsize=\small]
kchsy chydaiin ol o l tchey char cfhar am
yteey char or ochy dcho lkody okodar chody
da ckhy ckhockhy shy dksheey cthy kotchody dal
dol chokeo dair dam sochey chokody
\end{Verbatim}
The paragraph is included as a short \emph{observed attestation} for structural comparison. The two example paragraphs in Chapter 9 were newly arranged and are not manuscript quotations. No semantic reading is assigned to either.

\end{document}
'''

def write_grammar():
    text=COMMON+BODY
    words=tab('attested_lexicon.csv')
    short= '\\begin{longtable}{@{}rllrl@{}}\n\\toprule Rank & Attested form & Glyph units & Count & First locus\\\\\\midrule\\endhead\n'
    for r in words[:80]:
        short+=f"{r['rank']} & {eva(r['form'])} & {eva(r['glyphs'])} & {r['frequency']} & {eva(r['sample_locus'])}\\\\\n"
    short+='\\bottomrule\n\\end{longtable}\n'
    text=text.replace('% AUTO_TOP_WORDS',short)
    banks=''
    for r in tab('position_registrations.csv'):
        ex=r['typical_forms'].split(';')[:14]
        banks+=f"\\subsection*{{{texplain(r['role'])} ({r['tokens']} tokens, {r['attested_types']} types)}}\n"
        banks+='\\begin{quote}\\ttfamily\\small\\sloppy '+ '  '.join(ex)+'\\end{quote}\n'
    text=text.replace('% AUTO_ROLE_BANKS',banks)
    rtxt='\\begin{longtable}{@{}lrrl@{}}\\toprule\nGlyph path & Tokens & Types & Sample carrier\\\\\\midrule\\endhead\n'
    for r in tab('shared_routes.csv')[:45]:
        rtxt+=f"{eva(r['route'])} & {r['containing_tokens']} & {r['distinct_forms']} & {eva(r['examples'].split(';')[0])}\\\\\n"
    rtxt+='\\bottomrule\\end{longtable}\n'
    text=text.replace('% AUTO_ROUTE_BANK',rtxt)
    (ROOT/'Voynich_A_Induced_Compositional_Grammar_EN.tex').write_text(text,encoding='utf-8')

LEX_BODY=r'''\begin{document}
\begin{titlepage}\vspace*{30mm}
{\sffamily\Large\color{accent} COMPANION LEXICAL INDEX\par}\vspace{8mm}
{\sffamily\Huge\bfseries\color{ink} Attested Voynich-A\par Surface Words\par}\vspace{10mm}
{\Large Alphabetical/formal concordance for free composition\par}
\vspace{15mm}\hrule\vspace{8mm}
{\large 1,971 attested types / 715 shared four- to six-glyph routes\par}
{\large Corpus-first English edition, 31 October 2026\par}
\vfill{\small The role abbreviations indicate \emph{observed manuscript positions}, not parts of speech or discovered translations. All entries come from the supplied pure Herbal A lexical corpus; no simulated word has been inserted.}\par
\end{titlepage}
\tableofcontents\clearpage
\section{How to Use This Concordance}
The lexicon lists every distinct clean word form in the 85-page annotated pure Herbal A dataset. Forms are ordered by descending token frequency, so the most reusable evidence comes first. A separate CSV contains all counts, pages, bifolia, glyph segmentation, and source loci. Use this volume as a writing inventory: every entry may be employed freely wherever its observed role permits it. This document \emph{does not} assert what any form means. The two annotation fields, \textbf{Meaning} and \textbf{Part of Speech}, are initially blank for every entry. They are not reconstructions or claims. Use the editable CSV or workbook for typing, or the printed cells for handwriting.

\begin{tabularx}{\textwidth}{@{}p{26mm}Y@{}}\toprule
Column & Description \\\midrule
Rank, word & Rank and complete EVA surface word.\\
N & Token frequency in the defined corpus.\\
Length & Number of segmentation glyphs, with \EVA{ch/sh/cfh/ckh/cph/cth} counted as one glyph.\\
Roles & Space-saving codes for exact slots in which the word was \emph{observed}.\\
Locus & One source line identifier, not the entire set of occurrences.\\
Meaning & Intentionally blank; readers may enter their own conjectured translation.\\
Part of Speech & Intentionally blank; readers may supply their own proposed category.\\
\bottomrule\end{tabularx}

\subsection{Role codes}
\begin{tabularx}{\textwidth}{@{}p{15mm}p{28mm}Y@{}}\toprule
Code & Slot & Details\\\midrule
P & PHW & First word in paragraph first line.\\
I & F1_BODY & Interior word of paragraph first line.\\
J & F1_LF & Last word of paragraph first line.\\
H & HEAD & First word in an ordinary inner line.\\
2 & W2 & Second word of an ordinary inner line.\\
B & BODY & Remaining interior word of inner line.\\
L & LF & Last word of an ordinary inner line.\\
F & PF_HEAD & First word of final line.\\
D & PF_BODY & Interior word of final line.\\
Z & PF_LF & Paragraph's final word.\\
\bottomrule\end{tabularx}

Only paragraphs with at least three lines contribute to slot counts. One two-line paragraph is included in the corpus frequency totals but absent from role classification; this is why rare words can have no printed role code. These entries are not errors and are accessible in the machine-readable table.

\section{Complete Attested Surface Word Inventory (1,971 types)}
The two rightmost columns are \textbf{reader-editable annotations}. Initially they are empty and are not part of corpus-derived evidence. The facing orientation is landscape to leave room for handwriting.
\begin{landscape}
% AUTO_LEXICON
\end{landscape}
\clearpage
\section{Registered Shared Routes (715 operational families)}
A route is a contiguous series of four to six glyphs, and it may overlap other routes inside the same complete word. Inclusion criteria are: at least three containing tokens, at least two distinct complete forms, and appearances on at least two manuscript surfaces. The route is not a proven lexeme or semantic family.

% AUTO_ROUTES
\section{What the Lexicon Does Not Contain}
No noun, verb, adjective, subject, object, person, tense, aspect, number, case, referent, or translation has been assigned to an EVA word \emph{by this research edition}. The new Meaning and Part of Speech fields are blank so that readers can write their own hypotheses; filling them does not turn them into attested facts. Analogical Grade-B innovations are \emph{not} inserted in the attested index; the checker creates a separate innovation audit for them. For examples and a readable syntax of paragraphs, see \emph{An Induced Compositional Surface Grammar}.
\end{document}
'''

def write_lexicon():
    text=COMMON.replace('VOYNICH A / OBSERVED GRAMMAR','VOYNICH A / ATTESTED LEXICON')+LEX_BODY
    for label in ['F1_BODY','F1_LF','PF_HEAD','PF_BODY','PF_LF']:
        text=text.replace(' & '+label+' & ', ' & '+eva(label)+' & ')
    roles={'PHW':'P','F1_BODY':'I','F1_LF':'J','HEAD':'H','W2':'2','BODY':'B','LF':'L','PF_HEAD':'F','PF_BODY':'D','PF_LF':'Z'}
    # Use the independently editable table if present; corpus evidence remains untouched.
    editable = ROOT/'data/attested_lexicon_editable.csv'
    lex_rows = tab('attested_lexicon_editable.csv') if editable.exists() else tab('attested_lexicon.csv')
    # All original evidence columns are retained. New columns stay blank until
    # the reader elects to fill them in the editable CSV.
    lex = (r"\footnotesize\renewcommand{\arraystretch}{1.16}"
           + "\n" + r"\setlength{\tabcolsep}{4.2pt}"
           + "\n" + r"\begin{longtable}{@{}r>{\ttfamily}lrrl>{\ttfamily}l>{\raggedright\arraybackslash}p{80mm}>{\raggedright\arraybackslash}p{36mm}@{}}"
           + "\n" + r"\toprule Rank & Form & N & Len & Roles & Locus & Meaning & Part of Speech\\\midrule\endfirsthead"
           + "\n" + r"\toprule Rank & Form & N & Len & Roles & Locus & Meaning & Part of Speech\\\midrule\endhead"
           + "\n")
    for r in lex_rows:
        rr = ''.join(roles[x] for x in roles if int(r[x])>0) or '-'
        # TeX escape is required for optional user-entered annotation values.
        meaning = texplain(r.get('Meaning',''))
        pos = texplain(r.get('Part of Speech',''))
        lex += (f"{r['rank']} & {r['form']} & {r['frequency']} & {r['glyph_length']} & "
                f"{rr} & {r['sample_locus']} & {meaning} & {pos}" + "\\\\" + "\n")
    lex += r"\bottomrule\end{longtable}\normalsize" + "\n"
    text=text.replace('% AUTO_LEXICON',lex)
    rs='\\footnotesize\\renewcommand{\\arraystretch}{1.10}\n\\begin{longtable}{@{}>{\\ttfamily}lrrrl@{}}\n\\toprule Route (glyph units) & N & Types & Pages & Example carrier\\\\\\midrule\\endfirsthead\n\\toprule Route & N & Types & Pages & Example\\\\\\midrule\\endhead\n'
    for r in tab('shared_routes.csv'):
        rs+=f"{r['route']} & {r['containing_tokens']} & {r['distinct_forms']} & {r['pages']} & {eva(r['examples'].split(';')[0])}\\\\\n"
    rs+='\\bottomrule\\end{longtable}\\normalsize\n'
    text=text.replace('% AUTO_ROUTES',rs)
    (ROOT/'Voynich_A_Attested_Lexicon_EN.tex').write_text(text,encoding='utf-8')

if __name__=='__main__':
    write_grammar();write_lexicon()
    print('wrote standalone TeX (corpus only)')
