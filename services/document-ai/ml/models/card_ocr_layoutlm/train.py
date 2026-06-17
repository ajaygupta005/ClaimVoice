"""
Fine-tune microsoft/layoutlmv3-base for 25-class card OCR (NER).

Reads:   data/processed/synthetic_cards/  (labels.jsonl + PNG files)
Writes:  services/document-ai/artifacts/card_ocr/latest/
             config.json          ← id2label / label2id embedded
             model.safetensors   ← best-val-loss weights
             tokenizer.json      ← fast tokeniser
             tokenizer_config.json
             special_tokens_map.json
             preprocessor_config.json

These files are everything AutoModelForTokenClassification.from_pretrained()
and LayoutLMv3Processor.from_pretrained() need in the inference runner.

Run from the ml/ directory:
    python -m models.card_ocr_layoutlm.train
    python -m models.card_ocr_layoutlm.train training.epochs=2 training.batch_size=2
"""

from __future__ import annotations

import time
from pathlib import Path

import hydra
import mlflow
import torch
import torch.nn as nn
from models.card_ocr_layoutlm.dataset import LABEL_LIST, CardOCRDataset
from omegaconf import DictConfig, OmegaConf
from torch.utils.data import DataLoader
from transformers import AutoModelForTokenClassification, LayoutLMv3Processor

# ---------------------------------------------------------------------------
# Path resolution — anchored to __file__ so they survive `cd` changes
# ---------------------------------------------------------------------------
# train.py is at: ml/models/card_ocr_layoutlm/train.py
#   parents[0] = ml/models/card_ocr_layoutlm/
#   parents[1] = ml/models/
#   parents[2] = ml/
#   parents[3] = services/document-ai/
#   parents[4] = services/
#   parents[5] = ClaimVoice/  (repo root)

_SERVICE_ROOT = Path(__file__).parents[3]
_REPO_ROOT = Path(__file__).parents[5]

_DATA_DIR = _REPO_ROOT / "data" / "processed" / "synthetic_cards"
_ARTIFACT_DIR = _SERVICE_ROOT / "artifacts" / "card_ocr" / "latest"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _run_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    device: torch.device,
) -> tuple[float, float]:
    """One full pass over *loader*.

    Returns:
        (avg_loss_per_sample, token_accuracy)

    Token accuracy counts only non-ignored positions (active NER tokens).
    The model computes cross-entropy internally when ``labels`` is present in
    the batch, so we don't instantiate a separate criterion.
    """
    training = optimizer is not None
    model.train(training)

    total_loss = total_correct = total_active_tokens = 0

    ctx = torch.enable_grad() if training else torch.no_grad()
    with ctx:
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}

            if training:
                optimizer.zero_grad()

            outputs = model(**batch)
            loss = outputs.loss  # already averaged over active tokens

            if training:
                loss.backward()
                # Clip gradients — LayoutLMv3 can have spiky gradients early in
                # fine-tuning when the new classification head is random.
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            total_loss += loss.item() * batch["input_ids"].size(0)

            # Per-token accuracy, ignoring padding / special-token positions
            labels = batch["labels"]  # (B, L)
            preds = outputs.logits.argmax(dim=-1)  # (B, L)
            active = labels != -100
            total_correct += (preds[active] == labels[active]).sum().item()
            total_active_tokens += active.sum().item()

    n = len(loader.dataset)
    avg_loss = total_loss / n
    token_acc = total_correct / max(total_active_tokens, 1)
    return avg_loss, token_acc


