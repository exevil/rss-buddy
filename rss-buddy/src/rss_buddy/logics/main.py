import os
import logging
from typing import Dict

from rss_buddy.config import parse_cli_arguments, load_config
from rss_buddy.logics.fetch_feeds import fetch_feeds
from rss_buddy.logics.process_feed import process_feed
from rss_buddy.logics.openai_feed_item_processor import OpenAIFeedItemProcessor
from rss_buddy.logics.generate_digest import generate_digest
from rss_buddy.logics.generate_outputs import generate_outputs
from rss_buddy.logics.generate_feed import generate_feed

from rss_buddy.models import AppConfig, Feed, OutputType
logging.basicConfig(level=logging.INFO)

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

        # Get template directory.
        template_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "templates",
            )
        )

        # Process feeds.
        feed_outputs: Dict[str, Dict[OutputType, str]] = {}
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
            # Generate feed outputs.
            output_name = feed.metadata.title.replace(" ", "-")
            feed_outputs[output_name] = generate_outputs(
                input=output_feed,
                template_dir=template_dir,
                outputs=[
                    OutputType(
                        template_name="feed.html.j2",
                        relative_output_path=f"{output_name}.html",
                    ),
                    OutputType(
                        template_name="feed.rss.j2",
                        relative_output_path=f"{output_name}.rss",
                    ),
                ],
            )

        # Generate index outputs.
        index_input = dict(zip(feed_outputs.keys(), feeds))
        index_outputs = generate_outputs(
            input=index_input,
            template_dir=template_dir,
            outputs=[
                OutputType(
                    template_name="index.html.j2",
                    relative_output_path="index.html",
                ),
            ],
        )
        # Merge feed outputs and index outputs.
        merged_feed_outputs = dict()
        for subdict in feed_outputs.values():
            merged_feed_outputs.update(subdict)
        outputs = {**merged_feed_outputs, **index_outputs}
        # Save outputs.
        output_dir = self.config.output_dir
        # Create output directory if it doesn't exist.
        os.makedirs(output_dir, exist_ok=True)
        for output_type, output_content in outputs.items():
            save_path = os.path.join(output_dir, output_type.relative_output_path)
            logging.info(f"Saving output: {save_path}")
            with open(save_path, "w") as f:
                f.write(output_content)
            logging.info(f"Output saved: {save_path}")

def main():
    cli_args = parse_cli_arguments()
    config = load_config(cli_args)
    main = Main(config=config)
    main.run()

if __name__ == "__main__":
    main()