"""
Fine-tune ResNet-50 for 8-class insurance payor classification.

Reads:   data/processed/synthetic_cards/labels.jsonl  (+ PNGs)
Writes:  services/document-ai/artifacts/payor_classifier/latest/model.safetensors

Run from the ml/ directory:
    python -m models.payor_classifier_resnet.train
    python -m models.payor_classifier_resnet.train training.epochs=5 training.batch_size=16
"""

from __future__ import annotations

import time
from pathlib import Path

import hydra
import mlflow
import torch
import torch.nn as nn
from models.payor_classifier_resnet.dataset import SyntheticCardDataset
from omegaconf import DictConfig, OmegaConf
from safetensors.torch import save_file
from torch.utils.data import DataLoader
from torchvision.models import ResNet50_Weights, resnet50

# ---------------------------------------------------------------------------
# Path resolution — all anchored to __file__ so they survive `cd` changes
# ---------------------------------------------------------------------------

# train.py lives at: ml/models/payor_classifier_resnet/train.py
# parents[3] = services/document-ai/
# parents[5] = ClaimVoice/ (repo root)
_SERVICE_ROOT = Path(__file__).parents[3]
_REPO_ROOT = Path(__file__).parents[5]

_DATA_DIR = _REPO_ROOT / "data" / "processed" / "synthetic_cards"
_ARTIFACT_DIR = _SERVICE_ROOT / "artifacts" / "payor_classifier" / "latest"

# ---------------------------------------------------------------------------
# Device selection
# ---------------------------------------------------------------------------


def _get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# Model construction
# ---------------------------------------------------------------------------


def build_model(num_classes: int, pretrained: bool) -> nn.Module:
    """Return ResNet-50 with a fresh classification head sized to *num_classes*."""
    weights = ResNet50_Weights.DEFAULT if pretrained else None
    model = resnet50(weights=weights)
    # Replace the 1000-class ImageNet head with our 8-class head.
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


# ---------------------------------------------------------------------------
# Training and evaluation helpers
# ---------------------------------------------------------------------------


def _run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer | None,
    device: torch.device,
) -> tuple[float, float]:
    """Run one full pass over *loader*. Trains when *optimizer* is not None."""
    training = optimizer is not None
    model.train(training)

    total_loss = total_correct = total_samples = 0

    ctx = torch.enable_grad() if training else torch.no_grad()
    with ctx:
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)

            if training:
                optimizer.zero_grad()

            logits = model(images)
            loss = criterion(logits, labels)

            if training:
                loss.backward()
                optimizer.step()

            total_loss += loss.item() * images.size(0)
            total_correct += (logits.argmax(1) == labels).sum().item()
            total_samples += images.size(0)

    avg_loss = total_loss / total_samples
    avg_acc = total_correct / total_samples
    return avg_loss, avg_acc


# ---------------------------------------------------------------------------
# Checkpoint export
# ---------------------------------------------------------------------------


def save_checkpoint(model: nn.Module, artifact_dir: Path) -> None:
    """Save model weights as safetensors to *artifact_dir/model.safetensors*."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_path = artifact_dir / "model.safetensors"
    # Move state dict to CPU before serialising to avoid device-specific files.
    cpu_state = {k: v.cpu() for k, v in model.state_dict().items()}
    save_file(cpu_state, str(out_path))
    print(f"  ✓ checkpoint saved → {out_path}")


# ---------------------------------------------------------------------------
# Hydra entry point
# ---------------------------------------------------------------------------


@hydra.main(
    version_base=None,
    config_path="../../configs",  # ml/models/payor_classifier_resnet/ → ml/configs/
    config_name="train_payor_classifier",
)
def main(cfg: DictConfig) -> None:
    device = _get_device()
    print("\n=== Payor Classifier Training ===")
    print(f"Device : {device}")
    print(f"Config :\n{OmegaConf.to_yaml(cfg)}")

    # ── Data ────────────────────────────────────────────────────────────────
    if not _DATA_DIR.exists():
        raise FileNotFoundError(
            f"Synthetic card data not found at '{_DATA_DIR}'. "
            "Run `python data/ingest/synthetic_cards.py` first."
        )

    train_ds = SyntheticCardDataset(
        _DATA_DIR,
        split="train",
        val_fraction=cfg.data.val_fraction,
        seed=cfg.data.seed,
    )
    val_ds = SyntheticCardDataset(
        _DATA_DIR,
        split="val",
        val_fraction=cfg.data.val_fraction,
        seed=cfg.data.seed,
    )

    print(f"Train : {len(train_ds)} samples")
    print(f"Val   : {len(val_ds)} samples")
    print(f"Classes: {train_ds.class_names()}\n")

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
    model = build_model(
        num_classes=cfg.model.num_classes,
        pretrained=cfg.model.pretrained,
    ).to(device)

    criterion = nn.CrossEntropyLoss()

    if cfg.training.optimizer == "sgd":
        optimizer = torch.optim.SGD(
            model.parameters(),
            lr=cfg.training.lr,
            momentum=0.9,
            weight_decay=cfg.training.weight_decay,
        )
    else:
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=cfg.training.lr,
            weight_decay=cfg.training.weight_decay,
        )

    if cfg.training.lr_scheduler == "plateau":
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="max", patience=2, factor=0.5, verbose=True
        )
    else:
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg.training.epochs)

    # ── MLflow run ──────────────────────────────────────────────────────────
    mlflow.set_experiment("payor_classifier")

    flat_params = {
        **{f"model.{k}": v for k, v in OmegaConf.to_container(cfg.model).items()},
        **{f"training.{k}": v for k, v in OmegaConf.to_container(cfg.training).items()},
        **{f"data.{k}": v for k, v in OmegaConf.to_container(cfg.data).items()},
        "device": str(device),
        "train_samples": len(train_ds),
        "val_samples": len(val_ds),
    }

    with mlflow.start_run():
        mlflow.log_params(flat_params)

        best_val_acc = 0.0
        epochs_without_improvement = 0

        for epoch in range(1, cfg.training.epochs + 1):
            t0 = time.perf_counter()

            train_loss, train_acc = _run_epoch(model, train_loader, criterion, optimizer, device)
            val_loss, val_acc = _run_epoch(model, val_loader, criterion, None, device)

            # Step scheduler
            if cfg.training.lr_scheduler == "plateau":
                scheduler.step(val_acc)
            else:
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

            # Save best checkpoint
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                epochs_without_improvement = 0
                save_checkpoint(model, _ARTIFACT_DIR)
                mlflow.log_metric("best_val_acc", best_val_acc, step=epoch)
            else:
                epochs_without_improvement += 1

            # Early stopping
            if epochs_without_improvement >= cfg.training.patience:
                print(f"\nEarly stop: no improvement for {cfg.training.patience} epochs.")
                break

        # Log the saved weights file as an MLflow artifact too
        weights_path = _ARTIFACT_DIR / "model.safetensors"
        if weights_path.exists():
            mlflow.log_artifact(str(weights_path), artifact_path="model")

        mlflow.log_metric("best_val_acc", best_val_acc)
        print(f"\nTraining complete.  Best val_acc = {best_val_acc:.4f}")
        print(f"Checkpoint: {_ARTIFACT_DIR / 'model.safetensors'}")


if __name__ == "__main__":
    main()
