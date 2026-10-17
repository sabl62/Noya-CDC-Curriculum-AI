import React, { useState, useEffect, useRef, useId } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import mermaid from "mermaid";
import { Check } from "lucide-react";

mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "strict", suppressErrorRendering: true });

// Map of language identifiers to display names
const languageNames = {
  bash: "Bash",
  shell: "Shell",
  sh: "Shell",
  python: "Python",
  py: "Python",
  javascript: "JavaScript",
  js: "JavaScript",
  html: "HTML",
  css: "CSS",
  json: "JSON",
  sql: "SQL",
  java: "Java",
  cpp: "C++",
  c: "C",
  go: "Go",
  rust: "Rust",
  typescript: "TypeScript",
  ts: "TypeScript",
  xml: "XML",
  yaml: "YAML",
  yml: "YAML",
  markdown: "Markdown",
  md: "Markdown",
  mermaid: "Mermaid",
  venn: "Venn Diagram",
  "noya-graph": "Graph Data",
  "noya-activity": "Learning Activity",
  "noya-geometry": "Geometry Diagram",
};

const getLanguageName = (lang) => {
  if (!lang) return null;
  return languageNames[lang.toLowerCase()] || lang;
};

// Mermaid diagram renderer
const MermaidDiagram = ({ code }) => {
  const ref = useRef(null);
  const [rendered, setRendered] = useState(false);
  const [error, setError] = useState(false);
  const isMindMap = /^\s*mindmap\b/i.test(code || "");

  useEffect(() => {
    if (!code || !ref.current) return undefined;
    let active = true;
    setRendered(false);
    setError(false);
    const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const target = ref.current;
    try {
      // Mermaid only owns this empty child; drawing into document.body can
      // briefly add a second scrollbar, while drawing into the React wrapper
      // can conflict with React's child reconciliation.
      mermaid.render(id, code.trim(), target).then(({ svg }) => {
        if (!active) return;
        target.innerHTML = svg;
        setRendered(true);
      }).catch(() => {
        if (active) setError(true);
      });
    } catch {
      setError(true);
    }

    return () => {
      active = false;
      target.replaceChildren();
    };
  }, [code]);

  if (error) {
    return (
      <div className="my-3 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] p-3 text-[13px] text-[var(--ink-soft)]">
        This diagram couldn’t be rendered. Ask Noya to redraw it.
      </div>
    );
  }

  return (
    <div className={`mermaid-diagram my-3 flex justify-center overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border)] bg-white p-4${isMindMap ? " is-mindmap" : ""}`}>
      <div ref={ref} className="mermaid-svg-host" aria-busy={!rendered} />
      {!rendered && <div className="text-[13px] text-[var(--ink-faint)]">Loading diagram...</div>}
    </div>
  );
};

// Venn diagram parser - tracks whether values have %
const parseVennData = (code) => {
  const lines = code.trim().split("\n");
  const data = { sets: [], regions: {}, hasPercent: false };
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("sets:")) {
      data.sets = trimmed.replace("sets:", "").split(",").map((s) => s.trim());
    } else if (trimmed.includes(":")) {
      const [key, val] = trimmed.split(":").map((s) => s.trim());
      if (val.includes("%")) data.hasPercent = true;
      data.regions[key] = parseFloat(val) || 0;
    }
  }
  return data.sets.length >= 2 ? data : null;
};

