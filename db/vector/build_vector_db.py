import os
import time
from multiprocessing import get_context
from queue import Empty
from typing import Any, Dict, List, Optional

import typer

from db.neo4j.neo4j_handler import count_nodes, stream_nodes, close
from .helper.embedder import embed_batch
from .helper.text_builder import build_text
from .milvus_store import init_milvus

try:
    import tqdm as tqdm_module

    tqdm = tqdm_module.tqdm
except ImportError:

    class tqdm:
        def __init__(self, iterable=None, total=None, desc="", unit=""):
            self.iterable = iterable
            self.total = total
            self.desc = desc
            self.unit = unit
            self.n = 0

        def update(self, n=1):
            self.n += n
            if self.desc:
                print(f"{self.desc}: {self.n}{self.unit}", end="\r")

        def close(self):
            print()

        def __iter__(self):
            if self.iterable:
                for item in self.iterable:
                    self.update(1)
                    yield item
                self.close()
            else:
                return iter([])


# Process orchestration
MP_CONTEXT = get_context("spawn")
IMPORT_SENTINEL = "__IMPORT_DONE__"
TRANSFORM_SENTINEL = "__TRANSFORM_DONE__"

# Milvus VARCHAR field limit for text storage
MAX_TEXT_LENGTH = 2000
TRUNCATION_SUFFIX = "..."

# Configuration from Env
IMPORT_BATCH_SIZE = int(os.getenv("VECTOR_BUILD_IMPORT_BATCH", "100"))
INSERT_BATCH_SIZE = int(os.getenv("VECTOR_BUILD_INSERT_BATCH", "500"))

_worker_env_value = os.getenv("VECTOR_BUILD_WORKERS")
try:
    WORKERS: Optional[int] = int(_worker_env_value) if _worker_env_value else None
except ValueError:
    WORKERS = None

try:
    WORKER_PERCENT = float(os.getenv("VECTOR_BUILD_WORKER_PERCENT", "0.75"))
except ValueError:
    WORKER_PERCENT = 0.75

if WORKER_PERCENT <= 0:
    WORKER_PERCENT = 0.75
elif WORKER_PERCENT > 1:
    WORKER_PERCENT = 1.0

try:
    _cpu_cap_value = int(os.getenv("VECTOR_BUILD_MAX_CORES", "8"))
    WORKER_CPU_CAP: Optional[int] = _cpu_cap_value if _cpu_cap_value > 0 else None
except ValueError:
    WORKER_CPU_CAP = 8

QUEUE_MULTIPLIER = max(2, int(os.getenv("VECTOR_BUILD_QUEUE_MULTIPLIER", "4")))
ESTIMATE_SECONDS_PER_NODE = float(
    os.getenv("VECTOR_BUILD_ESTIMATE_SECONDS_PER_NODE", "0.05")
)
SAMPLE_PERCENT = float(os.getenv("VECTOR_BUILD_SAMPLE_PERCENT", "1.0"))
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
TEST_SAMPLE_PERCENT = float(os.getenv("TEST_SAMPLE_PERCENT", "1.0"))
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"


def _effective_sample_percent() -> float:
    """Return effective sampling percent, clamped to [0, 100].

    Priority:
    - If TEST_MODE is enabled, process all available nodes (100%).
    - Otherwise, use SAMPLE_PERCENT from env.
    """
    if TEST_MODE:
        percent = 100.0
    else:
        percent = SAMPLE_PERCENT
    return max(0.0, min(percent, 100.0))


def truncate_text(
    text: str, max_length: int = MAX_TEXT_LENGTH, suffix: str = TRUNCATION_SUFFIX
) -> str:
    if len(text) > max_length:
        return text[: max_length - len(suffix)] + suffix
    return text


def process_node_batch(nodes: List[Dict[str, Any]], label: str):
    """Process a batch of nodes: build text, truncate, and embed."""
    texts: List[str] = []
    valid_nodes: List[Dict[str, Any]] = []

    for node in nodes:
        try:
            text = build_text(node)
            text = truncate_text(text)
            texts.append(text)
            valid_nodes.append(node)
        except Exception as exc:
            print(f"Error building text for node {node.get('id')}: {exc}")

    if not valid_nodes:
        return [], [], [], []

    try:
        # Embed in smaller chunks to avoid timeouts
        chunk_size = 5
        all_vectors = []
        for i in range(0, len(texts), chunk_size):
            chunk_texts = texts[i:i + chunk_size]
            chunk_vectors = embed_batch(chunk_texts)
            if len(chunk_vectors) != len(chunk_texts):
                print(f"Mismatch in embedding count for {label} chunk. Expected {len(chunk_texts)}, got {len(chunk_vectors)}.")
                return [], [], [], []
            all_vectors.extend(chunk_vectors)
        
        vectors = all_vectors

        if len(vectors) != len(valid_nodes):
            print(
                f"Mismatch in embedding count for {label}. Expected {len(valid_nodes)}, got {len(vectors)}."
            )
            return [], [], [], []

        ids = [n["id"] for n in valid_nodes]
        node_labels = [label] * len(valid_nodes)

        return ids, vectors, texts, node_labels

    except Exception as exc:
        print(f"Error embedding batch for {label}: {exc}")
        return [], [], [], []


