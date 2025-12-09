from src.pipelines.DatasetCloudPipeline import DatasetCloudPipeline

def main():

    ids = ["DELIpWZN3tU", "C5tBt-0IEEy", "C96nZIGIb_v"]

    pipeline = DatasetCloudPipeline(data_dir="../data/socialdf/socialdf_vids")
    for id in ids:
        pipeline.run(id)

if __name__ == "__main__":
    main()