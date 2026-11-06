"""Mathematical transcriptions of the 92-entry Sphinx collection.

No published answers or inferred digit assignments are used as solver input.
Untranscribed puzzles remain in the denominator. See README.md for limitations.
"""

SOURCE = "http://cryptarithms.awardspace.us/collection.html"


def predicate(kind, expr, **kwargs):
    return {"kind": kind, "expr": expr, **kwargs}


def corpus():
    entries = {
        i: {
            "id": i,
            "source": SOURCE,
            "spec": None,
            "reason": "Not yet faithfully transcribed; counted as unsupported.",
        }
        for i in range(1, 93)
    }

    def add(i, equations, constraints=(), **kwargs):
        counter = 0
        encoded = []
        for equation in equations:
            parts = []
            for char in equation:
                if char == "?":
                    counter += 1
                    parts.append(f"?{counter}")
                else:
                    parts.append(
                        f"[{char}]" if char.isdigit() and "?" in equation else char
                    )
            encoded.append("".join(parts))
        entries[i] = {
            "id": i,
            "source": SOURCE,
            "spec": {"equations": encoded, "constraints": list(constraints), **kwargs},
        }

    def mul(i, a, b, partials, total, **kwargs):
        entries[i] = {
            "id": i,
            "source": SOURCE,
            "spec": {
                "equations": [],
                "layout": {"kind": "multiplication", "rows": [a, b, *partials, total]},
                **kwargs,
            },
        }

    p = predicate
    mul(
        1,
        "?????A",
        "A??????",
        ["A?A?A?J", "?????A", "???A??N", "???A?V", "?A????I", "?????AE", "JANVIER"],
        "?????????????",
        assignments={"A": 3},
        forbidden_blank_digits=[3],
    )
    add(2, ["ABC=C^4", "BCA=D^4"])
    add(3, ["FAG=E*HBI", "(A-F)^2=1", "G-A=A-F"])
    add(6, ["KED=E*GB", "(E-K)^2=1", "D-E=E-K", "(B-G)^2=1"])
    mul(11, "AR??", "RA??", ["????M", "????A", "????R", "MARS"], "????????")
    add(
        13,
        ["SPA=SPA"],
        [
            *[p("prime", w) for w in ["ROME", "PARIS", "ARRAS", "ARLON", "LENS"]],
            *[p("prime", f"{w}/7") for w in ["NIMES", "ANS", "MONS"]],
            p("square", "SPA"),
        ],
    )
    mul(
        17,
        "?????A",
        "MAI",
        ["???????", "???????", "??EN???"],
        "PRINTEMPS",
        equations=["ST^2=MAI"],
    )
    add(
        19,
        ["ROSE=ROSE", "INNES=INNES"],
        [p("square", "ROSE"), p("square", "INNES"), p("prime", "OR")],
    )
    mul(20, "ETE", "???", ["??21", "JUIN", "???"], "??2??1")
    add(23, ["NED+SASH=2*SHUN", "NED*SASH=SEND^2", "2*NED*SASH=SEED*(NED+SASH)"])
    add(
        26,
        ["AOUT+ATAO=TU?U", "TUOA-U?TT=O?T?"],
        [p("prime", "AOUT"), p("prime", "TUOA")],
    )
    mul(27, "ABCDE", "FGA", ["??H???", "BB???", "??H???"], "?F???D??")
    add(
        28,
        ["ABCB=ABCB", "BCAD=BCAD", "CBAD=CBAD"],
        [p("square", w) for w in ["ABCB", "BCAD", "CBAD"]],
    )
    add(
        29,
        ["ABCDE=ABCDE", "BACED=BACED"],
        [
            p("square", "ABCDE"),
            p("square", "BACED"),
            p("consecutive_primes", "C+D", other="B+E"),
        ],
    )
    add(30, ["SEPTEMBRE-ERBMETPES=MPPBRPSSM", "SEPTEMBRE+ERBMETPES=B?RBMRREB"])
    add(31, ["ABCABD=DEB^2"])
    add(
        32,
        ["ABCD=ABCD", "CADB=CADB", "CDBA=CDBA"],
        [
            p("divisible", "ABCD", modulus=51),
            p("divisible", "CADB", modulus=33),
            p("divisible", "CDBA", modulus=21),
        ],
    )
    add(33, ["AAAB*7=BEEDC", "AAAB*11=ADDFB"], [p("prime", "AAAB")])
    mul(
        34,
        "BOULE",
        "RADIS",
        ["1????0", "11???0", "101??0", "??0?0", "????0"],
        "?????????",
    )
    add(35, ["O+CTO=BRE"], [p("divisible", "OCTOBRE", modulus=21)])
    mul(
        36,
        "??????",
        "??",
        ["??????", "??????"],
        "OCTOBRE",
        constraints=[
            p("prime", w)
            for w in [
                "OCTO",
                "CTO",
                "CTOB",
                "TO",
                "TOBR",
                "TOBRE",
                "OBRE",
                "BRE",
                "BR",
                "RE",
                "E",
            ]
        ],
    )
    mul(37, "C?AA", "RCCIK", ["AACCK", "?????", "?????", "?????", "?????"], "KRAITCHIK")
    add(
        38,
        ["GALLUS=GALLUS", "AMICUS=AMICUS"],
        [
            p("square", "GALLUS"),
            p("square", "AMICUS"),
            p("prime", "MAN"),
            p("prime", "LANGE"),
            p("prime", "UME/3"),
            p("prime", "GEMIS/3"),
        ],
    )
    mul(39, "TOCK", "TOCK", ["?????", "?????", "?????", "?????"], "????TOCK")
    mul(
        42,
        "VENT",
        "NOVEMBRE",
        ["N???E", "M???R", "O???B", "S???M", "N???E", "E???V", "R???O", "B???N"],
        "????????????",
    )
    add(
        43,
        ["ABACDEBDECA=ABACDEBDECA"],
        [
            *[p("power", w, degree=3) for w in ["ABACDEBDECA", "AB", "ACD", "ECD"]],
            p("square", "EBD"),
        ],
    )
    add(46, ["PHARE=P*I*PA*RA", "DELAI=SH*OEOA", "ALORS=H*SS*ES*OI"])
    mul(
        47,
        "VALISE",
        "MORUE",
        ["???1616", "???????", "???????", "???????", "???3232"],
        "?????161616",
    )
    mul(
        48,
        "ABCDE",
        "CEDBA",
        ["?????", "????F", "?????G", "?????D", "?????A"],
        "??????????",
    )
    mul(
        49,
        "??3?",
        "??3",
        ["3???", "???33", "????"],
        "???????",
        forbidden_blank_digits=[3],
    )
    mul(
        50,
        "RIVE",
        "FLANC",
        ["????0", "????0", "1???0", "?0??0", "1??10"],
        "?1??0???0",
        forbidden_blank_digits=[0, 1],
    )
    add(53, ["????RELUE=LUE^3"])
    add(
        55,
        ["ABCD=ABCD"],
        [
            p("composite", w)
            for w in ["ABCD", "1920CD41", "496BC3", "872AB76", "10A25D8"]
        ],
    )
    add(56, ["-CO+LA=CO"], [p("square", "COLACO")])
    add(
        57,
        ["ABC*BCA*CAB=D63106938"],
        [
            p("inequality", "A", op=">", value="B"),
            p("inequality", "B", op=">", value="C"),
        ],
    )
    add(59, ["LISON=H^2*S*O^4"])
    add(60, ["ABC*ACB*BAC*BCA*CAB*CBA=298316E551967600", "A=2*(E-C)"])
    add(
        62,
        ["RABOUBOUMRAM=RABOUBOUMRAM"],
        [p("divisible", "RABOUBOUMRAM", modulus="2B5200B49")],
    )
    add(63, ["LAVALSEDAN^2=??????????LAVALSEDAN", "SEDAN^2=LAVALSEDAN"])
    add(65, ["1234*???=4???38"])
    mul(
        66,
        "SPHINX",
        "???????",
        ["SPHINX", "XSPHIN", "NXSPHI", "INXSPH", "HINXSP", "PHINXS", "SPHINX"],
        "S??P?HI??N?X",
    )
    mul(
        67,
        "POSITIF",
        "NEGATIF",
        ["????????", "????????", "????????", "0", "????????", "????????", "???????"],
        "N???????EGATIF",
    )
    add(68, ["A^B*C^D=ABCD"], distinct=False)
    mul(
        58,
        "???????",
        "????????",
        [
            "???????Q",
            "T??????U",
            "I??????E",
            "O??????S",
            "S??????T",
            "E??????I",
            "U??????O",
            "QUESTION",
        ],
        "???????????????",
    )
    from workbench_math import normalize_spec
    import re

    expanded = normalize_spec(entries[58]["spec"])
    factors = expanded["source_layout"]["rows"][:2]
    sums58 = [
        "+".join(re.findall(r"\?\d+|\[\d+\]|[A-Z0-9]", factor)) for factor in factors
    ]
    expanded["equations"].append(f"{sums58[0]}={sums58[1]}")
    entries[58]["spec"] = expanded
    add(
        70,
        ["TSRABVOLUE=TSRABVOLUE"],
        [
            p("square", w)
            for w in [
                "TSRABVOLUE",
                "RSBAOVTULE",
                "OSBURVLETA",
                "UBOSLRVEAT",
                "VLSOAEBTRU",
                "AUBTOELSRV",
                "BEOVSALRUT",
                "LTOVABERSU",
                "ELTUSBROVA",
            ]
        ],
    )
    mul(71, "LOTI", "RAVI", ["????T", "L???", "????I", "O????"], "L???E?OT", base=8)
    words = [
        "POIRE",
        "OPERA",
        "PORTE",
        "TAPIS",
        "ASTRE",
        "PATRE",
        "LOTUS",
        "LISTE",
        "LOUPE",
        "OUTRE",
    ]
    sums = ["(" + "+".join(w) + ")" for w in words]
    add(
        73,
        [f"{sums[j + 1]}-{sums[j]}={sums[1]}-{sums[0]}" for j in range(1, 9)],
        [p("inequality", sums[1], op=">", value=sums[0])],
    )
    add(74, ["SELLES=SELLES"], [p("square", "SELLES")])
    mul(
        75,
        "VALSE",
        "SLAVE",
        ["??????", "??????", "??????", "?????", "?????"],
        "???????LE",
        domains={v: [2, 3, 5, 7] for v in "VALSE"},
        distinct=False,
    )
    add(
        77,
        [
            "LEGROGDELAFERMIERE+EREIMREF ALEDGORGEL=3??14??15??????9??".replace(
                " ", ""
            ),
            "ADELE+ROGER=98937",
        ],
    )
    add(78, ["OHEM=RG^2", "OMLI=RA^2", "RA=RG+1", "RG+RA=LET", "OHEM+OMLI=RTOR"])
    mul(
        79, "XSPHI", "?????", ["SPHINX", "0", "XSPHI", "INXSPH", "HINXSP"], "?S???SSS??"
    )
    add(80, ["GALON=GOO^2", "ALONG=OOG^2"], base=6)
    grid = [
        "RL AA CN BD RC",
        "AE MC ML EA RB",
        "UA MB EE LR AU",
        "BR EU LM LN UE",
        "BN LD NC UU BM",
    ]
    cells = [r.split() for r in grid]
    lines = (
        cells
        + [list(c) for c in zip(*cells)]
        + [[cells[i][i] for i in range(5)], [cells[i][4 - i] for i in range(5)]]
    )
    add(81, ["+".join(line) + "=275" for line in lines])
    add(82, ["ALGER=R^2*NIG", "DELTA=R*(AADR*O+R)"], [p("prime", "R")])
    add(
        83,
        ["AMICUS=AMICUS"],
        [p("square", w) for w in ["AMICUS", "A", "ICUS", "US"]]
        + [p("power", "MI", degree=5)],
        base=6,
    )
    add(85, ["AAAU^2=ALUMINE", "(A+A+A+U)^2=A+L+U+M+I+N+E"])
    add(86, ["NXPSI*H=SPHINX"])
    add(89, ["ABBCCA=ABBCCA", "C=2*B"], [p("square", "ABBCCA")])
    seq = ["NC", "NL", "NO", "NU", "TD", "TS", "TA"]
    add(
        90,
        [f"{seq[j + 1]}-{seq[j]}=NL-NC" for j in range(1, 6)]
        + ["+".join(seq) + "=INI"],
        [p("inequality", "NL", op=">", value="NC")],
    )
    add(91, ["CHINE+INDE=HOEEC", "CHINE-INDE=COPRY"])
    mul(
        92,
        "ARRYCAYLUSSETUE",
        "UTLA",
        [
            "YLUSSETUEHARRYCA",
            "AYLUSSETUEHARRYC",
            "CAYLUSSETUEHARRY",
            "YCAYLUSSETUEHARR",
        ],
        "YETSETUEHARRYCAYTTA",
    )
    for i, root, radicand, rows in [
        (5, "??AB", "????????", ["??", "???", "A??", "????", "B???", "????", "????"]),
        (10, "AA?", "?????A", ["??", "????", "????", "?????", "?????"]),
        (12, "?AB", "??????", ["?A", "???", "??B", "?????", "?????"]),
        (15, "?B?", "????A", ["?", "???", "??", "???", "???"]),
        (22, "BA?", "?????A", ["?A", "????", "???C", "????", "????"]),
        (24, "????", "JUILLET", ["?", "??", "??", "???", "???", "?????", "?????"]),
        (25, "AA?", "?????A", ["??", "???", "???", "????", "A???"]),
        (40, "?R?E", "LAPIERRE", ["?", "???", "???", "????", "????", "?????", "?????"]),
        (41, "??PI", "LAPIERRE", ["?", "???", "???", "????", "????", "?????", "?????"]),
        (44, "????", "DECEMBRE", ["??", "??", "??", "????", "????", "?????", "?????"]),
    ]:
        entries[i] = {
            "id": i,
            "source": SOURCE,
            "spec": {
                "equations": [],
                "layout": {"kind": "root", "rows": [root, radicand, "0", *rows]},
            },
        }
    # Skipped zero quotient/root digits have explicit zero steps rather than rows
    # invented from published answers. #24 and #44 need layout-aware zero skips.
    for i in (24, 44):
        entries[i] = {
            "id": i,
            "source": SOURCE,
            "spec": None,
            "reason": "Root extraction contains omitted zero steps requiring explicit aligned layout.",
        }
    for i in [4, 5, 10, 12, 15, 22, 24, 25, 40, 41, 44, 45, 51, 69]:
        if entries[i]["spec"] is None:
            entries[i]["reason"] = (
                "Requires faithful digit-extraction or intersecting-power layout transcription."
            )
    entries[18]["reason"] = (
        "Large geometric-series digit-location research problem, not a finite digit substitution."
    )
    entries[64]["reason"] = (
        "Requires half-turn numeral glyph semantics, not ordinary multiplication."
    )
    entries[28]["note"] = (
        "Literal ABCB retained. The published answer instead describes ABCD; no silent correction."
    )
    entries[43]["note"] = (
        "Literal ECD cube condition retained; the published key makes ECD=516, which is not a cube."
    )
    entries[75]["note"] = (
        "Modern prime-digit interpretation retained. The published answer includes digit 1, not a modern prime."
    )
    return list(entries.values())