def populate(labels: List[str]):
    """Populate the Milvus vector database with staged multiprocessing."""
    sample_percent = _effective_sample_percent()

    if TEST_MODE:
        typer.secho("!!! TEST MODE ENABLED !!!", fg=typer.colors.YELLOW, bold=True)
    typer.secho(
        f"Using {sample_percent:.2f}% sampling per label.",
        fg=typer.colors.BLUE,
    )

    label_stats = _gather_label_stats(labels, sample_percent)
    if not label_stats:
        typer.secho("No valid labels specified.", fg=typer.colors.YELLOW)
        return

    _print_label_stats(label_stats, sample_percent)

    worker_count = _prompt_worker_count(WORKERS)
    queue_size = max(worker_count * QUEUE_MULTIPLIER, worker_count * 2)

    for stats in label_stats:
        label = stats["label"]
        target = stats["selected"]

        if target == 0:
            typer.secho(
                f"Skipping {label}: no nodes within sampling.",
                fg=typer.colors.YELLOW,
            )
            continue

        eta_seconds = _estimate_duration(target, worker_count)
        typer.secho(
            f"Processing {label}: {target} nodes (~{_format_duration(eta_seconds)})",
            fg=typer.colors.BLUE,
        )

        _run_pipeline_for_label(
            label=label,
            sample_percent=sample_percent,
            worker_count=worker_count,
            expected_total=target,
            queue_size=queue_size,
        )

    typer.secho("\nVector DB build completed.", fg=typer.colors.GREEN, bold=True)


def _gather_label_stats(labels: List[str], sample_percent: float):
    stats = []
    for label in labels:
        total = count_nodes(label)
        selected = count_nodes(label, sample_percent=sample_percent)
        stats.append({"label": label, "total": total, "selected": selected})
    return stats


def _print_label_stats(stats: List[Dict[str, int]], sample_percent: float) -> None:
    typer.secho("\nNode summary by label:", fg=typer.colors.CYAN, bold=True)
    for entry in stats:
        label = entry["label"]
        total = entry["total"]
        selected = entry["selected"]
        typer.echo(
            f"- {label}: total={total:,} | to process={selected:,} ({sample_percent:.2f}%)"
        )


def _prompt_worker_count(default_workers: Optional[int]) -> int:
    raw_cpus = os.cpu_count() or 1
    cpu_cap = WORKER_CPU_CAP if isinstance(WORKER_CPU_CAP, int) else raw_cpus
    available_cpus = min(raw_cpus, cpu_cap)

    percent_target = int(round(available_cpus * WORKER_PERCENT))
    percent_target = max(1, min(percent_target, available_cpus))

    if default_workers is not None and default_workers > 0:
        suggested = max(1, min(default_workers, available_cpus))
    else:
        suggested = percent_target

    typer.echo(
        (
            f"Detected {raw_cpus} cores (usable {available_cpus}). "
            f"Defaulting to {suggested} workers (~{int(WORKER_PERCENT * 100)}% load)."
        )
    )

    use_all = typer.confirm(
        f"Do you want to use all cores ({available_cpus})?", default=False
    )
    if use_all:
        return available_cpus
    workers = typer.prompt(
        "How many cores do you want to use?",
        default=suggested,
        type=int,
    )
    return max(1, min(workers, available_cpus))


def _estimate_duration(node_count: int, worker_count: int) -> float:
    workers = max(1, worker_count)
    return node_count * ESTIMATE_SECONDS_PER_NODE / workers


def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "<1s"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _run_pipeline_for_label(
    label: str,
    sample_percent: float,
    worker_count: int,
    expected_total: int,
    queue_size: int,
) -> None:
    typer.secho(
        f"\n--- Processing label: {label} ---", fg=typer.colors.BRIGHT_BLUE, bold=True
    )

    ctx = MP_CONTEXT
    import_queue = ctx.Queue(maxsize=queue_size)
    transform_queue = ctx.Queue(maxsize=queue_size)
    status_queue = ctx.Queue()
    result_queue = ctx.Queue()

    importer = ctx.Process(
        target=_importer_worker,
        name=f"importer-{label}",
        args=(
            label,
            sample_percent,
            IMPORT_BATCH_SIZE,
            worker_count,
            import_queue,
            status_queue,
        ),
    )
    transformers = [
        ctx.Process(
            target=_transform_worker,
            name=f"transform-{label}-{idx}",
            args=(label, import_queue, transform_queue, status_queue),
        )
        for idx in range(worker_count)
    ]
    writer = ctx.Process(
        target=_writer_worker,
        name=f"writer-{label}",
        args=(
            label,
            transform_queue,
            INSERT_BATCH_SIZE,
            worker_count,
            status_queue,
            result_queue,
        ),
    )

    processes = [importer, writer, *transformers]

    for process in processes:
        process.start()

    pbar = tqdm(total=expected_total, desc=f"Importing {label}", unit="nodes")
    start_time = time.time()

    try:
        _monitor_status(processes, status_queue, pbar)
    except (Exception, KeyboardInterrupt) as exc:
        _terminate_processes(processes)
        raise RuntimeError(f"Error during {label} pipeline: {exc}") from exc
    finally:
        pbar.close()

    for process in processes:
        process.join()
        if process.exitcode not in (0, None):
            _terminate_processes(processes)
            raise RuntimeError(f"{process.name} finished with code {process.exitcode}")

    total_inserted = _read_result(result_queue)
    elapsed = time.time() - start_time
    rate = total_inserted / elapsed if elapsed > 0 else 0
    typer.secho(
        f"{label}: {total_inserted} nodes inserted ({rate:.2f} nodes/sec).",
        fg=typer.colors.GREEN,
    )


