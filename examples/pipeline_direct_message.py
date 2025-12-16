from src.pipelines.DirectMessagePipeline import DirectMessagePipeline

def main():

    event_data = {
        "id": "test-request-dm-pipeline",
        "data": {
            "videoUrl": "https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=17929257822119892&signature=AYetfvAQDwK5LN7tZsGEea_rVUIyUJ0rO4izcGK_Vn3x5eu9k5qH2spAjm0OIJeMp2I3SIejLjFkagdEK_QZJo_Ebud5XuwNXfCkt-2L1CiowEIEQHhe6WnTcvzOc1R6iK2MEDMADQDw9y56Qh526VYGXrD6a40Ug47o9SCnGV-fkt1bpY7r7fviDrdGdaIzQ9Am1tfL6crlbGOgk2cbR582bCsKlDPL",
            "videoPath": "",
            "videoId": "17929257822119892",
            "userId": "17841405857678291",
            "claim": "",
            "context": "",
            "message": ""
        }
    }

    pipeline = DirectMessagePipeline(saving_dir="../data/requests")
    pipeline.run(event_data)

if __name__ == "__main__":
    main()