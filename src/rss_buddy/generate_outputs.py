import os
import logging

from typing import List, Dict, Any
from datetime import datetime
from email.utils import format_datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

from models import OutputType, OutputPath, Item, DigestItem

def _rfc822(date: datetime) -> str:
    """
    Format a datetime object as an RFC 822 date string.
    """
    return format_datetime(date)

def _is_item(obj: Any) -> bool:
    """Check if object is an Item."""
    return isinstance(obj, Item)

def _is_digest_item(obj: Any) -> bool:
    """Check if object is a DigestItem."""
    return isinstance(obj, DigestItem)

def generate_outputs(
    input: Any,
    template_dir: str,
    outputs: List[OutputType]
) -> Dict[OutputPath, str]:
    """
    Generate outputs from an input using the specified output types. The input will be passed to the template as the `input` variable.
    
    Returns:
        Dict[Output, str]: A dictionary mapping output types to their rendered content.
    """
    logging.info(f"Generating outputs for {len(outputs)} outputs")

    env = Environment(
        loader=FileSystemLoader(template_dir)
    )
    # Add a custom filters to the environment
    env.filters["rfc822"] = _rfc822
    env.filters["is_item"] = _is_item
    env.filters["is_digest_item"] = _is_digest_item

    rendered_outputs = {}
    for output in outputs:
        logging.info(f"Generating output: {output.template_name}")

        template = env.get_template(output.template_name)
        rendered_output = template.render(input=input)
        rendered_outputs[output.relative_output_path] = rendered_output

        logging.info(f"Output generated: {output.template_name}")
    
    return rendered_outputs