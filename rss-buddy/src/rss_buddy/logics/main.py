from rss_buddy.config import parse_cli_arguments, load_config
from rss_buddy.logics.fetch_feeds import fetch_feeds
from rss_buddy.logics.process_feed import process_feed
from rss_buddy.logics.openai_feed_item_processor import OpenAIFeedItemProcessor
from rss_buddy.logics.generate_digest import generate_digest
from rss_buddy.logics.generate_outputs import generate_outputs
from rss_buddy.logics.generate_feed import generate_feed

from rss_buddy.models import AppConfig, Feed, OutputType

class Main:
    """ 
    Main class for the RSS Buddy application.
    """
    def __init__(
            self,
            config: AppConfig,
            ):
        self.config = config

    def run(self):
        """
        Run the main application.
        """
        # Load feeds.
        feeds = fetch_feeds(
            credentials=self.config.feed_credentials,
            days_lookback=self.config.days_lookback,
        )

        # Process feeds.
        for feed in feeds:
            processor = OpenAIFeedItemProcessor(
                openai_api_key=self.config.openai_api_key,
                global_filter_criteria=self.config.global_filter_criteria,
                item_filter_criteria=feed.credentials.filter_criteria,
            )
            processed_feed = process_feed(
                feed=feed,
                item_processor=processor,
                days_lookback=self.config.days_lookback,
            )
            # Generate digest.
            digest = generate_digest(
                items=processed_feed.passed_items,
            )
            # Generate output feed.
            output_feed = generate_feed(
                credentials=feed.credentials,
                metadata=feed.metadata,
                passed_items=processed_feed.passed_items,
                digest_item=digest,
            )
            # Generate outputs.
            output_name = feed.credentials.url.split('/')[-1]
            outputs = generate_outputs(
                feed=output_feed,
                template_dir="templates",
                outputs=[
                    OutputType(
                        template_name="feed.html",
                        relative_output_path=f"{output_name}.html",
                    ),
                    OutputType(
                        template_name="feed.rss",
                        relative_output_path=f"{output_name}.rss",
                    ),
                ],
            )
            # Save outputs.
            for output_type, output_content in outputs.items():
                with open(output_type.relative_output_path, "w") as f:
                    f.write(output_content)

if __name__ == "__main__":
    cli_args = parse_cli_arguments()
    config = load_config(cli_args)
    main = Main(config=config)
    main.run()