import polars as pl

def create_val_dataset():
    
    df = pl.read_csv("../socialdf_vids/socialdf_processed.csv")
    is_real = df.filter(pl.col("target") == 0).sample(n=50, seed=42)
    is_fake = df.filter(pl.col("target") == 1).sample(n=50, seed=42)

    val_df = pl.concat([is_real, is_fake])
    val_df.write_csv("val_socialdf.csv")

if __name__ == "__main__":
    create_val_dataset()