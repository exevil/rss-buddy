import os
from typing import List, Dict
from jinja2 import Environment, FileSystemLoader

from rss_buddy.models import Feed, OutputType

def generate_outputs(
    feed: Feed,
    template_dir: str,
    outputs: List[OutputType]
) -> Dict[OutputType, str]:
    """
    Generate outputs from a feed using the specified output types.
    
    Returns:
        Dict[Output, str]: A dictionary mapping output types to their rendered content.
    """
    env = Environment(loader=FileSystemLoader(template_dir))

    rendered_outputs = {}
    for output in outputs:
        template = env.get_template(output.template_name)
        rendered_output = template.render(feed=feed)
        rendered_outputs[output] = rendered_output
    
    return rendered_outputs