def _save_checkpoint(
    model: AutoModelForTokenClassification,
    processor: LayoutLMv3Processor,
    artifact_dir: Path,
) -> None:
    """Persist a complete HuggingFace checkpoint (weights + config + tokeniser)."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    # safe_serialization=True → saves model.safetensors instead of pytorch_model.bin
    model.save_pretrained(str(artifact_dir), safe_serialization=True)
    processor.save_pretrained(str(artifact_dir))
    print(f"  ✓ checkpoint saved → {artifact_dir}")


# ---------------------------------------------------------------------------
# Hydra entry point
# ---------------------------------------------------------------------------


@hydra.main(
    version_base=None,
    config_path="../../configs",  # ml/models/card_ocr_layoutlm/ → ml/configs/
    config_name="train_card_ocr",
)
def main(cfg: DictConfig) -> None:
    device = _get_device()
    num_labels = len(LABEL_LIST)  # 25 — overrides whatever is in the YAML

    print("\n=== Card OCR Training (LayoutLMv3) ===")
    print(f"Device     : {device}")
    print(f"Model      : {cfg.model.name}")
    print(f"Num labels : {num_labels}  {LABEL_LIST[:4]} … {LABEL_LIST[-2:]}")
    print(f"Config:\n{OmegaConf.to_yaml(cfg)}")

    if not _DATA_DIR.exists():
        raise FileNotFoundError(
            f"Synthetic card data not found at '{_DATA_DIR}'. "
            "Run `python data/ingest/synthetic_cards.py` first."
        )

    # ── Processor ───────────────────────────────────────────────────────────
    print(f"Loading processor '{cfg.model.name}' …")
    processor = LayoutLMv3Processor.from_pretrained(
        cfg.model.name,
        apply_ocr=False,  # words + boxes come from labels.jsonl, not tesseract
    )

    # ── Datasets + loaders ──────────────────────────────────────────────────
    train_ds = CardOCRDataset(
        _DATA_DIR,
        processor,
        split="train",
        val_fraction=cfg.data.val_fraction,
        seed=cfg.data.seed,
        max_length=cfg.data.max_length,
    )
    val_ds = CardOCRDataset(
        _DATA_DIR,
        processor,
        split="val",
        val_fraction=cfg.data.val_fraction,
        seed=cfg.data.seed,
        max_length=cfg.data.max_length,
    )
    print(f"Train : {len(train_ds)} samples  |  Val : {len(val_ds)} samples\n")

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.training.batch_size,
        shuffle=True,
        num_workers=cfg.data.num_workers,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.training.batch_size,
        shuffle=False,
        num_workers=cfg.data.num_workers,
        pin_memory=(device.type == "cuda"),
    )

    # ── Model ───────────────────────────────────────────────────────────────
    # id2label / label2id are persisted in config.json so the inference runner
    # can call model.config.id2label without importing this training module.
    id2label = {i: lbl for i, lbl in enumerate(LABEL_LIST)}
    label2id = {lbl: i for i, lbl in enumerate(LABEL_LIST)}

    print(f"Loading model '{cfg.model.name}' with {num_labels} output labels …")
    model = AutoModelForTokenClassification.from_pretrained(
        cfg.model.name,
        num_labels=num_labels,
        id2label=id2label,
        label2id=label2id,
        # The pretrained head has 2 (or another) output units; we replace it
        # with a fresh linear layer sized to num_labels.
        ignore_mismatched_sizes=True,
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=cfg.training.lr,
        weight_decay=cfg.training.weight_decay,
    )
    # Cosine schedule decays LR smoothly to ~0 over all epochs.
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg.training.epochs)

    # ── MLflow run ──────────────────────────────────────────────────────────
    mlflow.set_experiment("card_ocr_layoutlmv3")

    flat_params: dict = {
        **{f"model.{k}": v for k, v in OmegaConf.to_container(cfg.model).items()},
        **{f"training.{k}": v for k, v in OmegaConf.to_container(cfg.training).items()},
        **{f"data.{k}": v for k, v in OmegaConf.to_container(cfg.data).items()},
        "device": str(device),
        "num_labels": num_labels,
        "train_samples": len(train_ds),
        "val_samples": len(val_ds),
    }

    with mlflow.start_run():
        mlflow.log_params(flat_params)

        best_val_loss = float("inf")
        epochs_no_improve = 0

        for epoch in range(1, cfg.training.epochs + 1):
            t0 = time.perf_counter()

            train_loss, train_acc = _run_epoch(model, train_loader, optimizer, device)
            val_loss, val_acc = _run_epoch(model, val_loader, None, device)
            scheduler.step()

            elapsed = time.perf_counter() - t0
            current_lr = optimizer.param_groups[0]["lr"]

            print(
                f"Epoch {epoch:02d}/{cfg.training.epochs}  "
                f"train_loss={train_loss:.4f}  train_acc={train_acc:.4f}  "
                f"val_loss={val_loss:.4f}  val_acc={val_acc:.4f}  "
                f"lr={current_lr:.2e}  ({elapsed:.1f}s)"
            )

            mlflow.log_metrics(
                {
                    "train_loss": train_loss,
                    "train_acc": train_acc,
                    "val_loss": val_loss,
                    "val_acc": val_acc,
                    "lr": current_lr,
                },
                step=epoch,
            )

            # Save checkpoint whenever val_loss improves.
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                epochs_no_improve = 0
                _save_checkpoint(model, processor, _ARTIFACT_DIR)
                mlflow.log_metric("best_val_loss", best_val_loss, step=epoch)
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= cfg.training.patience:
                print(
                    f"\nEarly stop: val_loss did not improve for "
                    f"{cfg.training.patience} consecutive epochs."
                )
                break

        # Attach the saved directory as an MLflow artifact.
        if _ARTIFACT_DIR.exists():
            mlflow.log_artifacts(str(_ARTIFACT_DIR), artifact_path="model")

        mlflow.log_metric("best_val_loss", best_val_loss)
        print(f"\nTraining complete.  Best val_loss = {best_val_loss:.4f}")
        print(f"Checkpoint : {_ARTIFACT_DIR}")


if __name__ == "__main__":
    main()