// Venn diagram renderer - works with ANY set names
const VennDiagram = ({ code }) => {
  const data = parseVennData(code);
  if (!data) {
    return (
      <div className="my-3 rounded-[var(--radius-sm)] border border-red-300 bg-red-50 p-3 text-[13px] text-red-700">
        Invalid Venn diagram format.
      </div>
    );
  }

  const { sets, regions, hasPercent } = data;
  const n = sets.length;
  const W = 440, H = 360;
  const cx = W / 2, cy = H / 2 + 15;
  const R = 95, spread = 50;

  const angles = n === 3
    ? [Math.PI / 2, Math.PI / 2 + (2 * Math.PI) / 3, Math.PI / 2 + (4 * Math.PI) / 3]
    : n === 2 ? [Math.PI, 0] : [0];

  const centers = angles.map((a) => ({
    x: cx + spread * Math.cos(a),
    y: cy - spread * Math.sin(a),
  }));

  // Compute label positions relative to circle centers
  const pos = {};
  if (n === 3) {
    const [s0, s1, s2] = sets;
    // Only regions: push outward from each circle center toward the non-overlapping edge
    pos[s0] = { x: centers[0].x - 30, y: centers[0].y - 35 };
    pos[s1] = { x: centers[1].x + 30, y: centers[1].y - 35 };
    pos[s2] = { x: centers[2].x, y: centers[2].y + 40 };
    // Pairwise intersections: midpoint between two circle centers
    pos[s0 + "_" + s1] = { x: (centers[0].x + centers[1].x) / 2, y: (centers[0].y + centers[1].y) / 2 - 12 };
    pos[s1 + "_" + s2] = { x: (centers[1].x + centers[2].x) / 2 + 12, y: (centers[1].y + centers[2].y) / 2 + 8 };
    pos[s0 + "_" + s2] = { x: (centers[0].x + centers[2].x) / 2 - 12, y: (centers[0].y + centers[2].y) / 2 + 8 };
    // Triple intersection: exact center
    pos[s0 + "_" + s1 + "_" + s2] = { x: cx, y: cy };
  } else if (n === 2) {
    const [s0, s1] = sets;
    pos[s0] = { x: centers[0].x - 25, y: centers[0].y };
    pos[s1] = { x: centers[1].x + 25, y: centers[1].y };
    pos[s0 + "_" + s1] = { x: cx, y: cy };
  } else {
    pos[sets[0]] = { x: cx, y: cy };
  }

  const norm = (key) => {
    const v = regions[key];
    return v !== undefined ? parseFloat(v) || 0 : undefined;
  };

  const regionLabels = {};
  if (n === 3) {
    const [s0, s1, s2] = sets;
    regionLabels[s0] = norm(s0 + "_only") ?? norm(s0) ?? 0;
    regionLabels[s1] = norm(s1 + "_only") ?? norm(s1) ?? 0;
    regionLabels[s2] = norm(s2 + "_only") ?? norm(s2) ?? 0;
    regionLabels[s0 + "_" + s1] = norm(s0 + "_" + s1) ?? 0;
    regionLabels[s1 + "_" + s2] = norm(s1 + "_" + s2) ?? 0;
    regionLabels[s0 + "_" + s2] = norm(s0 + "_" + s2) ?? 0;
    regionLabels[s0 + "_" + s1 + "_" + s2] = norm(s0 + "_" + s1 + "_" + s2) ?? 0;
  } else if (n === 2) {
    const [s0, s1] = sets;
    regionLabels[s0] = norm(s0 + "_only") ?? norm(s0) ?? 0;
    regionLabels[s1] = norm(s1 + "_only") ?? norm(s1) ?? 0;
    regionLabels[s0 + "_" + s1] = norm(s0 + "_" + s1) ?? 0;
  } else {
    regionLabels[sets[0]] = norm(sets[0]) ?? norm(sets[0] + "_only") ?? 0;
  }

  const colors = ["#4A90D9", "#E67E22", "#27AE60"];
  const formatVal = (v) => hasPercent ? v + "%" : String(v);

  return (
    <div className="my-3 flex justify-center overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border)] bg-white p-4">
      <svg width={W} height={H} viewBox={"0 0 " + W + " " + H}>
        <rect x="0" y="0" width={W} height={H} fill="#fafafa" rx="8" />
        {centers.map((c, i) => (
          <circle key={i} cx={c.x} cy={c.y} r={R}
            fill={colors[i % colors.length]} fillOpacity="0.15"
            stroke={colors[i % colors.length]} strokeWidth="2" />
        ))}
        {n === 3 && centers.map((c, i) => {
          var dy = i < 2 ? -R - 14 : R + 24;
          return (
            <text key={"lbl-" + i} x={c.x} y={c.y + dy}
              textAnchor="middle" fontSize="14" fontWeight="bold" fill={colors[i]}>
              {sets[i]}
            </text>
          );
        })}
        {Object.entries(pos).map(([key, coordinate]) => {
          var value = regionLabels[key];
          if (value === undefined || value === null || !coordinate) return null;
          return (
            <text key={key} x={coordinate.x} y={coordinate.y}
              textAnchor="middle" fontSize="14" fontWeight="600" fill="#333">
              {formatVal(value)}
            </text>
          );
        })}
      </svg>
    </div>
  );
};