def _monitor_status(processes, status_queue, pbar):
    while True:
        alive = any(p.is_alive() for p in processes)
        try:
            message = status_queue.get(timeout=0.5)
        except Empty:
            if not alive:
                break
            continue

        if isinstance(message, int):
            pbar.update(message)
        elif isinstance(message, dict) and "error" in message:
            raise RuntimeError(message["error"])
        elif message == "DONE":
            continue


def _terminate_processes(processes):
    for process in processes:
        if process.is_alive():
            process.terminate()
    for process in processes:
        process.join(timeout=1)


def _read_result(result_queue):
    try:
        result = result_queue.get(timeout=5)
    except Empty:
        return 0

    if isinstance(result, dict):
        if "error" in result:
            raise RuntimeError(result["error"])
        return int(result.get("total", 0))
    if isinstance(result, int):
        return result
    return 0


def _importer_worker(
    label: str,
    sample_percent: float,
    import_batch_size: int,
    transform_workers: int,
    output_queue,
    status_queue,
):
    try:
        batch: List[Dict[str, Any]] = []
        for node in stream_nodes(
            label, batch=import_batch_size * 2, sample_percent=sample_percent
        ):
            batch.append(node)
            if len(batch) >= import_batch_size:
                output_queue.put(batch)
                status_queue.put(len(batch))
                batch = []
        if batch:
            output_queue.put(batch)
            status_queue.put(len(batch))
    except Exception as exc:  # noqa: BLE001
        status_queue.put({"error": f"Importer error for {label}: {exc}"})
        raise
    finally:
        close()
        for _ in range(transform_workers):
            output_queue.put(IMPORT_SENTINEL)
        status_queue.put("DONE")


def _transform_worker(label: str, input_queue, output_queue, status_queue):
    try:
        while True:
            batch = input_queue.get()
            if batch == IMPORT_SENTINEL:
                output_queue.put(TRANSFORM_SENTINEL)
                break
            ids, vectors, texts, lbls = process_node_batch(batch, label)
            if ids:
                output_queue.put((ids, vectors, texts, lbls))
    except Exception as exc:  # noqa: BLE001
        status_queue.put({"error": f"Transform error for {label}: {exc}"})
        raise
    finally:
        close()


def _writer_worker(
    label: str,
    input_queue,
    insert_batch_size: int,
    transformer_workers: int,
    status_queue,
    result_queue,
):
    try:
        collection = init_milvus()
        buffer = {"ids": [], "vectors": [], "texts": [], "labels": []}
        total_inserted = 0
        completed = 0

        while completed < transformer_workers:
            try:
                item = input_queue.get(timeout=60)
            except Empty:
                # If no message for 60 seconds, assume stuck and break
                print(f"Writer timeout waiting for transform workers, flushing remaining buffer")
                break
            if item == TRANSFORM_SENTINEL:
                completed += 1
                continue

            ids, vectors, texts, labels = item
            buffer["ids"].extend(ids)
            buffer["vectors"].extend(vectors)
            buffer["texts"].extend(texts)
            buffer["labels"].extend(labels)

            if len(buffer["ids"]) >= insert_batch_size:
                _flush_buffer(collection, buffer)
                total_inserted += len(buffer["ids"])
                buffer = {"ids": [], "vectors": [], "texts": [], "labels": []}

        if buffer["ids"]:
            _flush_buffer(collection, buffer)
            total_inserted += len(buffer["ids"])

        result_queue.put({"total": total_inserted})
    except Exception as exc:
        status_queue.put({"error": f"Writer error for {label}: {exc}"})
        result_queue.put({"error": str(exc)})
        raise


def _flush_buffer(collection, buffer):
    """Insert buffered data into Milvus."""
    try:
        collection.insert(
            [buffer["ids"], buffer["vectors"], buffer["texts"], buffer["labels"]]
        )
    except Exception as exc:
        print(f"Error inserting to Milvus: {exc}")
