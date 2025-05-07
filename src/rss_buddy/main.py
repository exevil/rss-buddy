import os
import logging
from typing import Dict, Callable

from rss_buddy.fetch_feeds import fetch_feeds
from rss_buddy.process_feed import process_feed
from rss_buddy.openai_feed_item_processor import OpenAIFeedItemProcessor
from rss_buddy.generate_outputs import generate_outputs
from rss_buddy.generate_feed import generate_feed
from rss_buddy.generate_digest import generate_digest
from rss_buddy.state_manager import StateManager

from models import AppConfig, Feed, OutputType, Item, OutputPath
from config import load_config

logging.basicConfig(level=logging.INFO)

# Name of the output feed.
OutputName = str

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
                "templates",
            )
        )

        # Normalize and prepare output directory.
        output_dir = os.path.abspath(self.config.output_dir)
        os.makedirs(output_dir, exist_ok=True)

        # Load state.
        state_manager = StateManager(
            file_path=os.path.join(
                output_dir,
                self.config.state_file_name,
            ),
            feed_credentials=self.config.feed_credentials,
            global_filter_criteria=self.config.global_filter_criteria,
        )

        # Process feeds.
        feed_outputs: Dict[OutputName, Dict[OutputPath, str]] = {}
        for feed in feeds:
            processor = OpenAIFeedItemProcessor(
                openai_api_key=self.config.openai_api_key,
                global_filter_criteria=self.config.global_filter_criteria,
                item_filter_criteria=feed.credentials.filter_criteria,
            )
            # Check if an item has been previously processed and process it with LLM if not.
            def is_passed_filter(item: Item) -> bool:
                previous_result = state_manager.item_previous_processing_result(
                    feed_link=feed.credentials.url,
                    item_guid=item.guid,
                ) 
                if previous_result is not None:
                    return previous_result
                else:
                    return processor.is_passed_filter(item)
                
            processed_feed = process_feed(
                feed=feed,
                is_passed_filter=is_passed_filter,
                days_lookback=self.config.days_lookback,
            )
            # Update state.
            state_manager.update_state(
                feed_credentials=feed.credentials,
                processing_result=processed_feed.result,
            )
            # Generate digest.
            digest = generate_digest(
                feed=feed,
                item_guids=processed_feed.result.failed_item_guids,
            )
            # Generate output feed.
            output_feed = generate_feed(
                original_feed=feed,
                passed_item_guids=processed_feed.result.passed_item_guids,
                digest_item=digest,
            )
            # Generate feed outputs.
            output_name: OutputName = feed.metadata.title.replace(" ", "-")
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
        # Merge outputs.
        merged_feed_outputs: Dict[OutputPath, str] = {}
        for subdict in feed_outputs.values():
            merged_feed_outputs.update(subdict)
        outputs = {**merged_feed_outputs, **index_outputs}

        # Write outputs.
        for output_path, output_content in outputs.items():
            save_path = os.path.join(output_dir, output_path)
            logging.info(f"Saving output to \"{save_path}\"")
            with open(save_path, "w") as f:
                f.write(output_content)
            logging.info(f"Output saved to \"{save_path}\"")
        # Write state.
        state_manager.write()

def main():
    config = load_config()
    main = Main(config=config)
    main.run()

if __name__ == "__main__":
    main()