// Code block with language header
const NoyaGraph = ({ code }) => {
  let chart;
  try {
    chart = JSON.parse(code);
  } catch {
    return <div className="noya-visual-error">This graph could not be displayed.</div>;
  }
  const pointIsValid = (point) => Number.isFinite(Number(point?.x))
    && Number.isFinite(Number(point?.y))
    && Math.abs(Number(point.x)) <= 1e12
    && Math.abs(Number(point.y)) <= 1e12;
  const palette = { blue: "#3b82f6", red: "#ef4444", green: "#15803d", orange: "#ea580c", purple: "#7c3aed" };
  const rawSeries = Array.isArray(chart?.series)
    ? chart.series.slice(0, 6)
    : [{ name: chart?.seriesName || chart?.yLabel || "Value", points: chart?.points, color: "green" }];
  const series = rawSeries
    .filter((item) => item && Array.isArray(item.points))
    .map((item, index) => ({
      name: typeof item.name === "string" ? item.name.slice(0, 80) : `Series ${index + 1}`,
      color: palette[String(item.color || "").toLowerCase()] || ["#15803d", "#3b82f6", "#ef4444", "#ea580c", "#7c3aed", "#0f766e"][index],
      points: item.points.filter(pointIsValid).slice(0, 40).map((point) => ({ x: Number(point.x), y: Number(point.y) })).sort((left, right) => left.x - right.x),
    }))
    .filter((item) => item.points.length >= 2);
  const values = series.flatMap((item) => item.points);
  if (!values.length) return <div className="noya-visual-error">This graph needs at least two data points per line.</div>;

  const width = 620;
  const height = 300;
  // Reserve room for both the rotated y-axis title and its tick labels.
  const plot = { left: 90, top: 20, right: 20, bottom: 54 };
  const xMin = Math.min(...values.map((point) => point.x));
  const xMax = Math.max(...values.map((point) => point.x));
  const rawYMin = Math.min(...values.map((point) => point.y));
  const rawYMax = Math.max(...values.map((point) => point.y));
  const yPadding = rawYMin === rawYMax ? Math.max(1, Math.abs(rawYMin) * 0.15) : (rawYMax - rawYMin) * 0.12;
  const yMin = rawYMin - yPadding;
  const yMax = rawYMax + yPadding;
  const plotWidth = width - plot.left - plot.right;
  const plotHeight = height - plot.top - plot.bottom;
  const x = (value) => plot.left + ((value - xMin) / (xMax - xMin || 1)) * plotWidth;
  const y = (value) => plot.top + ((yMax - value) / (yMax - yMin || 1)) * plotHeight;
  const ticks = Array.from({ length: 4 }, (_, index) => {
    const fraction = index / 3;
    return {
      x: xMin + (xMax - xMin) * fraction,
      y: yMin + (yMax - yMin) * fraction,
    };
  });
  const format = (value) => Number(value.toPrecision(3)).toString();

  return (
    <figure className="noya-graph">
      <figcaption>{String(chart.title || "Graph")}</figcaption>
      <div className="noya-graph-scroll">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${String(chart.title || "Graph")}: ${String(chart.xLabel || "x")} versus ${String(chart.yLabel || "y")}`}>
          {ticks.map((tick, index) => (
            <g key={`grid-${index}`}>
              <line x1={plot.left} x2={width - plot.right} y1={y(tick.y)} y2={y(tick.y)} className="noya-graph-grid" />
              <text x={plot.left - 10} y={y(tick.y) + 4} textAnchor="end" className="noya-graph-tick">{format(tick.y)}</text>
              <text x={x(tick.x)} y={height - plot.bottom + 19} textAnchor="middle" className="noya-graph-tick">{format(tick.x)}</text>
            </g>
          ))}
          <line x1={plot.left} x2={width - plot.right} y1={height - plot.bottom} y2={height - plot.bottom} className="noya-graph-axis" />
          <line x1={plot.left} x2={plot.left} y1={plot.top} y2={height - plot.bottom} className="noya-graph-axis" />
          {series.map((line, seriesIndex) => {
            const path = line.points.map((point, index) => `${index ? "L" : "M"}${x(point.x)},${y(point.y)}`).join(" ");
            return (
              <g key={`series-${seriesIndex}`}>
                <path d={path} className="noya-graph-line" style={{ stroke: line.color }} />
                {line.points.map((point, pointIndex) => <circle key={`point-${pointIndex}`} cx={x(point.x)} cy={y(point.y)} r="4" className="noya-graph-point" style={{ stroke: line.color }} />)}
              </g>
            );
          })}
          <text x={plot.left + plotWidth / 2} y={height - 8} textAnchor="middle" className="noya-graph-label">{String(chart.xLabel || "x")}</text>
          <text transform={`translate(15 ${plot.top + plotHeight / 2}) rotate(-90)`} textAnchor="middle" className="noya-graph-label">{String(chart.yLabel || "y")}</text>
        </svg>
      </div>
      {series.length > 1 && (
        <ul className="noya-graph-legend" aria-label="Graph series">
          {series.map((line, index) => <li key={`legend-${index}`}><span style={{ backgroundColor: line.color }} />{line.name}</li>)}
        </ul>
      )}
    </figure>
  );
};

const isRightTriangleDiagram = (code) =>
  /right[- ]angled triangle|right triangle/i.test(code)
  && /vertex\s*a\b/i.test(code)
  && /vertex\s*b\b/i.test(code)
  && /vertex\s*c\b/i.test(code)
  && /midpoint[\s\S]{0,80}hypotenuse\s*ac/i.test(code);

const RightTriangleDiagram = ({ title = "Right triangle ABC" }) => (
  <figure className="noya-geometry">
    <figcaption>{title}</figcaption>
    <svg viewBox="0 0 640 380" role="img" aria-label="Right triangle ABC with a right angle at B and midpoint D on hypotenuse AC">
      <line x1="150" y1="66" x2="150" y2="292" className="noya-geometry-side" />
      <line x1="150" y1="292" x2="492" y2="292" className="noya-geometry-side" />
      <line x1="150" y1="66" x2="492" y2="292" className="noya-geometry-hypotenuse" />
      <line x1="306" y1="177" x2="313" y2="165" className="noya-geometry-midpoint-mark" />
      <line x1="330" y1="193" x2="336" y2="181" className="noya-geometry-midpoint-mark" />
      <line x1="150" y1="292" x2="321" y2="179" className="noya-geometry-median" />
      <path d="M150 264 H178 V292" className="noya-geometry-angle" />
      <circle cx="150" cy="66" r="5" className="noya-geometry-point" />
      <circle cx="150" cy="292" r="5" className="noya-geometry-point" />
      <circle cx="492" cy="292" r="5" className="noya-geometry-point" />
      <circle cx="321" cy="179" r="6" className="noya-geometry-midpoint" />
      <text x="126" y="58" textAnchor="end" className="noya-geometry-label">A</text>
      <text x="126" y="316" textAnchor="end" className="noya-geometry-label">B</text>
      <text x="507" y="316" className="noya-geometry-label">C</text>
      <text x="331" y="169" className="noya-geometry-label">D</text>
      <text x="166" y="322" className="noya-geometry-note">90°</text>
      <text x="368" y="202" transform="rotate(33.5 368 202)" textAnchor="middle" className="noya-geometry-note">Hypotenuse AC</text>
      <text x="222" y="242" transform="rotate(-33.5 222 242)" textAnchor="middle" className="noya-geometry-note">Median BD</text>
    </svg>
    <p>D is the midpoint of hypotenuse AC, and BD is the median.</p>
  </figure>
);

const NoyaGeometry = ({ code }) => {
  let geometry;
  try {
    geometry = JSON.parse(code);
  } catch {
    return <div className="noya-visual-error">This geometry diagram could not be displayed.</div>;
  }
  if (geometry?.type !== "right-triangle" || geometry?.rightAngleAt !== "B" || geometry?.hypotenuse !== "AC") {
    return <div className="noya-visual-error">This geometry diagram could not be displayed.</div>;
  }
  const title = typeof geometry.title === "string" ? geometry.title.slice(0, 100) : "Right triangle ABC";
  return <RightTriangleDiagram title={title} />;
};

const inlineMarkdownComponents = { p: ({ children }) => <>{children}</> };

const MathText = ({ children }) => (
  <ReactMarkdown
    remarkPlugins={[remarkMath]}
    rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]}
    components={inlineMarkdownComponents}
  >
    {String(children ?? "")}
  </ReactMarkdown>
);

const NoyaActivity = ({ code }) => {
  let activity;
  try {
    activity = JSON.parse(code);
  } catch {
    return <div className="noya-visual-error">This activity could not be displayed.</div>;
  }
  const isChoice = activity?.type === "choice"
    && Array.isArray(activity.options)
    && activity.options.length >= 2
    && activity.options.length <= 5
    && activity.options.every((option) => typeof option === "string" && option.length <= 200)
    && Number.isInteger(activity.answer)
    && activity.answer >= 0
    && activity.answer < activity.options.length;
  const isNumber = activity?.type === "number" && Number.isFinite(Number(activity.answer));
  if ((!isChoice && !isNumber) || typeof activity.prompt !== "string" || !activity.prompt || activity.prompt.length > 500) return <div className="noya-visual-error">This activity could not be displayed.</div>;

  return <ActivityCard key={code} activity={activity} isChoice={isChoice} />;
};

const ActivityCard = ({ activity, isChoice }) => {
  const activityId = useId();
  const [selection, setSelection] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const isNumber = activity.type === "number";
  const answer = Number(activity.answer);
  const numericCorrect = !isChoice && selection.trim() !== "" && Math.abs(Number(selection) - answer) <= Math.max(0, Number(activity.tolerance) || 0);
  const correct = isChoice ? Number(selection) === answer : numericCorrect;
  const canSubmit = isChoice ? selection !== "" : selection.trim() !== "" && Number.isFinite(Number(selection));

  return (
    <section className="noya-activity" aria-labelledby={activityId}>
      <div className="noya-activity-heading">
        <h3 id={activityId}><MathText>{typeof activity.title === "string" ? activity.title : "Check your understanding"}</MathText></h3>
        <span>Quick check</span>
      </div>
      <p><MathText>{activity.prompt}</MathText></p>
      {isChoice ? (
        <div className="noya-activity-options" role="group" aria-label="Answer options">
          {activity.options.map((option, index) => (
            <button key={`${index}-${option}`} type="button" className={`noya-activity-option${selection === index ? " selected" : ""}`} aria-pressed={selection === index} disabled={submitted} onClick={() => setSelection(index)}>
              <span className="noya-activity-option-letter">{String.fromCharCode(65 + index)}</span>
              <span className="noya-activity-option-text"><MathText>{option}</MathText></span>
            </button>
          ))}
        </div>
      ) : (
        <label className="noya-activity-number-label">
          <span>Your answer{typeof activity.unit === "string" && activity.unit ? ` (${activity.unit})` : ""}</span>
          <input type="number" inputMode="decimal" value={selection} disabled={submitted} onChange={(event) => setSelection(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && canSubmit && !submitted) { event.preventDefault(); setSubmitted(true); } }} />
        </label>
      )}
      {!submitted ? (
        <button type="button" className="noya-activity-submit" disabled={!canSubmit} onClick={() => setSubmitted(true)}>Check answer</button>
      ) : (
        <div className={`noya-activity-feedback${correct ? " correct" : " incorrect"}`} role="status">
          <strong>
            {correct && <Check size={15} aria-hidden="true" />}
            {correct ? "Correct" : <>Answer: {isChoice ? <MathText>{activity.options[answer]}</MathText> : `${activity.answer}${typeof activity.unit === "string" && activity.unit ? ` ${activity.unit}` : ""}`}</>}
          </strong>
          {activity.explanation && <span><MathText>{activity.explanation}</MathText></span>}
        </div>
      )}
    </section>
  );
};

// Code blocks can opt into the Pro-only, safe visual formats.
const CodeBlock = ({ children, className, richContent }) => {
  const match = /language-([\w-]+)/.exec(className || "");
  const language = match ? match[1] : null;
  const displayName = getLanguageName(language);
  const code = String(children ?? "").replace(/\n$/, "");

  if (language === "mermaid") {
    if (richContent && isRightTriangleDiagram(code)) return <RightTriangleDiagram />;
    return richContent ? <MermaidDiagram code={code} /> : <pre className="my-3 overflow-x-auto rounded-[var(--radius-sm)] bg-[var(--surface)] p-3 text-sm"><code>{code}</code></pre>;
  }

  if (language === "venn") {
    return richContent ? <VennDiagram code={code} /> : <pre className="my-3 overflow-x-auto rounded-[var(--radius-sm)] bg-[var(--surface)] p-3 text-sm"><code>{code}</code></pre>;
  }

  if (language === "noya-graph") {
    return richContent ? <NoyaGraph code={code} /> : <pre className="my-3 overflow-x-auto rounded-[var(--radius-sm)] bg-[var(--surface)] p-3 text-sm"><code>{code}</code></pre>;
  }

  if (language === "noya-geometry") {
    return richContent ? <NoyaGeometry code={code} /> : <pre className="my-3 overflow-x-auto rounded-[var(--radius-sm)] bg-[var(--surface)] p-3 text-sm"><code>{code}</code></pre>;
  }

  if (language === "noya-activity") {
    return richContent ? <NoyaActivity code={code} /> : <pre className="my-3 overflow-x-auto rounded-[var(--radius-sm)] bg-[var(--surface)] p-3 text-sm"><code>{code}</code></pre>;
  }

  if (language === "noya" && richContent) {
    try {
      const visual = JSON.parse(code);
      if ((visual?.type === "choice" || visual?.type === "number") && visual?.prompt) {
        return <NoyaActivity code={code} />;
      }
      if (visual?.type === "right-triangle") {
        return <NoyaGeometry code={code} />;
      }
      if (Array.isArray(visual?.points) || Array.isArray(visual?.series)) {
        return <NoyaGraph code={code} />;
      }
    } catch {
      // Keep unrecognized `noya` blocks readable as ordinary code below.
    }
  }

  return (
    <div className="my-3 overflow-hidden rounded-[var(--radius-sm)] border border-[var(--border-strong)]">
      {displayName && (
        <div className="flex items-center justify-between bg-[var(--ink)] px-3 py-1.5 font-[var(--font-mono)] text-[12px] font-semibold text-[var(--bg)]">
          <span>{displayName}</span>
        </div>
      )}
      <pre className="overflow-x-auto bg-[var(--ink)] px-4 py-3 font-[var(--font-mono)] text-[13px] leading-relaxed text-[var(--bg)]">
        <code className={className}>{children}</code>
      </pre>
    </div>
  );
};

// Inline code
const InlineCode = ({ children }) => (
  <code className="rounded-[4px] bg-[var(--pine-tint)] px-[6px] py-[2px] font-[var(--font-mono)] text-[0.875em] font-medium text-[var(--pine-strong)]">
    {children}
  </code>
);

// Headings — left-border accent encodes hierarchy depth
const headingStyles = {
  1: "text-[22px] font-bold border-l-[3px] border-[var(--pine)] pl-3 mt-6 mb-2.5 leading-snug",
  2: "text-[19px] font-bold border-l-[3px] border-[var(--brass)] pl-3 mt-5 mb-2 leading-snug",
  3: "text-[16px] font-semibold mt-4 mb-1.5 leading-snug",
  4: "text-[15px] font-semibold mt-3 mb-1 leading-snug",
};

const Heading = ({ level, children }) => {
  const className = headingStyles[level] || headingStyles[4];
  const Tag = `h${level}`;
  const text = Array.isArray(children) ? children.join("") : String(children ?? "");
  const id = text.toLowerCase().replace(/[^\w]+/g, "-") || undefined;

  return (
    <Tag id={id} className={`${className} text-[var(--ink)] scroll-mt-20`}>
      {children}
    </Tag>
  );
};

// Hard-word tooltip: a tap/click-and-focus-friendly glossary mark,
// not a hover-only affordance (works for touch and keyboard).
const HardWord = ({ children, meaning, simple, example }) => {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        onBlur={() => setOpen(false)}
        aria-expanded={open}
        className="marginalia cursor-help border-b border-dashed border-[var(--brass)] text-[1em] not-italic font-semibold text-[var(--brass)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brass)]/40"
      >
        {children}
      </button>
      {open && (
        <span
          role="tooltip"
          className="animate-fade-in absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-[var(--radius-sm)] border border-[var(--border-strong)] bg-[var(--surface-raised)] p-3 text-left text-[12.5px] font-normal not-italic text-[var(--ink-soft)] shadow-[0_8px_24px_rgba(0,0,0,0.16)]"
        >
          <span className="mb-1.5 block border-b border-[var(--border)] pb-1.5 font-[var(--font-body)] text-[13px] font-bold text-[var(--ink)]">
            {children}
          </span>
          {meaning && (
            <span className="mb-1.5 block">
              <span className="mb-0.5 block font-semibold text-[var(--pine)]">Meaning</span>
              {meaning}
            </span>
          )}
          {simple && (
            <span className="mb-1.5 block">
              <span className="mb-0.5 block font-semibold text-[var(--brass)]">Simple version</span>
              {simple}
            </span>
          )}
          {example && (
            <span className="block italic">
              <span className="mb-0.5 block font-semibold text-[var(--ink-faint)] not-italic">Example</span>
              {example}
            </span>
          )}
        </span>
      )}
    </span>
  );
};

const MarkdownLink = ({ href, children }) => {
  if (href?.startsWith("hardword://")) {
    try {
      const details = decodeURIComponent(href.replace("hardword://", ""));
      const [meaning = "", simple = "", example = ""] = details.split("|").map((p) => p.trim());
      return (
        <HardWord meaning={meaning} simple={simple} example={example}>
          {children}
        </HardWord>
      );
    } catch {
      // fall through to a plain link if parsing fails
    }
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-[var(--pine)] underline underline-offset-2 hover:text-[var(--pine-strong)]"
    >
      {children}
    </a>
  );
};

const List = ({ ordered, children }) => {
  const Component = ordered ? "ol" : "ul";
  return (
    <Component className={`my-1.5 ml-1 flex flex-col gap-1 pl-5 ${ordered ? "list-decimal" : "list-disc"}`}>
      {children}
    </Component>
  );
};

const ListItem = ({ children }) => <li className="pl-0.5 leading-[1.7]">{children}</li>;

const Blockquote = ({ children }) => (
  <blockquote className="my-3 rounded-r-[var(--radius-sm)] border-l-[3px] border-[var(--brass)] bg-[var(--brass-tint)] px-4 py-2.5 leading-relaxed text-[var(--ink-soft)]">
    {children}
  </blockquote>
);

const Table = ({ children }) => (
  <div className="my-3 overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border)]">
    <table className="w-full border-collapse text-[14px] tabular">{children}</table>
  </div>
);

const TableHead = ({ children }) => <thead className="bg-[var(--pine-tint)] font-semibold">{children}</thead>;
const TableBody = ({ children }) => <tbody>{children}</tbody>;
const TableRow = ({ children }) => <tr className="border-b border-[var(--border)] last:border-0">{children}</tr>;
const TableHeader = ({ children }) => <th className="px-3.5 py-2.5 text-left font-semibold text-[var(--ink)]">{children}</th>;
const TableCell = ({ children }) => <td className="px-3.5 py-2 text-[var(--ink-soft)]">{children}</td>;

const HorizontalRule = () => <hr className="my-4 border-t border-[var(--border)]" />;

// Parse the compact pipe-table syntax used by the assistant into standard
// Markdown table nodes, without pulling in a second Markdown parser.
const remarkPipeTables = () => (tree) => {
  const parseCells = (line) => {
    const trimmed = line.trim();
    if (!trimmed.includes("|")) return null;

    const cells = [];
    let cell = "";
    for (let index = 0; index < trimmed.length; index += 1) {
      const character = trimmed[index];
      if (character === "\\" && trimmed[index + 1] === "|") {
        cell += "|";
        index += 1;
      } else if (character === "|") {
        cells.push(cell.trim());
        cell = "";
      } else {
        cell += character;
      }
    }
    cells.push(cell.trim());

    if (trimmed.startsWith("|")) cells.shift();
    if (trimmed.endsWith("|") && !trimmed.endsWith("\\|")) cells.pop();
    return cells;
  };

  const parseInline = (value) => {
    const children = [];
    const tokenPattern = /(\$[^$\n]+\$|\*\*[^*\n]+\*\*|`[^`\n]+`|\*[^*\n]+\*)/g;
    let previousIndex = 0;

    for (const match of value.matchAll(tokenPattern)) {
      if (match.index > previousIndex) children.push({ type: "text", value: value.slice(previousIndex, match.index) });
      const token = match[0];
      if (token.startsWith("$")) {
        const value = token.slice(1, -1);
        children.push({
          type: "inlineMath",
          value,
          // remark-math normally adds this data while parsing. These table
          // nodes are built manually, so provide the same HAST representation
          // for rehype-katex to render them inside cells.
          data: {
            hName: "code",
            hProperties: { className: ["language-math", "math-inline"] },
            hChildren: [{ type: "text", value }],
          },
        });
      }
      else if (token.startsWith("**")) children.push({ type: "strong", children: parseInline(token.slice(2, -2)) });
      else if (token.startsWith("`")) children.push({ type: "inlineCode", value: token.slice(1, -1) });
      else children.push({ type: "emphasis", children: parseInline(token.slice(1, -1)) });
      previousIndex = match.index + token.length;
    }

    if (previousIndex < value.length) children.push({ type: "text", value: value.slice(previousIndex) });
    return children.length ? children : [{ type: "text", value: "" }];
  };
  const cellNode = (value) => ({ type: "tableCell", children: parseInline(value) });
  const rowNode = (cells) => ({ type: "tableRow", children: cells.map(cellNode) });
  const serializeInline = (node) => {
    if (node.type === "text") return node.value;
    if (node.type === "inlineMath") return `$${node.value}$`;
    if (node.type === "inlineCode") return `\`${node.value}\``;
    if (node.type === "strong") return `**${node.children.map(serializeInline).join("")}**`;
    if (node.type === "emphasis") return `*${node.children.map(serializeInline).join("")}*`;
    if (node.type === "delete") return `~~${node.children.map(serializeInline).join("")}~~`;
    return null;
  };

  const transform = (parent) => {
    if (!parent.children) return;

    const nextChildren = [];
    for (const node of parent.children) {
      transform(node);
      if (node.type !== "paragraph" || !node.children?.length) {
        nextChildren.push(node);
        continue;
      }

      const paragraphText = node.children.map(serializeInline);
      if (paragraphText.some((part) => part === null)) {
        nextChildren.push(node);
        continue;
      }
      const lines = paragraphText.join("").split("\n");
      let start = 0;
      let cursor = 0;
      while (cursor < lines.length - 1) {
        const headers = parseCells(lines[cursor]);
        const separators = parseCells(lines[cursor + 1]);
        if (!headers?.length || headers.length !== separators?.length || !separators.every((cell) => /^:?-{1,}:?$/.test(cell))) {
          cursor += 1;
          continue;
        }

        if (cursor > start) {
          nextChildren.push({ type: "paragraph", children: [{ type: "text", value: lines.slice(start, cursor).join("\n") }] });
        }

        const rows = [rowNode(headers)];
        cursor += 2;
        while (cursor < lines.length) {
          const cells = parseCells(lines[cursor]);
          if (!cells || cells.length !== headers.length) break;
          rows.push(rowNode(cells));
          cursor += 1;
        }
        nextChildren.push({ type: "table", align: headers.map(() => null), children: rows });
        start = cursor;
      }

      if (start === 0) {
        nextChildren.push(node);
      } else if (start < lines.length) {
        nextChildren.push({ type: "paragraph", children: [{ type: "text", value: lines.slice(start).join("\n") }] });
      }
    }
    parent.children = nextChildren;
  };

  transform(tree);
};

