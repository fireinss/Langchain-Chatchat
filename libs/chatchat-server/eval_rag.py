import argparse
import csv
import json
import statistics
import time
from pathlib import Path

import requests


def load_tests(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("testset must be a JSON array")
    for item in data:
        if "question" not in item:
            raise ValueError("each testset item needs a question field")
    return data


def call_kb_chat(base_url: str, question: str, kb_name: str, top_k: int,
                 score_threshold: float, fallback: bool, answer_mode: bool,
                 timeout: int):
    url = f"{base_url.rstrip('/')}/chat/kb_chat"
    payload = {
        "query": question,
        "mode": "local_kb",
        "kb_name": kb_name,
        "top_k": top_k,
        "score_threshold": score_threshold,
        "return_direct": not answer_mode,
        "stream": False,
        "fallback_to_search": fallback,
    }
    start = time.perf_counter()
    response = requests.post(url, json=payload, timeout=timeout)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if response.status_code != 200:
        return None, elapsed_ms, f"http {response.status_code}"

    body = response.json()
    if isinstance(body, str):
        body = json.loads(body)
    return body, elapsed_ms, None


def tokenize(text: str):
    return set(text.lower().replace(",", " ").replace(".", " ").replace("，", " ").replace("。", " ").split())


def hit_tokens(page_content: str, expected_tokens: list):
    tokens = tokenize(page_content or "")
    return any(tok.lower() in tokens for tok in expected_tokens)


def run_config(base_url, tests, kb_name, top_k, score_threshold, fallback,
               answer_mode, timeout):
    hits = 0
    latencies = []
    retrieved_counts = []
    for item in tests:
        body, elapsed_ms, error = call_kb_chat(
            base_url, item["question"], kb_name, top_k, score_threshold,
            fallback, answer_mode, timeout,
        )
        if error:
            continue
        expected = item.get("expected_tokens") or []
        if answer_mode:
            text = str(body.get("content") or "")
            hit = hit_tokens(text, expected) if expected else False
            retrieved = len(body.get("docs") or [])
        else:
            docs = body.get("docs") or []
            text = " ".join(str(d.get("page_content") or "") for d in docs)
            hit = hit_tokens(text, expected) if expected else False
            retrieved = len(docs)
        hits += int(hit)
        retrieved_counts.append(retrieved)
        latencies.append(elapsed_ms)

    total = len(latencies)
    return {
        "top_k": top_k,
        "score_threshold": score_threshold,
        "fallback": fallback,
        "mode": "answer" if answer_mode else "retrieval",
        "questions": total,
        "hit_rate": round(hits / total, 4) if total else None,
        "avg_latency_ms": round(statistics.mean(latencies), 1) if latencies else None,
        "p95_latency_ms": round(quantile(latencies, 0.95), 1) if latencies else None,
        "avg_retrieved": round(statistics.mean(retrieved_counts), 2) if retrieved_counts else None,
    }


def quantile(values, q):
    values = sorted(values)
    if not values:
        return 0.0
    index = max(0, min(len(values) - 1, int(round(q * (len(values) - 1)))))
    return values[index]


def main():
    parser = argparse.ArgumentParser(description="RAG retrieval/answer evaluation for kb_chat")
    parser.add_argument("--base-url", default="http://127.0.0.1:7861")
    parser.add_argument("--kb-name", default="samples")
    parser.add_argument("--tests", default="eval_samples.json")
    parser.add_argument("--top-k", default="3,5,10")
    parser.add_argument("--score-threshold", default="0.5")
    parser.add_argument("--fallback", action="store_true")
    parser.add_argument("--answer", action="store_true", help="evaluate LLM answers instead of retrieval")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--out", default="eval_report.csv")
    args = parser.parse_args()

    tests = load_tests(Path(args.tests))
    top_k_values = [int(x) for x in args.top_k.split(",") if x.strip()]
    threshold_values = [float(x) for x in args.score_threshold.split(",") if x.strip()]
    fallback_values = [False, True] if args.fallback else [False]

    rows = []
    for top_k in top_k_values:
        for threshold in threshold_values:
            for fallback in fallback_values:
                row = run_config(
                    args.base_url, tests, args.kb_name, top_k, threshold,
                    fallback, args.answer, args.timeout,
                )
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False))

    with open(args.out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"report written to {args.out}")


if __name__ == "__main__":
    main()