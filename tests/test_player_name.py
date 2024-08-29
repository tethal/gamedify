import re

import pytest
from playwright.sync_api import Page, expect


class PlayPage:
    def __init__(self, page: Page):
        page.goto("/play/123-456")
        self.page = page
        self.player_name = self.page.get_by_label("Zadej svou přezdívku:")
        self.enter_button = self.page.get_by_role("button", name="Vstoupit")
        self.wait_for_game_to_start = self.page.get_by_text(re.compile(r"Hello, .*, wait for the game to start."))


class TestSetPlayerNameForm:

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = PlayPage(page)
        self.other_page = PlayPage(page.context.new_page())

    def test_empty_player_name(self):
        self.page.enter_button.click()
        expect(self.page.player_name).to_be_visible()

    def test_set_player_name(self):
        self.page.player_name.fill("Alice")
        self.page.enter_button.click()

        expect(self.page.wait_for_game_to_start).to_contain_text("Alice")
        expect(self.other_page.wait_for_game_to_start).to_contain_text("Alice")

        p3 = PlayPage(self.page.page.context.new_page())
        expect(p3.wait_for_game_to_start).to_contain_text("Alice")
