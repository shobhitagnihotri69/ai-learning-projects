import argparse
from io import BytesIO
from time import sleep

import helium
from dotenv import load_dotenv
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from smolagents import CodeAgent, DuckDuckGoSearchTool, tool
from smolagents.agents import ActionStep
from smolagents.cli import load_model

DEFAULT_PROMPT = """
Search for images of Harry Potter and give a detailed visual description.
Also navigate to Wikipedia to gather key details about his appearance.
"""

def parse_args():
    parser = argparse.ArgumentParser(description="Browser agent using Smolagents")
    parser.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT)
    parser.add_argument("--model-type", default="LiteLLMModel")
    parser.add_argument("--model-id",   default="gpt-4o-mini")
    return parser.parse_args()


def save_screenshot(step: ActionStep, agent: CodeAgent) -> None:
    sleep(1.0)
    driver = helium.get_driver()
    if driver is None:
        return
    for prev in agent.memory.steps:
        if isinstance(prev, ActionStep) and prev.step_number <= step.step_number - 2:
            prev.observations_images = None
    img = Image.open(BytesIO(driver.get_screenshot_as_png()))
    step.observations_images = [img.copy()]
    step.observations = (step.observations or "") + f"\nCurrent url: {driver.current_url}"


@tool
def search_item_ctrl_f(text: str, nth_result: int = 1) -> str:
    """Search for text on page and jump to nth match.
    Args:
        text: text to search
        nth_result: which match to go to
    """
    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
    if nth_result > len(elements):
        raise Exception(f"Match {nth_result} not found ({len(elements)} total)")
    elem = elements[nth_result - 1]
    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
    return f"Found {len(elements)} matches. Focused on match {nth_result}."


@tool
def go_back() -> None:
    """Navigate to the previous page."""
    driver.back()


@tool
def close_popups() -> None:
    """Close any visible modal or popup."""
    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()


def init_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--force-device-scale-factor=1")
    opts.add_argument("--window-size=1000,1350")
    opts.add_argument("--disable-pdf-viewer")
    return helium.start_chrome(headless=False, options=opts)


def init_agent(model):
    return CodeAgent(
        tools=[DuckDuckGoSearchTool(), go_back, close_popups, search_item_ctrl_f],
        model=model,
        additional_authorized_imports=["helium"],
        step_callbacks=[save_screenshot],
        max_steps=25,
        verbosity_level=2,
    )


def main():
    load_dotenv()
    args  = parse_args()
    model = load_model(args.model_type, args.model_id)

    global driver
    driver = init_driver()
    agent  = init_agent(model)
    agent.python_executor("from helium import *")
    agent.run(args.prompt)


if __name__ == "__main__":
    main()
