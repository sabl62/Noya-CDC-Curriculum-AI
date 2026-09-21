import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });

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
};

const getLanguageName = (lang) => {
  if (!lang) return null;
  return languageNames[lang.toLowerCase()] || lang;
};

// Mermaid diagram renderer
const MermaidDiagram = ({ code }) => {
  const ref = useRef(null);
  const [svg, setSvg] = useState("");
  const [error, setError] = useState(null);
  const renderedRef = useRef(false);

  useEffect(() => {
    if (!code || renderedRef.current) return;
    renderedRef.current = true;
    const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    try {
      mermaid.render(id, code.trim()).then(({ svg: rendered }) => {
        setSvg(rendered);
      }).catch((err) => {
        setError(err.message || "Failed to render diagram");
      });
    } catch (err) {
      setError(err.message || "Failed to render diagram");
    }
  }, [code]);

  if (error) {
    return (
      <div className="my-3 rounded-[var(--radius-sm)] border border-red-300 bg-red-50 p-3 text-[13px] text-red-700">
        Diagram error: {error}
      </div>
    );
  }

  return (
    <div ref={ref} className="my-3 flex justify-center overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border)] bg-white p-4">
      {svg ? (
        <div dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <div className="text-[13px] text-[var(--ink-faint)]">Loading diagram...</div>
      )}
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
const CodeBlock = ({ children, className }) => {
  const match = /language-(\w+)/.exec(className || "");
  const language = match ? match[1] : null;
  const displayName = getLanguageName(language);

  if (language === "mermaid") {
    return <MermaidDiagram code={children} />;
  }

  if (language === "venn") {
    return <VennDiagram code={children} />;
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

  return result;
};

const MarkdownRenderer = ({ content, className = "", onQuestionClick }) => {
  const sanitizedContent = normalizeContent(content);

  if (!sanitizedContent) return null;

  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]}
        components={{
          code: ({ className, children }) => {
            const isInline = !className;
            return isInline ? <InlineCode>{children}</InlineCode> : <CodeBlock className={className}>{children}</CodeBlock>;
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

export default MarkdownRenderer;
