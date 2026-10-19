"use client";

import { ArrowUp, MessageCircle, RotateCcw, Square, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { usePathname } from "next/navigation";
import { Fragment, useEffect, useRef, useState } from "react";

import { useApi } from "@/lib/api";
import { spring } from "@/lib/motion";
import { useStoredValue } from "@/lib/storage";
import { cn } from "../ui/cn";
import { Segmented } from "../ui/controls";
import { Spinner } from "../ui/feedback";

type Provider = "local" | "gemini";
type Providers = Record<Provider, { model: string; problem: string | null }> & { default: Provider };
type ToolUse = { name: string; args: Record<string, unknown> };
type Message = { role: "user" | "assistant"; content: string; tools?: ToolUse[]; error?: string; model?: string };

const TOOL_LABELS: Record<string, string> = {
  get_technicals: "Technicals",
  get_fundamentals: "Fundamentals",
  get_forecast: "Forecast models",
  get_news_sentiment: "News sentiment",
  get_portfolio: "Portfolio",
  get_past_assessments: "Past assessments",
};

const SUGGESTIONS = ["Summarize this page", "What stands out here?", "Explain the key numbers"];

/** What the model is told about the page: its route, title, symbol and visible text. */
function pageContext() {
  const params = new URLSearchParams(window.location.search);
  let symbol = params.get("symbol");
  try {
    symbol ??= localStorage.getItem("pd-symbol");
  } catch {
    /* storage blocked */
  }
  return {
    path: window.location.pathname,
    title: document.title.replace(/ · Portfolio$/, ""),
    symbol: symbol?.toUpperCase().slice(0, 20) || null,
    text: (document.getElementById("main")?.innerText ?? "").slice(0, 60_000),
  };
}

/* ── Minimal Markdown: paragraphs, lists, **bold**, *italic*, `code`. No HTML passes through. ── */
function inline(text: string) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2)
      return <code key={i} className="rounded bg-fill px-1 text-[0.92em]">{part.slice(1, -1)}</code>;
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) return <em key={i}>{part.slice(1, -1)}</em>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}

function Markdown({ text }: { text: string }) {
  const blocks: React.ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  const flush = () => {
    if (!list) return;
    const Tag = list.ordered ? "ol" : "ul";
    blocks.push(
      <Tag key={blocks.length} className={cn("space-y-1 pl-5", list.ordered ? "list-decimal" : "list-disc")}>
        {list.items.map((item, i) => <li key={i}>{inline(item)}</li>)}
      </Tag>,
    );
    list = null;
  };
  for (const line of text.split("\n")) {
    const item = line.match(/^\s*(?:([-*•])|(\d+)[.)])\s+(.*)$/);
    if (item) {
      const ordered = !item[1];
      if (list && list.ordered !== ordered) flush();
      list ??= { ordered, items: [] };
      list.items.push(item[3]);
      continue;
    }
    flush();
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    if (heading) blocks.push(<p key={blocks.length} className="font-semibold">{inline(heading[1])}</p>);
    else if (line.trim()) blocks.push(<p key={blocks.length}>{inline(line)}</p>);
  }
  flush();
  return <div className="space-y-2">{blocks}</div>;
}

function Bubble({ message, streaming }: { message: Message; streaming: boolean }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="squircle max-w-[85%] rounded-[18px] rounded-br-[6px] bg-tint px-3.5 py-2 text-callout whitespace-pre-wrap text-white">
          {message.content}
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-1.5">
      {message.tools && message.tools.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {message.tools.map((t, i) => (
            <span key={i} className="rounded-full bg-fill-2 px-2 py-0.5 text-caption text-label-2">
              {TOOL_LABELS[t.name] ?? t.name}
              {typeof t.args.symbol === "string" && ` · ${t.args.symbol}`}
            </span>
          ))}
        </div>
      )}
      {message.content && (
        <div className="text-callout text-label">
          <Markdown text={message.content} />
        </div>
      )}
      {streaming && !message.content && (
        <div className="flex items-center gap-2 text-footnote text-label-2">
          <Spinner className="size-4" />
          {message.tools?.length ? `Reading ${TOOL_LABELS[message.tools.at(-1)!.name] ?? "data"}…` : "Thinking…"}
        </div>
      )}
      {message.error && <div className="text-footnote text-negative">{message.error}</div>}
    </div>
  );
}