const normalizeContent = (content) => {
  if (!content) return "";

  let text = "";
  if (typeof content === "string") {
    const trimmed = content.trim();
    if (trimmed.startsWith("{")) {
      try {
        text = JSON.parse(trimmed).response || trimmed;
      } catch {
        text = content;
      }
    } else {
      text = content;
    }
  } else {
    text = content?.response || "";
  }

  let result = text
    .replace(/\\\[((?:.|\n)*?)\\\]/g, (_, equation) => {
      const cleaned = equation.trim().replace(/<sub>(.*?)<\/sub>/g, '_{$1}').replace(/<sup>(.*?)<\/sup>/g, '^{$1}');
      return `\n$$${cleaned}$$\n`;
    })
    .replace(/\\\(((?:.|\n)*?)\\\)/g, (_, equation) => {
      const cleaned = equation.trim().replace(/<sub>(.*?)<\/sub>/g, '_{$1}').replace(/<sup>(.*?)<\/sup>/g, '^{$1}');
      return `$${cleaned}$`;
    })
    .replace(/(\S+)/g, (token) => {
      if (/<sub>|<sup>/i.test(token)) {
        return `$${token.replace(/<sub>(.*?)<\/sub>/g, '_{$1}').replace(/<sup>(.*?)<\/sup>/g, '^{$1}')}$`;
      }
      return token;
    })
    .replace(/\[\[([^:]+):\s*(.*?)\]\]/g, (_, term, details) => {
      return `[${term.trim()}](hardword://${encodeURIComponent(details.trim())})`;
    });

  // Recover compact one-line tables from older model output that escaped
  // pipes and joined rows with "| |". Also repair two-column tables that
  // omit the required Markdown separator row. Leave fenced examples untouched.
  return result.split(/(```[\s\S]*?```)/g).map((block) => {
    if (block.startsWith("```")) return block;
    const lines = block.split("\n").map((line) => {
      if (!line.includes("\\|") || !/\|\s*:?-{1,}/.test(line.replace(/\\\|/g, "|"))) return line;
      return line.replace(/\\\|/g, "|").replace(/\|\s*\|/g, "|\n|");
    }).join("\n").split("\n").map((line) => {
      const trimmed = line.trim();
      if (!/^\\?\|/.test(trimmed)) return line;
      return trimmed
        .replace(/^\\(?=\|)/, "")
        .replace(/\\\s*$/, "");
    });

    const getCells = (line) => {
      const trimmed = line.trim();
      if (!trimmed.startsWith("|")) return null;
      const cells = [];
      let cell = "";
      for (let cellIndex = 0; cellIndex < trimmed.length; cellIndex += 1) {
        const character = trimmed[cellIndex];
        if (character === "\\" && trimmed[cellIndex + 1] === "|") {
          cell += "|";
          cellIndex += 1;
        } else if (character === "|") {
          cells.push(cell.trim());
          cell = "";
        } else {
          cell += character;
        }
      }
      cells.push(cell.trim());
      if (trimmed.startsWith("|")) cells.shift();
      if (trimmed.endsWith("|") && !trimmed.endsWith("\\|")) cells.pop();
      return cells;
    };
    const isSeparator = (cells) => cells?.length > 0 && cells.every((cell) => /^:?-{1,}:?$/.test(cell));
    const repaired = [];

    for (let index = 0; index < lines.length; index += 1) {
      const headerCells = getCells(lines[index]);
      const nextCells = getCells(lines[index + 1] || "");
      const previousCells = getCells(lines[index - 1] || "");
      if (
        headerCells?.length > 1 &&
        nextCells?.length === headerCells.length &&
        !previousCells &&
        !isSeparator(nextCells)
      ) {
        repaired.push(lines[index]);
        repaired.push(`| ${headerCells.map(() => "---").join(" | ")} |`);
      } else {
        repaired.push(lines[index]);
      }
    }

    return repaired.join("\n");
  }).join("");
};

