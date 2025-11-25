import polars as pl
import random


class ValidationSocialDFDataLoader:

    def __init__(self, seed: int = 42, dataset_path: str = "data/social_media_dataset.csv"):
        self.seed = seed
        self.dataset_path = dataset_path

        self.df = pl.read_csv(self.dataset_path)