export function ChatLauncher() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [stored, setStored] = useStoredValue("pd-chat-provider");
  const provider: Provider = stored === "gemini" ? "gemini" : "local";
  const { data: providers } = useApi<Providers>(open ? "/chat/providers" : null);
  const abort = useRef<AbortController | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [messages]);

  useEffect(() => {
    if (!open) return;
    field.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const update = (fn: (m: Message) => Message) =>
    setMessages((cur) => [...cur.slice(0, -1), fn(cur[cur.length - 1])]);

  async function send(text: string) {
    text = text.trim();
    if (!text || busy) return;
    const history: Message[] = [...messages, { role: "user", content: text }];
    setMessages([...history, { role: "assistant", content: "", tools: [] }]);
    setInput("");
    setBusy(true);
    const controller = new AbortController();
    abort.current = controller;
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        credentials: "same-origin",
        signal: controller.signal,
        headers: { "X-Requested-With": "fetch", "Content-Type": "application/json" },
        body: JSON.stringify({
          provider,
          // Failed turns and empty replies aren't worth resending.
          messages: history.filter((m) => m.content).map(({ role, content }) => ({ role, content })),
          page: pageContext(),
        }),
      });
      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : `${res.status} ${res.statusText}`);
      }
      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += value;
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          if (event.type === "text") update((m) => ({ ...m, content: m.content + event.text }));
          else if (event.type === "tool") update((m) => ({ ...m, tools: [...(m.tools ?? []), { name: event.name, args: event.args }] }));
          else if (event.type === "error") update((m) => ({ ...m, error: event.message }));
          else if (event.type === "done") update((m) => ({ ...m, model: event.model }));
        }
      }
    } catch (e) {
      const stopped = e instanceof DOMException && e.name === "AbortError";
      update((m) => ({ ...m, error: stopped ? "Stopped." : e instanceof Error ? e.message : String(e) }));
    } finally {
      setBusy(false);
      abort.current = null;
    }
  }

  const problem = providers?.[provider].problem;
  const options = [
    { value: "local" as const, label: "Qwen" },
    { value: "gemini" as const, label: "Gemini" },
  ];

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.button
            key="launcher"
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.6, opacity: 0 }}
            whileTap={{ scale: 0.92 }}
            transition={spring.bouncy}
            onClick={() => setOpen(true)}
            aria-label="Ask about this page"
            title="Ask about this page"
            className="fixed right-4 bottom-[calc(68px+env(safe-area-inset-bottom))] z-40 flex size-13 cursor-pointer items-center justify-center rounded-full bg-tint text-white shadow-[var(--shadow-raised)] hover:brightness-110 lg:right-6 lg:bottom-6"
          >
            <MessageCircle className="size-6" strokeWidth={2} />
            {busy && <span className="absolute top-1 right-1 size-3 rounded-full bg-white ring-2 ring-tint" />}
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.section
            key="panel"
            role="dialog"
            aria-label="Chat"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.96 }}
            transition={spring.sheet}
            style={{ transformOrigin: "bottom right" }}
            className="squircle fixed inset-x-2 top-[max(8px,env(safe-area-inset-top))] bottom-[calc(60px+env(safe-area-inset-bottom))] z-40 flex flex-col overflow-hidden rounded-[22px] bg-elevated shadow-[var(--shadow-raised)] sm:inset-x-auto sm:top-auto sm:right-4 sm:h-[min(600px,calc(100dvh-140px))] sm:w-[400px] lg:right-6 lg:bottom-6"
          >
            <header className="hairline-b flex items-center gap-2 px-4 py-2.5">
              <div className="min-w-0 flex-1">
                <div className="text-headline">Assistant</div>
                <div className="truncate text-caption text-label-2">
                  {providers ? providers[provider].model : " "}
                </div>
              </div>
              <Segmented size="sm" label="Model" options={options} value={provider} onChange={setStored} />
              {messages.length > 0 && (
                <button
                  onClick={() => !busy && setMessages([])}
                  disabled={busy}
                  aria-label="New chat"
                  title="New chat"
                  className="flex size-9 cursor-pointer items-center justify-center rounded-full text-label-2 hover:bg-fill-2 hover:text-label disabled:opacity-40"
                >
                  <RotateCcw className="size-4" />
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                aria-label="Close chat"
                title="Close"
                className="flex size-9 cursor-pointer items-center justify-center rounded-full text-label-2 hover:bg-fill-2 hover:text-label"
              >
                <X className="size-[18px]" />
              </button>
            </header>

            <div ref={scroller} className="flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
              {messages.length === 0 ? (
                <div className="space-y-3 pt-2">
                  <p className="text-callout text-label-2">
                    Ask about what&apos;s on this page, or about any stock or your portfolio. It can look up technicals,
                    fundamentals, forecasts, news and past assessments when the page doesn&apos;t have the answer.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        onClick={() => send(s)}
                        className="cursor-pointer rounded-full bg-tint-fill px-3 py-1.5 text-footnote font-medium text-tint hover:brightness-95"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((m, i) => <Bubble key={i} message={m} streaming={busy && i === messages.length - 1} />)
              )}
            </div>

            {problem && (
              <div className="bg-warning-fill px-4 py-2 text-footnote text-warning">
                {problem}
                {provider === "local" && !providers?.gemini.problem && " Switch to Gemini, or start Ollama."}
              </div>
            )}

            <form
              className="hairline-t flex items-end gap-2 px-3 py-2.5"
              onSubmit={(e) => {
                e.preventDefault();
                send(input);
              }}
            >
              <textarea
                ref={field}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    send(input);
                  }
                }}
                rows={1}
                maxLength={8000}
                placeholder={`Ask about ${pathname === "/" ? "your overview" : "this page"}…`}
                aria-label="Message"
                className="squircle max-h-32 min-h-10 flex-1 resize-none rounded-[20px] bg-fill-2 px-3.5 py-2 text-callout outline-none [field-sizing:content] placeholder:text-label-3"
              />
              {busy ? (
                <button
                  type="button"
                  onClick={() => abort.current?.abort()}
                  aria-label="Stop"
                  title="Stop"
                  className="flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-full bg-fill text-label hover:bg-fill-strong"
                >
                  <Square className="size-3.5 fill-current" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  aria-label="Send"
                  title="Send"
                  className="flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-full bg-tint text-white hover:brightness-110 disabled:cursor-default disabled:opacity-40"
                >
                  <ArrowUp className="size-5" strokeWidth={2.4} />
                </button>
              )}
            </form>
          </motion.section>
        )}
      </AnimatePresence>
    </>
  );
}