const MarkdownRenderer = ({ content, className = "", onQuestionClick, richContent = false }) => {
  const sanitizedContent = normalizeContent(content);

  if (!sanitizedContent) return null;

  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkPipeTables, remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]}
        components={{
          // CodeBlock owns the complete code/visual presentation. Keeping
          // react-markdown's outer <pre> would add a dark frame around visuals.
          pre: ({ children }) => <>{children}</>,
          code: ({ className, children }) => {
            const isInline = !className;
            return isInline ? <InlineCode>{children}</InlineCode> : <CodeBlock className={className} richContent={richContent}>{children}</CodeBlock>;
          },
          strong: ({ children }) => <strong className="font-bold text-[var(--ink)]">{children}</strong>,
          h1: ({ children }) => <Heading level={1}>{children}</Heading>,
          h2: ({ children }) => <Heading level={2}>{children}</Heading>,
          h3: ({ children }) => <Heading level={3}>{children}</Heading>,
          h4: ({ children }) => <Heading level={4}>{children}</Heading>,
          h5: ({ children }) => <Heading level={4}>{children}</Heading>,
          h6: ({ children }) => <Heading level={4}>{children}</Heading>,
          a: ({ href, children }) => {
            if (href === "#ask") {
              const text = Array.isArray(children) ? children.join("") : children;
              return (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    onQuestionClick?.(text);
                  }}
                  className="inline-flex items-center gap-1.5 text-left font-medium text-[var(--pine)] transition-colors hover:text-[var(--pine-strong)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40"
                >
                  <ChevronTick /> <span>{children}</span>
                </button>
              );
            }
            return <MarkdownLink href={href}>{children}</MarkdownLink>;
          },
          ul: ({ children }) => <List ordered={false}>{children}</List>,
          ol: ({ children }) => <List ordered>{children}</List>,
          li: ListItem,
          blockquote: Blockquote,
          table: Table,
          thead: TableHead,
          tbody: TableBody,
          tr: TableRow,
          th: TableHeader,
          td: TableCell,
          hr: HorizontalRule,
          p: ({ children }) => <p className="mb-2.5 leading-[1.7] text-[var(--ink)] last:mb-0">{children}</p>,
        }}
      >
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  );
};

const ChevronTick = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="shrink-0">
    <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// ChatView updates scroll-related state frequently. Preserve the rendered
// Markdown subtree while its actual content and display mode stay unchanged,
// so stateful visuals like Mermaid diagrams are not torn down and restarted.
export default React.memo(MarkdownRenderer);
