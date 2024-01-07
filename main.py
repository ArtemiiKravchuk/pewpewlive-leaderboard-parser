"""Gather data from pewpew.live leaderboards"""

import itertools
import json
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException

from loguru import logger

logger = logger.opt(colors=True)

headless = Options()
headless.add_argument('--headless')


def split_list_by_br(lst: list) -> list[list]:
    """Split list using one of selenium elements by
    html <br> tags"""
    logger.trace("Splitting list by `br` tags: <y>{}</>", lst)

    return [list(group) for k, 
            group in
            itertools.groupby(lst, lambda x: x.tag_name=="br") if not k]


def get_players() -> list[dict]:
    """Get basic data about players, including
    link for further information"""
    logger.info("Getting basic player info")

    driver = webdriver.Firefox()
    driver.get("https://pewpew.live/era2")

    table = driver.find_element(By.XPATH, "//*[@id='score_table']")
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []

    logger.debug("Starting to go through leaderboard...")
    for row in rows[1:]:  # [1:] to remove headers
        cells = row.find_elements(By.TAG_NAME, "td")
        rank = int(cells[0].text[:-1])
        score = float(cells[1].text)

        name_field = cells[2]
        name = name_field.text
        link = name_field.find_element(
                By.TAG_NAME, "a").get_attribute("href")

        country = cells[3].text
        wr_count = cells[4].text
        if wr_count == "":
            wr_count = 0
        else:
            wr_count = int(wr_count)

        player = {"rank": rank, "score": score, "name": name,
                  "link": link, "country": country,
                  "wr_count": wr_count}
        logger.trace("Got player: <y>{}</>", player)
        data.append(player)

    return data


def get_medals(driver: webdriver.Firefox) -> dict:
    """Get medals from the given page (open with
    the given driver)"""
    logger.debug("Getting medals for a player")

    try:
        medals_header = driver.find_element(
            By.XPATH, "//*[contains(text(), 'Medals')]"
        )
    except NoSuchElementException: # player hides their medals
        logger.warning("Got NoSuchElementException on medals header")
        return None

    next_siblings = medals_header.find_elements(
        By.XPATH, "following-sibling::*"
    )
    raw_data = split_list_by_br(next_siblings)

    medals = []
    for level in raw_data:
        level_name = level[0].text

        try:
            stars = level[1].text
        except IndexError:  # encoutered "Scores" division
            return medals

        stars2p = level[2].text

        star_count = len(stars)
        star_count_2p = len(stars2p)
        medals.append({"level": level_name, "stars": star_count,
                       "stars_multiplayer": star_count_2p})
        # count += 4  # skip "starize" for next cycle

    return medals
    

def get_full_data(player: dict) -> dict:
    """Get full data on given player"""
    logger.debug("Getting full player data on <y>{}</>",
                 player["name"])

    driver = webdriver.Firefox(options=headless)
    driver.get(player["link"])

    discriminator = driver.find_element(
        By.CLASS_NAME, "discriminator"
    ).text
    discriminator = int(discriminator[1:])

    try:
        bio = driver.find_element(
            By.XPATH, "/html/body/div[1]/div[2]"
        ).text
    except NoSuchElementException:
        bio = None

    medals = get_medals(driver)

    player.update({"discriminator": discriminator,
                   "bio": bio, "medals": medals})
    return player


def main(file: str) -> dict:
    """Start data gathering, save the results into
    given file"""
    logger.info("Starting the script")

    players = get_players()
    full_data = []

    for player in players:
        full_data.append(get_full_data(player))

    logger.info("Finished collecting the data")

    with open(file, "w", encoding="UTF-8") as file:
        json.dump(full_data, file)
    return full_data


if __name__ == "__main__":
    logger.info('__name__ == "__main__", calling main()')
    print(main(sys.argv[1]))
