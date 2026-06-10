# payor_classifier_resnet — training entry
import hydra
from omegaconf import DictConfig
import mlflow

@hydra.main(version_base=None, config_path="../../../configs", config_name="train_payor_classifier")
def main(cfg: DictConfig):
    with mlflow.start_run():
        mlflow.log_params(dict(cfg.training))
        # TODO: training loop
        pass

if __name__ == "__main__":
    main()
