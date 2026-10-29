import { Fragment, type ReactNode } from "react";

/**
 * Tiny, safe markdown for chatbot replies: ### headings, "- " bullets, **bold**, _italic_, [n] citations
 * and paragraphs. It builds React elements from plain text - no HTML is ever injected, so replies can
 * never execute markup.
 */
function inline(text: string, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|_[^_]+_|\[\d+\])/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    if (t.startsWith("**")) out.push(<strong key={`${key}b${i++}`} className="font-semibold">{t.slice(2, -2)}</strong>);
    else if (t.startsWith("_")) out.push(<em key={`${key}i${i++}`} className="text-muted-foreground">{t.slice(1, -1)}</em>);
    else out.push(<sup key={`${key}c${i++}`} className="ml-0.5 text-[0.7em] font-medium text-primary">{t}</sup>);
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text, className }: { text: string; className?: string }) {
  const blocks = text.replace(/\r\n/g, "\n").split(/\n{2,}/);
  return (
    <div className={className}>
      {blocks.map((block, bi) => {
        const lines = block.split("\n").filter((l) => l.trim() !== "");
        if (!lines.length) return null;
        const nodes: ReactNode[] = [];
        let list: string[] = [];
        const flush = (k: string) => {
          if (list.length) {
            nodes.push(
              <ul key={k} className="my-1.5 list-disc space-y-1 pl-5 marker:text-muted-foreground">
                {list.map((li, i) => <li key={i}>{inline(li, `${k}-${i}`)}</li>)}
              </ul>,
            );
            list = [];
          }
        };
        lines.forEach((line, li) => {
          const k = `${bi}-${li}`;
          if (/^#{1,4}\s/.test(line)) {
            flush(`${k}l`);
            nodes.push(<p key={k} className="mt-2 text-sm font-semibold text-foreground first:mt-0">{inline(line.replace(/^#{1,4}\s/, ""), k)}</p>);
          } else if (/^\s*[-•*]\s+/.test(line)) {
            list.push(line.replace(/^\s*[-•*]\s+/, ""));
          } else {
            flush(`${k}l`);
            nodes.push(<p key={k}>{inline(line, k)}</p>);
          }
        });
        flush(`${bi}-end`);
        return <Fragment key={bi}><div className="space-y-1 [&+&]:mt-3">{nodes}</div></Fragment>;
      })}
    </div>
  );
}
