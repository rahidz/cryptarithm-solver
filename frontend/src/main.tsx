import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Layout = {
  kind: "addition" | "subtraction" | "multiplication" | "division" | "root";
  rows: string[];
};
type Spec = {
  equations: string[];
  base: number;
  assignments: Record<string, number>;
  distinct: boolean;
  mode: string;
  limit: number;
  timeout: number;
  backend: string;
  layout?: Layout;
  [key: string]: unknown;
};
type Puzzle = {
  id: string;
  title: string;
  tags: string[];
  notes: string;
  spec: Spec;
  source?: string;
};
type Benchmark = {
  id: number;
  source: string;
  spec: Partial<Spec> | null;
  reason?: string;
  note?: string;
};
type Solution = {
  assignment: Record<string, number>;
  rendered: string[];
  detail?: {
    kind: string;
    rows: { label: string; original: string; solved: string; value: string }[];
    columns: {
      stage: string;
      operation: string;
      column: number;
      inputs: number[];
      carry_in: number;
      carry_out: number;
      result: number;
      text: string;
    }[];
  };
};
type Result = {
  status?: string;
  solutions?: Solution[];
  unique?: boolean | null;
  complete?: boolean;
  elapsed?: number;
  backend?: string;
  message?: string;
  hints?: { rule: string; text: string; kind: string }[];
  candidates?: Record<
    string,
    { possible: number[]; excluded: number[]; unknown: number[] }
  >;
  spec?: Spec;
  verification?: unknown;
  rows?: Record<string, unknown>[];
  certificate?: unknown;
  identities?: unknown;
  steps?: {
    id: string;
    rule: string;
    source: string;
    premises: Record<string, number[]>;
    variable: string;
    removed: number[];
    remaining: number[];
    text: string;
  }[];
  domains?: Record<string, number[]>;
  solved?: boolean;
  contradiction?: boolean;
};
type Job = {
  id: string;
  state: string;
  result?: Result;
  error?: string;
  elapsed?: number;
};
const initial: Spec = {
  equations: ["SEND + MORE = MONEY"],
  base: 10,
  assignments: {},
  distinct: true,
  mode: "first",
  limit: 100,
  timeout: 30,
  backend: "cp-sat",
};
const examples: Puzzle[] = [
  {
    id: "example-send",
    title: "Send a little more",
    tags: ["Classic", "Addition"],
    notes: "The classic alphametic. Each letter is a different digit.",
    spec: initial,
  },
  {
    id: "example-multiply",
    title: "A reversal of fortune",
    tags: ["Multiplication"],
    notes: "A four-digit number, reversed by multiplying by nine.",
    spec: { ...initial, equations: ["ABCD * 9 = DCBA"] },
  },
  {
    id: "example-skeleton",
    title: "Fill in the gaps",
    tags: ["Skeleton"],
    notes: "Question marks are independent unknown digits.",
    spec: {
      ...initial,
      equations: [],
      layout: { kind: "multiplication", rows: ["1?", "?", "??", "7?"] },
    },
  },
  {
    id: "example-trig",
    title: "Not quite trigonometry",
    tags: ["Advanced"],
    notes: "A numerical identity disguised as familiar functions.",
    spec: { ...initial, equations: ["SIN*SIN + COS*COS = UNITE"] },
  },
  {
    id: "example-division",
    title: "Long story short",
    tags: ["Division"],
    notes: "A long-division layout, with an exact remainder.",
    spec: {
      ...initial,
      equations: [],
      layout: { kind: "division", rows: ["8?", "7", "1?", "0"] },
    },
  },
  {
    id: "example-bases",
    title: "Another number system",
    tags: ["Base 9"],
    notes: "The same arithmetic rules, a different collection of digits.",
    spec: { ...initial, equations: ["ALFRED / E = NEUMAN"], base: 9 },
  },
  {id:'example-certificate',title:'Finite certificate',tags:['Research'],notes:'',spec:{...initial,equations:['A+1=2'],base:3}},
  {id:'example-family',title:'Base-parametric identity',tags:['Research'],notes:'',spec:{...initial,equations:['AB+BA=(A+B)*11'],assignments:{A:1,B:2}}},
];
async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const r = await fetch("/api" + path, {
    method: method || (body === undefined ? "GET" : "POST"),
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  return r.json();
}
function download(name: string, data: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
function importedPuzzle(value: unknown): Puzzle {
  const record = (v: unknown): v is Record<string, unknown> =>
    !!v && typeof v === "object" && !Array.isArray(v);
  const strings = (v: unknown): v is string[] =>
    Array.isArray(v) && v.every((x) => typeof x === "string");
  if (
    !record(value) ||
    typeof value.title !== "string" ||
    (value.notes !== undefined && typeof value.notes !== "string") ||
    (value.tags !== undefined && !strings(value.tags)) ||
    !record(value.spec)
  )
    throw new Error(
      "Puzzle title, tags, notes, or specification has an invalid shape.",
    );
  const s = value.spec;
  if (
    !strings(s.equations) ||
    (s.base !== undefined &&
      (typeof s.base !== "number" ||
        !Number.isInteger(s.base) ||
        s.base < 2 ||
        s.base > 36))
  )
    throw new Error("Puzzle needs string equations and a base from 2 to 36.");
  if (
    s.layout !== undefined &&
    (!record(s.layout) ||
      typeof s.layout.kind !== "string" ||
      ![
        "addition",
        "subtraction",
        "multiplication",
        "division",
        "root",
      ].includes(s.layout.kind) ||
      !strings(s.layout.rows))
  )
    throw new Error("Layout needs a supported kind and string rows.");
  if (
    s.assignments !== undefined &&
    (!record(s.assignments) ||
      Object.values(s.assignments).some(
        (v) => typeof v !== "number" || !Number.isInteger(v),
      ))
  )
    throw new Error("Assignments must map variable names to integer digits.");
  for (const field of ["limit", "timeout"])
    if (
      s[field] !== undefined &&
      (typeof s[field] !== "number" || !Number.isFinite(s[field]))
    )
      throw new Error(field + " must be a finite number.");
  if (s.distinct !== undefined && typeof s.distinct !== "boolean")
    throw new Error("Distinct must be true or false.");
  if (
    s.mode !== undefined &&
    (typeof s.mode !== "string" ||
      !["first", "unique", "limit", "all"].includes(s.mode))
  )
    throw new Error("Unknown search mode.");
  if (
    s.backend !== undefined &&
    (typeof s.backend !== "string" || !["cp-sat", "z3"].includes(s.backend))
  )
    throw new Error("Unknown backend.");
  return {
    id: crypto.randomUUID(),
    title: value.title,
    tags: (value.tags || []) as string[],
    notes: (value.notes || "") as string,
    spec: { ...structuredClone(initial), ...s } as Spec,
    ...(typeof value.source === "string" && /^https?:\/\//.test(value.source)
      ? { source: value.source }
      : {}),
  };
}
function draft(): Puzzle {
  try {
    const p = JSON.parse(localStorage.getItem("cryptarithm-draft") || "null");
    if (p?.spec?.equations)
      return {
        ...importedPuzzle(p),
        id: typeof p.id === "string" ? p.id : crypto.randomUUID(),
      };
  } catch {}
  return {
    id: crypto.randomUUID(),
    title: "Untitled exploration",
    tags: [],
    notes: "",
    spec: structuredClone(initial),
  };
}

function App() {
  const [puzzle, setPuzzle] = useState<Puzzle>(draft),
    [library, setLibrary] = useState<Puzzle[]>([]),
    [page, setPage] = useState("workbench"),
    [tab, setTab] = useState("solution"),
    [query, setQuery] = useState(""),
    [job, setJob] = useState<Job | null>(null),
    [result, setResult] = useState<Result | null>(null),
    [resultContext, setResultContext] = useState<{
      label: string;
      spec: Spec;
    } | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [index, setIndex] = useState(0),
    [validation, setValidation] = useState<{
      valid: boolean;
      errors: unknown[];
      equations?: string[];
      normalized_spec?: Spec;
    } | null>(null),
    [assignText, setAssignText] = useState(""),
    [tagsText, setTagsText] = useState(""),
    [assumption, setAssumption] = useState(""),
    [seed, setSeed] = useState(42),
    [advanced, setAdvanced] = useState("[]"),
    [generationTemplate, setGenerationTemplate] = useState("addition"),
    [generationWidth, setGenerationWidth] = useState(2),
    [experimentKind, setExperimentKind] = useState("backends"),
    [minBase, setMinBase] = useState(2),
    [maxBase, setMaxBase] = useState(16),
    [hintCount, setHintCount] = useState(1);
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [librarySource, setLibrarySource] = useState("personal");
  const [history, setHistory] = useState<Puzzle[]>([]),
    [future, setFuture] = useState<Puzzle[]>([]);
  const startingRef = useRef(false);
  const importRef = useRef<HTMLInputElement>(null),
    eventRef = useRef<EventSource | null>(null);
  const busy = job && ["queued", "running"].includes(job.state),
    spec = puzzle.spec;
  useEffect(() => {
    api<Puzzle[]>("/puzzles")
      .then(setLibrary)
      .catch((e) => setError("Library unavailable: " + e.message));
  }, []);
  useEffect(() => {
    localStorage.setItem("cryptarithm-draft", JSON.stringify(puzzle));
    setTagsText(puzzle.tags.join(", "));
    setAssignText(
      Object.entries(spec.assignments)
        .map(([k, v]) => `${k}=${v}`)
        .join(", "),
    );
    setAdvanced(JSON.stringify(spec.constraints || [], null, 2));
  }, [puzzle]);
  useEffect(() => {
    setValidation(null);
    let active = true;
    const timer = setTimeout(() => {
      api<{
        valid: boolean;
        errors: unknown[];
        equations?: string[];
        normalized_spec?: Spec;
      }>("/validate", spec)
        .then((value) => {
          if (active) setValidation(value);
        })
        .catch(() => {});
    }, 450);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [spec]);
  useEffect(() => () => eventRef.current?.close(), []);
  useEffect(() => {
    api<Benchmark[]>("/benchmarks")
      .then(setBenchmarks)
      .catch(() => {});
  }, []);
  const edit = (p: Puzzle) => {
    if (busy || startingRef.current) {
      setNotice(
        "Cancel the active search before editing or opening another puzzle.",
      );
      return;
    }
    setHistory((h) => [...h.slice(-49), puzzle]);
    setFuture([]);
    setPuzzle(p);
    setValidation(null);
    setResult(null);
    setResultContext(null);
    setNotice("");
    setError("");
  };
  const patch = (s: Partial<Spec>) =>
    edit({ ...puzzle, spec: { ...spec, ...s } });
  const load = (p: Puzzle) => {
    edit({
      ...structuredClone(p),
      spec: { ...structuredClone(initial), ...structuredClone(p.spec) },
    });
    setPage("workbench");
    setResult(null);
  };
  const undo = () => {
    if (busy || startingRef.current) return;
    if (!history.length) return;
    setFuture((f) => [puzzle, ...f]);
    setPuzzle(history[history.length - 1]);
    setHistory(history.slice(0, -1));
    setResult(null);
    setResultContext(null);
  };
  const redo = () => {
    if (busy || startingRef.current) return;
    if (!future.length) return;
    setHistory((h) => [...h, puzzle]);
    setPuzzle(future[0]);
    setFuture(future.slice(1));
    setResult(null);
    setResultContext(null);
  };
  const run = async (
    action = "solve",
    override?: Spec,
    contextLabel?: string,
  ) => {
    if (busy || startingRef.current) return;
    startingRef.current = true;
    setError("");
    setNotice("");
    setResult(null);
    setResultContext(
      contextLabel
        ? { label: contextLabel, spec: structuredClone(override || spec) }
        : null,
    );
    setIndex(0);
    setHintCount(1);
    setTab(
      action === "hint"
        ? "reasoning"
        : action === "candidates"
          ? "candidates"
          : "solution",
    );
    try {
      const j = await api<{ id: string }>("/jobs", {
        spec: override || spec,
        action,
        options: {
          seed,
          kind: action === "generate" ? generationTemplate : experimentKind,
          width: generationWidth,
          min_base: minBase,
          max_base: maxBase,
          timeout: spec.timeout,
        },
      });
      setJob({ id: j.id, state: "queued" });
      eventRef.current?.close();
      const events = new EventSource("/api/jobs/" + j.id + "/events");
      eventRef.current = events;
      events.onmessage = (e) => {
        const next: Job = JSON.parse(e.data);
        setJob(next);
        if (next.result) setResult(next.result);
        if (next.error) setError(next.error);
        if (["done", "error", "cancelled"].includes(next.state)) events.close();
      };
      events.onerror = () => {
        events.close();
        api<Job>("/jobs/" + j.id)
          .then((next) => {
            setJob(next);
            if (next.result) setResult(next.result);
            if (next.error) setError(next.error);
            if (!["done", "error", "cancelled"].includes(next.state))
              setError(
                "Live connection interrupted. Reopen the job status or cancel before retrying.",
              );
          })
          .catch((e) => setError(e.message));
      };
    } catch (e) {
      setError(String(e));
    } finally {
      startingRef.current = false;
    }
  };
  const save = async () => {
    try {
      await api("/puzzles/" + puzzle.id, { ...puzzle }, "PUT");
      setLibrary(await api<Puzzle[]>("/puzzles"));
      setNotice("Saved to your local library.");
    } catch (e) {
      setError(String(e));
    }
  };
  const applyAssignments = () => {
    try {
      const values: Record<string, number> = {};
      if (assignText.trim())
        for (const part of assignText.split(",")) {
          const match = part.trim().match(/^([A-Za-z])\s*=\s*(\d+)$/);
          if (!match) throw new Error("Use assignments such as M=1, O=0.");
          values[match[1].toUpperCase()] = Number(match[2]);
        }
      patch({ assignments: values });
    } catch (e) {
      setError(String(e));
    }
  };
  const importFile = async (file?: File) => {
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      if (data.version !== 1 || !data.puzzle?.spec)
        throw new Error("Expected a version 1 workbench puzzle export.");
      const imported = importedPuzzle(data.puzzle);
      const check = await api<{ valid: boolean; errors: unknown[] }>(
        "/validate",
        imported.spec,
      );
      if (!check.valid) throw new Error(check.errors.map(String).join(" · "));
      load(imported);
      setNotice(
        "Imported as a new draft.",
      );
    } catch (e) {
      setError(String(e));
    }
  };
  const solution = result?.solutions?.[index],
    collectionPuzzles: Puzzle[] = benchmarks
      .filter((b) => b.spec)
      .map((b) => ({
        id: "collection-" + b.id,
        title: "Sphinx collection · " + b.id,
        tags: ["Collection"],
        notes: b.note || '',
        source: b.source,
        spec: { ...structuredClone(initial), ...b.spec },
      })),
    allLibrary =
      librarySource === "collection"
        ? collectionPuzzles
        : librarySource === "examples"
          ? examples
          : library,
    filtered = allLibrary.filter((p) =>
      (p.title + " " + p.tags.join(" "))
        .toLowerCase()
        .includes(query.toLowerCase()),
    );
  const setLayout = (kind: Layout["kind"]) => {
    const defaults: Record<Layout["kind"], string[]> = {
      addition: ["SEND", "MORE", "MONEY"],
      subtraction: ["MONEY", "MORE", "SEND"],
      multiplication: ["ABCD", "9", "DCBA"],
      division: ["8?", "7", "1?", "0"],
      root: ["3?", "1521", "0", "9", "621", "621"],
    };
    patch({ equations: [], layout: { kind, rows: defaults[kind] } });
  };
  return (
    <div className="app">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("workbench");
          }}
        >
          <span className="brand-symbol">α</span>
          <span>cryptarithm</span>
        </a>
        <nav aria-label="Main navigation">
          {[
            ["workbench", "▦", "Workbench"],
            ["library", "▤", "Puzzle library"],
            ["research", "⌘", "Research lab"],
          ].map(([id, icon, label]) => (
            <button
              key={id}
              className={"nav-item " + (page === id ? "selected" : "")}
              onClick={() => setPage(id)}
            >
              <span>{icon}</span>
              {label}
              {id === "library" && <b>{library.length}</b>}
            </button>
          ))}
        </nav>
        <div className="sidebar-label example-label">EXAMPLES</div>
        {examples.slice(0, 4).map((p) => (
          <button
            className="example-link"
            key={p.id}
            onClick={() => load({ ...p, id: crypto.randomUUID() })}
          >
            <span>↗</span>
            {p.title}
          </button>
        ))}
      </aside>
      <main>
        <header className="topbar">
          <span>
            {page === "workbench"
              ? "Workspace / " + puzzle.title
              : page === "library"
                ? "Workspace / Library"
                : "Workspace / Research"}
          </span>
          <div className="top-actions">
            <button
              className="text-button"
              onClick={() => importRef.current?.click()}
            >
              ↥ Import
            </button>
            <button
              className="text-button"
              onClick={() =>
                download("cryptarithm-puzzle.json", { version: 1, puzzle })
              }
            >
              ↧ Export
            </button>
            <button className="small-button" onClick={save}>
              Save puzzle
            </button>
          </div>
        </header>
        <input
          ref={importRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          aria-label="Import puzzle JSON"
          onChange={(e) => {
            importFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        <div className="content">
              <h1 className="page-title">
                {page === "workbench"
                  ? "Workbench"
                  : page === "library"
                    ? "Puzzle library"
                    : "Research lab"}
              </h1>
          {error && (
            <div className="alert error" role="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                ×
              </button>
            </div>
          )}
          {notice && (
            <div className="alert success" role="status">
              {notice}
            </div>
          )}
          {page === "library" ? (
            <>
              <div className="library-toolbar">
                <select
                  aria-label="Library source"
                  value={librarySource}
                  onChange={(e) => setLibrarySource(e.target.value)}
                >
                  <option value="personal">
                    My puzzles ({library.length})
                  </option>
                  <option value="examples">
                    Built-in examples ({examples.length})
                  </option>
                  <option value="collection">
                    Sphinx collection ({collectionPuzzles.length}/
                    {benchmarks.length})
                  </option>
                </select>
                <input
                  aria-label="Search library"
                  placeholder="Search titles or tags…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <button
                  className="primary"
                  onClick={() =>
                    load({
                      id: crypto.randomUUID(),
                      title: "Untitled exploration",
                      tags: [],
                      notes: "",
                      spec: structuredClone(initial),
                    })
                  }
                >
                  ＋ New puzzle
                </button>
              </div>
              {librarySource === "collection" && (
                <div className="collection-note">
                  <p>
                    {collectionPuzzles.length} of {benchmarks.length} source
                    entries have mathematical transcriptions. A transcription is
                    not a solved benchmark; unsupported entries remain in the
                    denominator.
                  </p>
                  <details>
                    <summary>
                      Entries not transcribed (
                      {benchmarks.length - collectionPuzzles.length})
                    </summary>
                    {benchmarks
                      .filter((b) => !b.spec)
                      .map((b) => (
                        <p key={b.id}>
                          <a href={b.source} target="_blank" rel="noreferrer">
                            #{b.id}
                          </a>{" "}
                          · {b.reason}
                        </p>
                      ))}
                  </details>
                </div>
              )}
              {!filtered.length && (
                <p className="help">
                  {librarySource === "personal"
                    ? "No saved puzzles yet. Save your current exploration, or switch to the built-in examples."
                    : "No matching puzzles."}
                </p>
              )}
              <div className="library-grid">
                {filtered.map((p) => (
                  <article className="puzzle-card" key={p.id}>
                    <div className="tags">
                      {p.tags.map((t) => (
                        <span key={t}>{t}</span>
                      ))}
                    </div>
                    <h2>{p.title}</h2>
                    <pre>
                      {p.spec.layout
                        ? p.spec.layout.rows.join("\n")
                        : p.spec.equations.join("\n")}
                    </pre>
                    <p>{p.notes}</p>
                    <div className="card-actions">
                      <button
                        onClick={() =>
                          load(
                            p.id.startsWith("collection-") ||
                              p.id.startsWith("example-")
                              ? { ...p, id: crypto.randomUUID() }
                              : p,
                          )
                        }
                      >
                        Open exploration ↗
                      </button>
                      {p.source && (
                        <a href={p.source} target="_blank" rel="noreferrer">
                          Source ↗
                        </a>
                      )}
                      {!p.id.startsWith("example-") &&
                        !p.id.startsWith("collection-") && (
                          <button
                            className="danger-text"
                            onClick={async () => {
                              if (
                                !confirm(
                                  "Delete “" + p.title + "” from your library?",
                                )
                              )
                                return;
                              try {
                                await api(
                                  "/puzzles/" + p.id,
                                  undefined,
                                  "DELETE",
                                );
                                setLibrary(
                                  library.filter((x) => x.id !== p.id),
                                );
                              } catch (e) {
                                setError(String(e));
                              }
                            }}
                          >
                            Delete
                          </button>
                        )}
                    </div>
                  </article>
                ))}
              </div>
            </>
          ) : (
            <>
              {page === "research" && (
                <section className="panel research-panel" aria-label="Generation and experiment settings">
                  <div className="research-controls">
                    <label>
                      Random seed
                      <input
                        type="number"
                        value={seed}
                        onChange={(e) => setSeed(Number(e.target.value))}
                      />
                    </label>
                    <label>
                      Generator template
                      <select
                        value={generationTemplate}
                        onChange={(e) => setGenerationTemplate(e.target.value)}
                      >
                        <option value="addition">Addition</option>
                        <option value="subtraction">Subtraction</option>
                        <option value="multiplication">Multiplication</option>
                        <option value="division">Division</option>
                      </select>
                    </label>
                    <label>
                      Numeral width
                      <select
                        value={generationWidth}
                        onChange={(e) =>
                          setGenerationWidth(Number(e.target.value))
                        }
                      >
                        {[1, 2, 3].map((n) => (
                          <option value={n} key={n}>
                            {n} digit{n > 1 ? "s" : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Experiment
                      <select
                        value={experimentKind}
                        onChange={(e) => setExperimentKind(e.target.value)}
                      >
                        <option value="backends">Compare CP-SAT / Z3</option>
                        <option value="bases">Finite base sweep</option>
                        <option value="minimal-clues">
                          Minimal assignment clues
                        </option>
                        <option value="proof-search">
                          Verified proof search
                        </option>
                        <option value="adversarial">
                          Adversarial generation
                        </option>
                        <option value="families">Parametric families</option>
                        <option value="certificate">Finite certificate</option>
                      </select>
                    </label>
                    {experimentKind === "bases" && (
                      <>
                        <label>
                          Minimum base
                          <input
                            type="number"
                            min="2"
                            max="36"
                            value={minBase}
                            onChange={(e) => setMinBase(Number(e.target.value))}
                          />
                        </label>
                        <label>
                          Maximum base
                          <input
                            type="number"
                            min="2"
                            max="36"
                            value={maxBase}
                            onChange={(e) => setMaxBase(Number(e.target.value))}
                          />
                        </label>
                      </>
                    )}
                    <button
                      className="primary"
                      disabled={!!busy}
                      onClick={() => run("generate")}
                    >
                      Generate puzzle ↗
                    </button>
                    <button
                      className="secondary"
                      disabled={!!busy}
                      onClick={() => run("experiment")}
                    >
                      Run experiment
                    </button>
                  </div>
                </section>
              )}
              <div className="work-grid">
                <section className="panel editor-panel">
                  <div className="panel-header">
                    <div>
                      <h2>
                        {page === "research" ? "Source puzzle" : "Puzzle"}
                      </h2>
                    </div>
                    <div className="undo-group">
                      <button
                        aria-label="Undo edit"
                        disabled={!history.length}
                        onClick={undo}
                      >
                        ↶
                      </button>
                      <button
                        aria-label="Redo edit"
                        disabled={!future.length}
                        onClick={redo}
                      >
                        ↷
                      </button>
                    </div>
                  </div>
                  <div className="editor-body">
                    <label className="field-label" htmlFor="puzzle-title">
                      TITLE
                    </label>
                    <input
                      id="puzzle-title"
                      className="title-input"
                      value={puzzle.title}
                      onChange={(e) =>
                        edit({ ...puzzle, title: e.target.value })
                      }
                    />
                    <div className="mode-switch">
                      <button
                        className={!spec.layout ? "active" : ""}
                        onClick={() => {
                          if (spec.layout) {
                            const next = validation?.normalized_spec;
                            if (validation?.valid && next) {
                              edit({ ...puzzle, spec: next });
                            } else
                              setNotice(
                                "Validate this layout before converting it to equations. Derived constraints must be preserved.",
                              );
                          }
                        }}
                      >
                        Equation editor
                      </button>
                      <button
                        className={spec.layout ? "active" : ""}
                        onClick={() => {
                          if (!spec.layout) setLayout("addition");
                        }}
                      >
                        Visual skeleton
                      </button>
                    </div>
                    {!spec.layout ? (
                      <>
                        <label className="sr-only" htmlFor="equations">
                          Puzzle equations, one per line
                        </label>
                        <textarea
                          id="equations"
                          className="equation-editor"
                          spellCheck={false}
                          value={spec.equations.join("\n")}
                          onChange={(e) =>
                            patch({ equations: e.target.value.split("\n") })
                          }
                        />
                        <div className="editor-caption">
                          <span>
                            One equation per line · shared letters share digits
                          </span>
                          <span>+ − × / ^</span>
                        </div>
                      </>
                    ) : (
                      <>
                        <label>
                          Arithmetic layout
                          <select
                            aria-label="Arithmetic layout"
                            value={spec.layout.kind}
                            onChange={(e) =>
                              setLayout(e.target.value as Layout["kind"])
                            }
                          >
                            <option value="addition">Column addition</option>
                            <option value="subtraction">
                              Column subtraction
                            </option>
                            <option value="multiplication">
                              Long multiplication
                            </option>
                            <option value="division">Long division</option>
                            <option value="root">Square-root extraction</option>
                          </select>
                        </label>
                        <div className={"skeleton " + spec.layout.kind}>
                          {spec.layout.rows.map((row, i) => (
                            <div
                              className={
                                "skeleton-row " +
                                (i === spec.layout!.rows.length - 1
                                  ? "last"
                                  : "")
                              }
                              key={i}
                            >
                              <label htmlFor={"row-" + i}>
                                {rowLabel(spec.layout!, i)}
                              </label>
                              <div className="skeleton-entry">
                                <input
                                  id={"row-" + i}
                                  aria-label={rowLabel(spec.layout!, i)}
                                  value={row}
                                  spellCheck={false}
                                  onChange={(e) => {
                                    const rows = [...spec.layout!.rows];
                                    rows[i] = e.target.value.toUpperCase();
                                    patch({
                                      layout: { ...spec.layout!, rows },
                                    });
                                  }}
                                  onKeyDown={(e) => {
                                    if (
                                      e.key === "ArrowDown" ||
                                      e.key === "ArrowUp"
                                    ) {
                                      e.preventDefault();
                                      document
                                        .getElementById(
                                          "row-" +
                                            (i +
                                              (e.key === "ArrowDown" ? 1 : -1)),
                                        )
                                        ?.focus();
                                    }
                                  }}
                                />
                                <div
                                  className="cell-preview"
                                  aria-label={
                                    rowLabel(spec.layout!, i) + " digit cells"
                                  }
                                >
                                  {Array.from(row.matchAll(/\[\d+\]|./g)).map(
                                    (match, j) => (
                                      <button
                                        key={j}
                                        className={
                                          match[0] === "?"
                                            ? "blank-cell"
                                            : /^[A-Z]$/.test(match[0])
                                              ? "letter-cell"
                                              : "fixed-cell"
                                        }
                                        aria-label={
                                          rowLabel(spec.layout!, i) +
                                          ", cell " +
                                          (j + 1) +
                                          ": " +
                                          match[0]
                                        }
                                        title="Select this digit in the row editor"
                                        onClick={() => {
                                          const input = document.getElementById(
                                            "row-" + i,
                                          ) as HTMLInputElement;
                                          input.focus();
                                          input.setSelectionRange(
                                            match.index!,
                                            match.index! + match[0].length,
                                          );
                                        }}
                                        onKeyDown={(e) => {
                                          if (
                                            e.key === "ArrowLeft" ||
                                            e.key === "ArrowRight"
                                          ) {
                                            e.preventDefault();
                                            const sibling =
                                              e.key === "ArrowLeft"
                                                ? e.currentTarget
                                                    .previousElementSibling
                                                : e.currentTarget
                                                    .nextElementSibling;
                                            (
                                              sibling as HTMLButtonElement | null
                                            )?.focus();
                                          }
                                        }}
                                      >
                                        {match[0]}
                                      </button>
                                    ),
                                  )}
                                </div>
                              </div>
                              {((spec.layout!.kind === "addition" &&
                                spec.layout!.rows.length > 3 &&
                                i < spec.layout!.rows.length - 1) ||
                                (spec.layout!.kind === "multiplication" &&
                                  i >= 2 &&
                                  i < spec.layout!.rows.length - 1) ||
                                (["division", "root"].includes(
                                  spec.layout!.kind,
                                ) &&
                                  i >= 4 &&
                                  i % 2 === 0)) && (
                                <button
                                  className="remove-row"
                                  aria-label={
                                    "Remove " +
                                    rowLabel(spec.layout!, i) +
                                    (spec.layout!.kind === "division" ||
                                    spec.layout!.kind === "root"
                                      ? " pair"
                                      : "")
                                  }
                                  title="Remove optional row or step pair"
                                  onClick={() => {
                                    const rows = [...spec.layout!.rows];
                                    rows.splice(
                                      i,
                                      ["division", "root"].includes(
                                        spec.layout!.kind,
                                      )
                                        ? 2
                                        : 1,
                                    );
                                    patch({
                                      layout: { ...spec.layout!, rows },
                                    });
                                  }}
                                >
                                  ×
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                        {spec.layout.kind === "addition" && (
                          <button
                            className="text-button"
                            onClick={() => {
                              const rows = [...spec.layout!.rows];
                              rows.splice(rows.length - 1, 0, "?");
                              patch({ layout: { ...spec.layout!, rows } });
                            }}
                          >
                            ＋ Add an addend
                          </button>
                        )}
                        {["multiplication", "division", "root"].includes(
                          spec.layout.kind,
                        ) && (
                          <button
                            className="text-button"
                            onClick={() => {
                              const rows = [...spec.layout!.rows];
                              if (spec.layout!.kind === "multiplication")
                                rows.splice(rows.length - 1, 0, "?");
                              else rows.push("?", "?");
                              patch({ layout: { ...spec.layout!, rows } });
                            }}
                          >
                            ＋{" "}
                            {spec.layout.kind === "root"
                              ? "Add current / product pair"
                              : spec.layout.kind === "division"
                                ? "Add product / difference pair"
                                : "Add partial product"}
                          </button>
                        )}
                        <p className="help">
                          Rows are right-aligned place values. Multiplication
                          partials run from units upward, without shift zeros.
                          Division pairs follow quotient digits left to right.
                          Root extraction brings down two digits per
                          current/product pair. Use ? for independent missing
                          digits.
                        </p>
                      </>
                    )}
                    <div className="validation" aria-live="polite">
                      {validation ? (
                        validation.valid ? (
                          <>
                            <span className="dot" />
                            Ready to explore
                          </>
                        ) : (
                          <span className="invalid">
                            {validation.errors.map(String).join(" · ")}
                          </span>
                        )
                      ) : (
                        <span>Checking puzzle…</span>
                      )}
                    </div>
                    <div className="settings-grid">
                      <label>
                        Number base
                        <input
                          type="number"
                          min="2"
                          max="36"
                          value={spec.base}
                          onChange={(e) =>
                            patch({ base: Number(e.target.value) })
                          }
                        />
                      </label>
                      <label>
                        Search mode
                        <select
                          value={spec.mode}
                          onChange={(e) => patch({ mode: e.target.value })}
                        >
                          <option value="first">Find a solution</option>
                          <option value="unique">Check uniqueness</option>
                          <option value="limit">Find up to N</option>
                          <option value="all">Enumerate all</option>
                        </select>
                      </label>
                      <label>
                        Time budget (seconds)
                        <input
                          type="number"
                          min="1"
                          value={spec.timeout}
                          onChange={(e) =>
                            patch({ timeout: Number(e.target.value) })
                          }
                        />
                      </label>
                      <label>
                        {spec.mode === "limit" ? "Solution limit" : "Solver"}
                        {spec.mode === "limit" ? (
                          <input
                            type="number"
                            min="1"
                            value={spec.limit}
                            onChange={(e) =>
                              patch({ limit: Number(e.target.value) })
                            }
                          />
                        ) : (
                          <select
                            value={spec.backend}
                            onChange={(e) => patch({ backend: e.target.value })}
                          >
                            <option value="cp-sat">OR-Tools CP-SAT</option>
                            <option value="z3">Z3 · experimental</option>
                          </select>
                        )}
                      </label>
                    </div>
                    <label className="checkbox">
                      <input
                        type="checkbox"
                        checked={spec.distinct}
                        onChange={(e) => patch({ distinct: e.target.checked })}
                      />
                      Different letters use different digits
                    </label>
                    <label>
                      Fixed assignments
                      <div className="input-action">
                        <input
                          aria-label="Fixed assignments"
                          placeholder="e.g. M=1, O=0"
                          value={assignText}
                          onChange={(e) => setAssignText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") applyAssignments();
                          }}
                        />
                        <button onClick={applyAssignments}>Apply</button>
                      </div>
                    </label>
                    <details>
                      <summary>Advanced constraints & notes</summary>
                      <label>
                        Constraints (JSON array)
                        <textarea
                          className="code-input"
                          aria-label="Advanced constraints JSON"
                          value={advanced}
                          onChange={(e) => setAdvanced(e.target.value)}
                        />
                      </label>
                      <button
                        className="small-button"
                        onClick={() => {
                          try {
                            const constraints = JSON.parse(advanced);
                            if (!Array.isArray(constraints))
                              throw new Error("Constraints must be an array.");
                            patch({ constraints });
                          } catch (e) {
                            setError(String(e));
                          }
                        }}
                      >
                        Apply constraints
                      </button>
                      <p className="help">
                        Exact predicate constraints are validated by the solver.
                        Export preserves all advanced fields.
                      </p>
                      <label>
                        Tags
                        <input
                          value={tagsText}
                          onChange={(e) => setTagsText(e.target.value)}
                          onBlur={() =>
                            edit({
                              ...puzzle,
                              tags: tagsText
                                .split(",")
                                .map((x) => x.trim())
                                .filter(Boolean),
                            })
                          }
                        />
                      </label>
                      <label>
                        Notes
                        <textarea
                          value={puzzle.notes}
                          onChange={(e) =>
                            edit({ ...puzzle, notes: e.target.value })
                          }
                        />
                      </label>
                    </details>
                    <div className="solve-actions">
                      {busy ? (
                        <button
                          className="primary cancel"
                          onClick={async () => {
                            try {
                              await api("/jobs/" + job.id + "/cancel", {});
                            } catch (e) {
                              setError(String(e));
                            }
                          }}
                        >
                          ■ Cancel search
                        </button>
                      ) : (
                        <button
                          className="primary"
                          disabled={validation?.valid === false}
                          onClick={() => run()}
                        >
                          Solve puzzle <span>→</span>
                        </button>
                      )}
                      <button
                        className="hint-button"
                        disabled={!!busy}
                        onClick={() => run("hint")}
                      >
                        ✧ Get a hint
                      </button>
                    </div>
                  </div>
                </section>
                <section className="panel results-panel">
                  <div className="panel-header">
                    <div>
                      <h2>Results</h2>
                    </div>
                  </div>
                  <div className="result-tabs" role="tablist">
                    {["solution", "reasoning", "candidates"].map((t) => (
                      <button
                        key={t}
                        role="tab"
                        aria-selected={tab === t}
                        className={tab === t ? "active" : ""}
                        onClick={() => setTab(t)}
                      >
                        {t === "solution"
                          ? "Solutions"
                          : t === "reasoning"
                            ? "Reasoning"
                            : "Digit candidates"}
                      </button>
                    ))}
                  </div>
                  <div className="result-body" aria-live="polite">
                    {resultContext && (
                      <div className="assumption-scope" role="status">
                        <strong>{resultContext.label}</strong>
                        <p>
                          All solutions, impossibility results, and uniqueness
                          conclusions below apply only under this temporary
                          assumption—not to the original puzzle.
                        </p>
                      </div>
                    )}
                    {busy ? (
                      <div className="empty-state">
                        <div className="orbit spinning">∴</div>
                        <h3>
                          {job.state === "queued"
                            ? "Queued"
                            : "Searching…"}
                        </h3>
                        <p>
                          {(job.elapsed || 0).toFixed(1)}s · {spec.backend}
                        </p>
                      </div>
                    ) : job?.state === "cancelled" ? (
                      <div className="empty-state">
                        <h3>Search cancelled</h3>
                      </div>
                    ) : result ? (
                      <>
                        {result.status && (
                          <div className={"result-status " + result.status}>
                            <span className="dot" />
                            {result.status === "satisfiable"
                              ? "Solution found"
                              : result.status === "unsatisfiable"
                                ? "Proven impossible"
                                : result.status === "incomplete"
                                  ? "Search incomplete"
                                  : result.status}
                            <span>{result.elapsed?.toFixed(3)}s</span>
                          </div>
                        )}
                        {!result.status && result.complete !== undefined && (
                          <div
                            className={
                              "result-status " +
                              (result.complete ? "satisfiable" : "incomplete")
                            }
                          >
                            <span className="dot" />
                            {result.complete
                              ? "Bounded experiment completed"
                              : "Experiment incomplete"}
                          </div>
                        )}
                        {result.message && (
                          <p className="result-message">{result.message}</p>
                        )}
                        {tab === "solution" && (
                          <>
                            {solution ? (
                              <>
                                <div className="solution-heading">
                                  <span>
                                    ASSIGNMENT {index + 1} OF{" "}
                                    {result.solutions!.length}
                                  </span>
                                  <div>
                                    <button
                                      aria-label="Previous solution"
                                      disabled={index === 0}
                                      onClick={() => setIndex(index - 1)}
                                    >
                                      ←
                                    </button>
                                    <button
                                      aria-label="Next solution"
                                      disabled={
                                        index === result.solutions!.length - 1
                                      }
                                      onClick={() => setIndex(index + 1)}
                                    >
                                      →
                                    </button>
                                  </div>
                                </div>
                                {solution.detail?.rows.length ? (
                                  <>
                                    <div className="solved-layout">
                                      <div className="solved-layout-head">
                                        <span>ROW</span>
                                        <span>ORIGINAL</span>
                                        <span>COMPLETED</span>
                                      </div>
                                      {solution.detail.rows.map((row, i) => (
                                        <div
                                          className="solved-layout-row"
                                          key={i}
                                        >
                                          <span>{row.label}</span>
                                          <code>{row.original}</code>
                                          <strong>{row.solved}</strong>
                                        </div>
                                      ))}
                                    </div>
                                    <details>
                                      <summary>Compiled equations</summary>
                                      <pre className="artifact-preview">
                                        {solution.rendered.join("\n")}
                                      </pre>
                                    </details>
                                  </>
                                ) : (
                                  <div className="solved-equations">
                                    {solution.rendered.map((line, i) => (
                                      <div key={i}>{line}</div>
                                    ))}
                                  </div>
                                )}
                                <div className="mapping-grid">
                                  {Object.entries(solution.assignment).map(
                                    ([letter, digit]) => (
                                      <div
                                        key={letter}
                                        className={
                                          index > 0 &&
                                          result.solutions![index - 1]
                                            .assignment[letter] !== digit
                                            ? "changed"
                                            : ""
                                        }
                                      >
                                        <span>{letter}</span>
                                        <strong>{digit}</strong>
                                      </div>
                                    ),
                                  )}
                                </div>
                                {!!solution.detail?.columns.length && (
                                  <details className="arithmetic-details">
                                    <summary>Inspect carries & borrows</summary>
                                    {solution.detail.columns.map(
                                      (column, i) => (
                                        <p className="help" key={i}>
                                          <strong>
                                            {column.stage} · column{" "}
                                            {column.column + 1}
                                          </strong>
                                          <br />
                                          {column.text}
                                        </p>
                                      ),
                                    )}
                                  </details>
                                )}
                                <div className="proof-note">
                                  {result.unique === true
                                    ? "✓ Uniqueness proved: exactly one assignment."
                                    : result.unique === false
                                      ? "Multiple distinct assignments exist."
                                      : result.complete
                                        ? "Search completed."
                                        : "This answer does not establish uniqueness."}
                                </div>
                                <button
                                  className="secondary full"
                                  onClick={() =>
                                    run(
                                      "solve",
                                      {
                                        ...(resultContext?.spec || spec),
                                        mode: "unique",
                                      },
                                      resultContext?.label,
                                    )
                                  }
                                  disabled={!!busy}
                                >
                                  Check uniqueness
                                </button>
                              </>
                            ) : null}
                            {result.spec && (
                              <div className="generated">
                                <h3>Generated puzzle</h3>
                                <pre>{result.spec.equations.join("\n")}</pre>
                                <p>
                                  Verification:{" "}
                                  {JSON.stringify(result.verification)}
                                </p>
                                <button
                                  className="primary"
                                  onClick={() =>
                                    load({
                                      id: crypto.randomUUID(),
                                      title: "Generated exploration · " + seed,
                                      tags: ["Generated"],
                                      notes: "Seed " + seed,
                                      spec: result.spec!,
                                    })
                                  }
                                >
                                  Open in workbench →
                                </button>
                              </div>
                            )}
                            {result.rows && (
                              <>
                                <div className="table-wrap">
                                  <table>
                                    <thead>
                                      <tr>
                                        {Object.keys(result.rows[0] || {}).map(
                                          (k) => (
                                            <th key={k}>{k}</th>
                                          ),
                                        )}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {result.rows.map((row, i) => (
                                        <tr key={i}>
                                          {Object.values(row).map((v, j) => (
                                            <td key={j}>
                                              {typeof v === "object"
                                                ? JSON.stringify(v)
                                                : String(v)}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                                <button
                                  className="secondary"
                                  onClick={() =>
                                    download(
                                      "cryptarithm-experiment.json",
                                      result,
                                    )
                                  }
                                >
                                  Export experiment
                                </button>
                              </>
                            )}
                            {result.identities !== undefined && (
                              <details>
                                <summary>Exact identities</summary>
                                <pre className="artifact-preview">
                                  {JSON.stringify(result.identities, null, 2)}
                                </pre>
                              </details>
                            )}
                            {result.certificate !== undefined && (
                              <div className="certificate-card">
                                <button
                                  className="secondary"
                                  onClick={() =>
                                    download(
                                      "cryptarithm-certificate.json",
                                      result.certificate,
                                    )
                                  }
                                >
                                  Download certificate JSON
                                </button>
                              </div>
                            )}
                          </>
                        )}
                        {tab === "reasoning" && (
                          <>
                            {result.hints?.slice(0, hintCount).map((h, i) => (
                              <article className="deduction" key={i}>
                                <span>{h.kind || "verified"}</span>
                                <h4>{h.rule}</h4>
                                <p>{h.text}</p>
                              </article>
                            ))}
                            {result.steps && (
                              <details>
                                <summary>
                                  Replay elementary deductions (
                                  {result.steps.length})
                                </summary>
                                {result.steps.map((step, i) => (
                                  <article className="deduction" key={i}>
                                    <span>
                                      {step.source} · {step.rule}
                                    </span>
                                    <p>{step.text}</p>
                                    <details>
                                      <summary>
                                        Premises & domain change
                                      </summary>
                                      <pre className="artifact-preview">
                                        {JSON.stringify(
                                          {
                                            premises: step.premises,
                                            variable: step.variable,
                                            removed: step.removed,
                                            remaining: step.remaining,
                                          },
                                          null,
                                          2,
                                        )}
                                      </pre>
                                    </details>
                                  </article>
                                ))}
                              </details>
                            )}
                            {result.domains && (
                              <details>
                                <summary>
                                  Remaining digit domains
                                  {result.solved
                                    ? " · all fixed"
                                    : result.contradiction
                                      ? " · contradiction"
                                      : ""}
                                </summary>
                                <pre className="artifact-preview">
                                  {JSON.stringify(result.domains, null, 2)}
                                </pre>
                              </details>
                            )}
                            {result.hints &&
                              hintCount < result.hints.length && (
                                <button
                                  className="secondary"
                                  onClick={() => setHintCount(hintCount + 1)}
                                >
                                  Reveal next deduction
                                </button>
                              )}
                            <button
                              className="secondary full"
                              disabled={!!busy}
                              onClick={() => run("hint")}
                            >
                              Find verified deductions
                            </button>
                            <label className="assumption-label">
                              Try an assumption
                              <div className="input-action">
                                <input
                                  aria-label="Assumption"
                                  placeholder="e.g. S=9"
                                  value={assumption}
                                  onChange={(e) =>
                                    setAssumption(e.target.value)
                                  }
                                />
                                <button
                                  onClick={() => {
                                    const m = assumption.match(
                                      /^\s*([A-Za-z])\s*=\s*(\d+)\s*$/,
                                    );
                                    if (!m) {
                                      setError(
                                        "Use a single assumption such as S=9.",
                                      );
                                      return;
                                    }
                                    run(
                                      "solve",
                                      {
                                        ...spec,
                                        assignments: {
                                          ...spec.assignments,
                                          [m[1].toUpperCase()]: Number(m[2]),
                                        },
                                      },
                                      `Under assumption ${m[1].toUpperCase()}=${Number(m[2])}`,
                                    );
                                  }}
                                >
                                  Test
                                </button>
                              </div>
                            </label>
                            <p className="help">
                              This temporary assumption does not change your
                              saved puzzle.
                            </p>
                          </>
                        )}
                        {tab === "candidates" && (
                          <>
                            <h3 className="section-title">
                              What could each digit be?
                            </h3>
                            <p className="help">
                              Possible values have a witness. Excluded values
                              are proved impossible. Unknown values need more
                              search.
                            </p>
                            {result.candidates &&
                              Object.entries(result.candidates).map(
                                ([letter, c]) => (
                                  <div className="candidate-row" key={letter}>
                                    <strong>{letter}</strong>
                                    <div>
                                      {Array.from(
                                        { length: spec.base },
                                        (_, i) => (
                                          <span
                                            title={
                                              c.possible.includes(i)
                                                ? "Witness found"
                                                : c.excluded.includes(i)
                                                  ? "Proved impossible"
                                                  : "Not resolved"
                                            }
                                            className={
                                              c.possible.includes(i)
                                                ? "possible"
                                                : c.excluded.includes(i)
                                                  ? "excluded"
                                                  : "unknown"
                                            }
                                            key={i}
                                          >
                                            {i}
                                          </span>
                                        ),
                                      )}
                                    </div>
                                  </div>
                                ),
                              )}
                            <button
                              className="secondary full"
                              disabled={!!busy}
                              onClick={() => run("candidates")}
                            >
                              Analyze digit candidates
                            </button>
                          </>
                        )}
                      </>
                    ) : (
                      <p className="empty-state">No results.</p>
                    )}
                  </div>
                </section>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
function rowLabel(layout: Layout, i: number) {
  const n = layout.rows.length;
  if (layout.kind === "addition")
    return i === n - 1 ? "Sum" : "Addend " + (i + 1);
  if (layout.kind === "subtraction")
    return ["Minuend", "Subtrahend", "Difference"][i] || "Row";
  if (layout.kind === "multiplication")
    return i === 0
      ? "Multiplicand"
      : i === 1
        ? "Multiplier"
        : i === n - 1
          ? "Product"
          : "Partial " + (i - 1);
  if (layout.kind === "root")
    return (
      ["Root", "Radicand", "Remainder", "Initial square"][i] ||
      (i % 2 === 0 ? "Current " + (i - 2) / 2 : "Product " + (i - 3) / 2)
    );
  return (
    ["Dividend", "Divisor", "Quotient", "Remainder"][i] ||
    (i % 2 === 0 ? "Product " + (i - 2) / 2 : "Difference " + (i - 3) / 2)
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
