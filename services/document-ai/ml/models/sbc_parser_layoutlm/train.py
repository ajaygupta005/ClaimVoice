# sbc_parser_layoutlm — training entry
import hydra
from omegaconf import DictConfig
import mlflow

@hydra.main(version_base=None, config_path="../../../configs", config_name="train_sbc")
def main(cfg: DictConfig):
    with mlflow.start_run():
        mlflow.log_params(dict(cfg.training))
        # TODO: training loop
        pass

if __name__ == "__main__":
    main()
